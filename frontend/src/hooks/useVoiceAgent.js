import { useState, useEffect, useRef, useCallback } from 'react'

// Derive a safe default WebSocket URL in production when VITE_WS_URL is not provided.
// - Prefer env var when available
// - On HTTPS origins, force wss:// with current host
// - On HTTP (local dev), allow ws:// with localhost fallback
const WS_URL = (() => {
  const envUrl = import.meta.env.VITE_WS_URL && String(import.meta.env.VITE_WS_URL).trim()
  if (envUrl) return envUrl

  if (typeof window !== 'undefined' && window.location) {
    const { protocol, host } = window.location
    const isSecure = protocol === 'https:'
    const wsScheme = isSecure ? 'wss' : 'ws'
    return `${wsScheme}://${host}/ws/voice`
  }

  return 'ws://localhost:8000/ws/voice'
})()
const RECONNECT_DELAY = 3000

// For worklets, prefer absolute '/static/' so FastAPI and dev both serve them

export function useVoiceAgent() {
  const [isConnected, setIsConnected] = useState(false)
  const [isSessionActive, setIsSessionActive] = useState(false)
  const [messages, setMessages] = useState([])
  const [claimData, setClaimData] = useState({})
  const [isClaimComplete, setIsClaimComplete] = useState(false)
  const [agentStatus, setAgentStatus] = useState('Initializing...')
  const [error, setError] = useState(null)
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Microphone device management
  const [microphones, setMicrophones] = useState([])
  const [selectedDeviceId, setSelectedDeviceId] = useState('')
  const [isEnumeratingDevices, setIsEnumeratingDevices] = useState(false)
  const [permissionsGranted, setPermissionsGranted] = useState(false)
  const [autoPermissionPrompted, setAutoPermissionPrompted] = useState(false)

  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioWorkletNodeRef = useRef(null)
  const playbackWorkletRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  // Enumerate available input devices
  const refreshAudioDevices = useCallback(async (requestPermission = false) => {
    try {
      setIsEnumeratingDevices(true)
      // Optionally request permission to reveal device labels
      if (requestPermission) {
        try {
          const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true })
          setPermissionsGranted(true)
          tempStream.getTracks().forEach(t => t.stop())
        } catch (permErr) {
          // Do not surface as a blocking error here; user can still pick default device
          console.warn('Microphone permission not granted (labels may be hidden):', permErr)
        }
      }

      const allDevices = await navigator.mediaDevices.enumerateDevices()
      const inputs = allDevices.filter(d => d.kind === 'audioinput')
      setMicrophones(inputs)

      // Initialize a default selection if none selected yet
      if (!selectedDeviceId && inputs.length > 0) {
        const preferred = inputs.find(d => d.deviceId === 'default') || inputs[0]
        setSelectedDeviceId(preferred.deviceId)
      }
    } catch (err) {
      console.error('Failed to enumerate devices:', err)
    } finally {
      setIsEnumeratingDevices(false)
    }
  }, [selectedDeviceId])

  const requestDevicePermission = useCallback(async () => {
    try {
      const tempStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      setPermissionsGranted(true)
      tempStream.getTracks().forEach(t => t.stop())
      await refreshAudioDevices(false)
    } catch (err) {
      console.error('Permission request failed:', err)
      setError('Microphone permission denied. Device names may be hidden.')
    }
  }, [refreshAudioDevices])

  // Handle messages from server (defined before connectWebSocket to avoid circular dependency)
  const handleServerMessage = useCallback((message) => {
    const { type, data } = message

    switch (type) {
      case 'connected':
        setAgentStatus('Ready')
        console.log('Session connected:', data.session_id)
        break

      case 'chat_message':
        // Check if message already exists (avoid duplicates from optimistic updates)
        setMessages(prev => {
          const isDuplicate = prev.some(msg => 
            msg.role === data.role && 
            msg.content === data.content &&
            Math.abs(new Date(msg.timestamp).getTime() - new Date(data.timestamp).getTime()) < 2000
          )
          
          if (isDuplicate) {
            return prev
          }
          
          return [...prev, {
            role: data.role,
            content: data.content,
            type: data.type || 'voice',
            image: data.image,
            imageName: data.imageName,
            timestamp: data.timestamp
          }]
        })
        
        // Update status based on message role
        if (data.role === 'assistant') {
          setAgentStatus('Agent speaking...')
          setIsSpeaking(false) // Audio is done when transcript arrives
        }
        break

      case 'claim_data_update':
        setClaimData(data.claim_data)
        setIsClaimComplete(data.is_complete)
        console.log('Claim data updated:', data.is_complete ? 'Complete' : 'In progress')
        break

      case 'audio_delta':
        // Play audio through worklet
        if (playbackWorkletRef.current && data.audio) {
          try {
            // Ensure audio context is running before playing
            if (audioContextRef.current?.state === 'suspended') {
              audioContextRef.current.resume()
            }
            
            const audioBytes = Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))
            const audioData = new Int16Array(audioBytes.buffer)
            playbackWorkletRef.current.port.postMessage({ audio: audioData })
            setIsSpeaking(true)
            // While agent is speaking, we should avoid sending mic chunks
            // Microphone capture gate is enforced by the backend; we also prevent UI from flooding
          } catch (err) {
            console.error('Failed to decode audio:', err)
          }
        }
        break

      case 'user_speech_started':
        setAgentStatus('Listening...')
        setIsSpeaking(false)
        break

      case 'user_speech_stopped':
        setAgentStatus('Processing...')
        break

      case 'agent_ready':
        setAgentStatus('Ready')
        setIsSpeaking(false)
        // Ensure audio context is ready for next playback
        if (audioContextRef.current?.state === 'suspended') {
          audioContextRef.current.resume().then(() => {
            console.log('Audio context resumed for agent speech')
          })
        }
        break

      case 'claim_complete':
        setClaimData(data.claim_data)
        setIsClaimComplete(true)
        setAgentStatus('Claim Submitted ✅')
        console.log('Claim submitted successfully:', data.submission_result)
        
        // Show success message
        if (data.submission_result?.claim_id) {
          console.log('Claim ID:', data.submission_result.claim_id)
        }
        break

      case 'error':
        setError(data.message)
        setAgentStatus('Error')
        console.error('Server error:', data.message)
        break

      default:
        console.log('Unknown message type:', type, data)
    }
  }, [])

  // Initialize audio context and worklets
  const initializeAudio = useCallback(async () => {
    try {
      // Create audio context for playback
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000,
        latencyHint: 'interactive'
      })
      audioContextRef.current = audioContext
      
      // Ensure audio context is running
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }

      // Load playback worklet via bundler URL to ensure it is emitted and served
      const playbackUrl = new URL('../worklets/audio-playback-worklet.js', import.meta.url)
      await audioContext.audioWorklet.addModule(playbackUrl)
      const playbackNode = new AudioWorkletNode(audioContext, 'audio-playback-worklet')
      playbackNode.connect(audioContext.destination)
      playbackWorkletRef.current = playbackNode
      
      console.log('Audio context initialized, state:', audioContext.state)

      // Get microphone access (honor selected device if provided)
      const audioConstraints = {
        channelCount: 1,
        sampleRate: 24000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }

      if (selectedDeviceId) {
        // If "default" keep as string; otherwise require exact match
        audioConstraints.deviceId = selectedDeviceId === 'default' 
          ? 'default' 
          : { exact: selectedDeviceId }
      }

      let stream
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints })
      } catch (constraintErr) {
        console.warn('Primary getUserMedia failed, retrying with relaxed constraints:', constraintErr)
        // Relax constraints as a fallback to avoid OverconstrainedError on some devices
        stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      }
      mediaStreamRef.current = stream

      // Load audio processor worklet via bundler URL
      const processorUrl = new URL('../worklets/audio-processor-worklet.js', import.meta.url)
      await audioContext.audioWorklet.addModule(processorUrl)
      const source = audioContext.createMediaStreamSource(stream)
      const processorNode = new AudioWorkletNode(audioContext, 'audio-processor-worklet')
      
      // Handle audio data from microphone
      processorNode.port.onmessage = (event) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const audioData = event.data
          const base64Audio = btoa(
            String.fromCharCode(...new Uint8Array(audioData.buffer))
          )
          wsRef.current.send(JSON.stringify({
            type: 'audio_data',
            audio: base64Audio
          }))
        }
      }

      source.connect(processorNode)
      audioWorkletNodeRef.current = processorNode

      return true
    } catch (err) {
      console.error('Failed to initialize audio:', err)
      setError('Microphone access denied. Please allow microphone access and refresh.')
      return false
    }
  }, [selectedDeviceId])

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      setError(null)
      setAgentStatus('Connected')
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleServerMessage(message)
      } catch (err) {
        console.error('Failed to parse message:', err)
      }
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      setError('Connection error. Please check your network.')
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
      setIsConnected(false)
      setIsSessionActive(false)
      setAgentStatus('Disconnected')
      
      // Only attempt reconnection if not manually stopped
      if (wsRef.current === ws) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connectWebSocket()
        }, RECONNECT_DELAY)
      }
    }
  }, [handleServerMessage])  // Add dependency

  // Start voice session
  const startSession = useCallback(async () => {
    try {
      // Initialize audio first
      const audioReady = await initializeAudio()
      if (!audioReady) return

      // Ensure WebSocket is connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected to server. Attempting to connect...')
        connectWebSocket() // Try to reconnect
        // Wait a bit for connection
        await new Promise(resolve => setTimeout(resolve, 1000))
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          setError('Could not connect to server. Please refresh and try again.')
          return
        }
      }

      // Start session
      wsRef.current.send(JSON.stringify({ type: 'start_session' }))
      setIsSessionActive(true)
      setAgentStatus('Starting session...')
      
      // Resume audio context if suspended (critical for audio playback)
      if (audioContextRef.current?.state === 'suspended') {
        await audioContextRef.current.resume()
        console.log('Audio context resumed for session')
      }
      
      console.log('Session started, audio context state:', audioContextRef.current?.state)
    } catch (err) {
      console.error('Failed to start session:', err)
      setError('Failed to start session: ' + err.message)
    }
  }, [initializeAudio, connectWebSocket])

  // Stop voice session
  const stopSession = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop_session' }))
    }
    
    setIsSessionActive(false)
    setAgentStatus('Session ended')

    // Stop audio streams
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    audioWorkletNodeRef.current = null
    playbackWorkletRef.current = null
  }, [])

  // Initialize WebSocket connection on mount
  useEffect(() => {
    connectWebSocket()

    return () => {
      // Cleanup on unmount
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      
      stopSession()
      
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connectWebSocket, stopSession])

  // Keep device list updated and react to hardware changes
  useEffect(() => {
    // Initial enumeration without forcing permission prompt
    refreshAudioDevices(false)

    const handleDeviceChange = () => refreshAudioDevices(false)
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange)
    }
    return () => {
      if (navigator.mediaDevices && navigator.mediaDevices.removeEventListener) {
        navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange)
      }
    }
  }, [refreshAudioDevices])

  // If no devices or labels are available, proactively request permission once
  useEffect(() => {
    const noDevices = microphones.length === 0
    const labelsMissing = microphones.length > 0 && microphones.every(m => !m.label)
    if (!autoPermissionPrompted && (noDevices || labelsMissing) && !permissionsGranted) {
      setAutoPermissionPrompted(true)
      requestDevicePermission()
    }
  }, [microphones, permissionsGranted, autoPermissionPrompted, requestDevicePermission])

  // Add user interaction handler to resume audio context (browser requirement)
  useEffect(() => {
    const resumeAudioOnInteraction = async () => {
      if (audioContextRef.current?.state === 'suspended') {
        await audioContextRef.current.resume()
        console.log('Audio context resumed by user interaction')
      }
    }
    
    // Listen for any user interaction to resume audio
    document.addEventListener('click', resumeAudioOnInteraction)
    document.addEventListener('touchstart', resumeAudioOnInteraction)
    
    return () => {
      document.removeEventListener('click', resumeAudioOnInteraction)
      document.removeEventListener('touchstart', resumeAudioOnInteraction)
    }
  }, [])

  // Send text message
  const sendTextMessage = useCallback((text) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && isSessionActive) {
      wsRef.current.send(JSON.stringify({
        type: 'text_input',
        text: text
      }))
      
      // Optimistically add to UI
      setMessages(prev => [...prev, {
        role: 'user',
        content: text,
        type: 'text',
        timestamp: new Date().toLocaleTimeString()
      }])
      
      console.log('Sent text message:', text)
    } else {
      console.warn('Cannot send text: WebSocket not connected or session inactive')
    }
  }, [isSessionActive])

  // Send image
  const sendImage = useCallback((imageData) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && isSessionActive) {
      wsRef.current.send(JSON.stringify({
        type: 'image_input',
        image: imageData.data,
        mimeType: imageData.mimeType,
        name: imageData.name
      }))

      console.log('Sent image:', imageData.name, imageData.mimeType)
    } else {
      console.warn('Cannot send image: WebSocket not connected or session inactive')
    }
  }, [isSessionActive])

  return {
    isConnected,
    isSessionActive,
    messages,
    claimData,
    isClaimComplete,
    agentStatus,
    error,
    isSpeaking,
    startSession,
    stopSession,
    sendTextMessage,
    sendImage,
    // microphone selection API
    microphones,
    selectedDeviceId,
    setSelectedDeviceId,
    refreshAudioDevices,
    isEnumeratingDevices,
    permissionsGranted,
    requestDevicePermission,
  }
}
