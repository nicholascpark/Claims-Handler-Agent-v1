import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/voice'
const RECONNECT_DELAY = 3000

export function useVoiceAgent() {
  const [isConnected, setIsConnected] = useState(false)
  const [isSessionActive, setIsSessionActive] = useState(false)
  const [messages, setMessages] = useState([])
  const [claimData, setClaimData] = useState({})
  const [isClaimComplete, setIsClaimComplete] = useState(false)
  const [agentStatus, setAgentStatus] = useState('Initializing...')
  const [error, setError] = useState(null)

  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioWorkletNodeRef = useRef(null)
  const playbackWorkletRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  // Initialize audio context and worklets
  const initializeAudio = useCallback(async () => {
    try {
      // Create audio context for playback
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000
      })
      audioContextRef.current = audioContext

      // Load playback worklet
      await audioContext.audioWorklet.addModule('/audio-playback-worklet.js')
      const playbackNode = new AudioWorkletNode(audioContext, 'audio-playback-worklet')
      playbackNode.connect(audioContext.destination)
      playbackWorkletRef.current = playbackNode

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 24000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      })
      mediaStreamRef.current = stream

      // Load audio processor worklet for microphone
      await audioContext.audioWorklet.addModule('/audio-processor-worklet.js')
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
  }, [])

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
      
      // Attempt reconnection
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Attempting to reconnect...')
        connectWebSocket()
      }, RECONNECT_DELAY)
    }
  }, [])

  // Handle messages from server
  const handleServerMessage = (message) => {
    const { type, data } = message

    switch (type) {
      case 'connected':
        setAgentStatus('Ready')
        console.log('Session connected:', data.session_id)
        break

      case 'chat_message':
        setMessages(prev => [...prev, {
          role: data.role,
          content: data.content,
          timestamp: data.timestamp
        }])
        break

      case 'claim_data_update':
        setClaimData(data.claim_data)
        setIsClaimComplete(data.is_complete)
        break

      case 'audio_delta':
        // Play audio through worklet
        if (playbackWorkletRef.current && data.audio) {
          try {
            const audioBytes = Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))
            const audioData = new Int16Array(audioBytes.buffer)
            playbackWorkletRef.current.port.postMessage({ audio: audioData })
          } catch (err) {
            console.error('Failed to decode audio:', err)
          }
        }
        break

      case 'agent_ready':
        setAgentStatus('Listening...')
        break

      case 'claim_complete':
        setClaimData(data.claim_data)
        setIsClaimComplete(true)
        setAgentStatus('Claim Submitted')
        console.log('Claim submitted:', data.submission_result)
        break

      case 'error':
        setError(data.message)
        setAgentStatus('Error')
        break

      default:
        console.log('Unknown message type:', type)
    }
  }

  // Start voice session
  const startSession = useCallback(async () => {
    try {
      // Initialize audio first
      const audioReady = await initializeAudio()
      if (!audioReady) return

      // Ensure WebSocket is connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected to server. Attempting to connect...')
        return
      }

      // Start session
      wsRef.current.send(JSON.stringify({ type: 'start_session' }))
      setIsSessionActive(true)
      setAgentStatus('Starting session...')
      
      // Resume audio context if suspended
      if (audioContextRef.current?.state === 'suspended') {
        await audioContextRef.current.resume()
      }
    } catch (err) {
      console.error('Failed to start session:', err)
      setError('Failed to start session: ' + err.message)
    }
  }, [initializeAudio])

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

  return {
    isConnected,
    isSessionActive,
    messages,
    claimData,
    isClaimComplete,
    agentStatus,
    error,
    startSession,
    stopSession,
  }
}
