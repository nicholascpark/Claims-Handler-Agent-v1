import { useState, useRef, useCallback, useEffect, useMemo } from 'react';

// Constants for configuration
const AUDIO_CONSTRAINTS = {
  audio: {
    sampleRate: 48000,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  }
};

const FALLBACK_CONSTRAINTS = { audio: true };
const VISUALIZATION_BARS = 8;
const DATA_COLLECTION_INTERVAL = 100; // ms
const MAX_RECORDING_WAIT = 3000; // ms

const useAudioRecording = () => {
  // Core states
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState(null);
  const [audioLevels, setAudioLevels] = useState(new Array(VISUALIZATION_BARS).fill(0));
  const [availableDevices, setAvailableDevices] = useState([]);
  
  // Persist preferred microphone
  const [selectedDeviceId, setSelectedDeviceId] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('preferredMicDeviceId') || null;
    }
    return null;
  });

  // Refs for audio components
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const animationFrameRef = useRef(null);
  const analyzerRef = useRef(null);
  const audioContextRef = useRef(null);
  const recordingStateRef = useRef({ isRecording: false, isPaused: false });

  // Update recording state ref
  useEffect(() => {
    recordingStateRef.current = { isRecording, isPaused };
  }, [isRecording, isPaused]);

  // Memoized MIME type detection
  const mimeType = useMemo(() => {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
    return types.find(type => MediaRecorder.isTypeSupported(type)) || '';
  }, []);

  // Get available audio devices
  const getAudioDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter(device => device.kind === 'audioinput');
      setAvailableDevices(audioInputs);
      
      // Auto-select first device if none selected
      if (audioInputs.length > 0 && !selectedDeviceId) {
        const firstDevice = audioInputs[0].deviceId;
        setSelectedDeviceId(firstDevice);
        if (typeof window !== 'undefined') {
          localStorage.setItem('preferredMicDeviceId', firstDevice);
        }
      }
      
      return audioInputs;
    } catch (err) {
      setError(`Failed to get microphone devices: ${err.message}`);
      return [];
    }
  }, [selectedDeviceId]);

  // Optimized stream creation
  const createStream = useCallback(async () => {
    const constraints = selectedDeviceId 
      ? { ...AUDIO_CONSTRAINTS, audio: { ...AUDIO_CONSTRAINTS.audio, deviceId: { exact: selectedDeviceId } } }
      : AUDIO_CONSTRAINTS;

    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (error) {
      // Fallback to basic constraints
      console.warn('Failed with enhanced constraints, using fallback');
      return await navigator.mediaDevices.getUserMedia(FALLBACK_CONSTRAINTS);
    }
  }, [selectedDeviceId]);

  // Initialize audio recording
  const initializeRecording = useCallback(async () => {
    try {
      console.log('initializeRecording called');
      setError(null);
      
      // Get devices and create stream
      console.log('Getting audio devices...');
      await getAudioDevices();
      console.log('Creating stream...');
      const stream = await createStream();
      console.log('Stream created:', stream);
      
      // Verify audio tracks
      const audioTracks = stream.getAudioTracks();
      console.log('Audio tracks found:', audioTracks.length);
      if (audioTracks.length === 0) {
        throw new Error('No audio tracks found in the stream');
      }
      
      streamRef.current = stream;

      // Set up audio analysis
      console.log('Setting up audio analysis...');
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyzer = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      analyzer.fftSize = 256;
      microphone.connect(analyzer);
      
      audioContextRef.current = audioContext;
      analyzerRef.current = analyzer;

      // Create MediaRecorder
      console.log('Creating MediaRecorder...');
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      // Optimized event handlers
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (chunksRef.current.length === 0) {
          setError('No audio data was recorded. Please check your microphone permissions.');
          setAudioBlob(null);
          return;
        }

        const totalSize = chunksRef.current.reduce((total, chunk) => total + chunk.size, 0);
        if (totalSize === 0) {
          setError('Audio recording failed - no audio data captured.');
          setAudioBlob(null);
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType });
        setAudioBlob(blob);
        setAudioURL(URL.createObjectURL(blob));
        chunksRef.current = [];
      };

      mediaRecorder.onerror = (event) => {
        setError(`Recording error: ${event.error.message}`);
      };

      console.log('Setting isInitialized to true');
      setIsInitialized(true);
    } catch (err) {
      console.error('initializeRecording failed:', err);
      setError(`Failed to initialize recording: ${err.message}`);
    }
  }, [selectedDeviceId, getAudioDevices, createStream, mimeType]);

  // Start recording
  const startRecording = useCallback(async () => {
    console.log('startRecording called with isInitialized:', isInitialized);
    
    if (!isInitialized) {
      console.log('Not initialized, calling initializeRecording...');
      await initializeRecording();
      console.log('After initialization, isInitialized should be true');
    }

    console.log('Checking refs:', { 
      hasMediaRecorder: !!mediaRecorderRef.current, 
      hasStream: !!streamRef.current,
      streamActive: streamRef.current?.active
    });

    if (mediaRecorderRef.current && streamRef.current) {
      try {
        console.log('Setting up recording...');
        setError(null);
        setAudioBlob(null);
        
        // Clean up previous audio URL
        if (audioURL) {
          URL.revokeObjectURL(audioURL);
        }
        setAudioURL(null);

        // Resume AudioContext if suspended
        if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
          console.log('Resuming suspended AudioContext...');
          await audioContextRef.current.resume();
        }

        // Ensure stream is active
        if (!streamRef.current.active) {
          console.log('Stream not active, re-initializing...');
          await initializeRecording();
          if (!streamRef.current.active) {
            throw new Error('Failed to activate audio stream');
          }
        }

        // Clear chunks and start recording
        console.log('Starting MediaRecorder...');
        chunksRef.current = [];
        mediaRecorderRef.current.start(DATA_COLLECTION_INTERVAL);
        
        console.log('Setting recording states...');
        setIsRecording(true);
        setIsPaused(false);
        setRecordingTime(0);

        // Start timer
        timerRef.current = setInterval(() => {
          setRecordingTime(prev => prev + 1);
        }, 1000);
        
        // Start visualization
        startAudioVisualization();
        console.log('Recording started successfully');
      } catch (err) {
        console.error('Error in startRecording try block:', err);
        setError(`Failed to start recording: ${err.message}`);
      }
    } else {
      const errorMsg = 'Recording not properly initialized. Please refresh and try again.';
      console.error(errorMsg, {
        hasMediaRecorder: !!mediaRecorderRef.current,
        hasStream: !!streamRef.current
      });
      setError(errorMsg);
    }
  }, [isInitialized, initializeRecording, audioURL]);

  // Pause recording
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      stopAudioVisualization();
    }
  }, [isRecording, isPaused]);

  // Resume recording
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
      startAudioVisualization();
    }
  }, [isRecording, isPaused]);

  // Stop recording with Promise-based approach
  const stopRecording = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (!mediaRecorderRef.current || (!isRecording && !isPaused)) {
        resolve(null);
        return;
      }

      let resolved = false;
      
      const resolveStop = (blob) => {
        if (resolved) return;
        resolved = true;
        resolve(blob);
      };
      
      const rejectStop = (error) => {
        if (resolved) return;
        resolved = true;
        reject(error);
      };

      // Set timeout as fallback
      const stopTimeout = setTimeout(() => {
        if (resolved) return;
        
        if (chunksRef.current && chunksRef.current.length > 0) {
          try {
            const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
            const manualBlob = new Blob(chunksRef.current, { type: mimeType });
            setAudioBlob(manualBlob);
            setAudioURL(URL.createObjectURL(manualBlob));
            chunksRef.current = [];
            resolveStop(manualBlob);
          } catch (error) {
            rejectStop(new Error(`Failed to create audio blob: ${error.message}`));
          }
        } else {
          rejectStop(new Error('Recording stopped but no audio data was captured'));
        }
      }, MAX_RECORDING_WAIT);

      // Override onstop handler
      const originalOnStop = mediaRecorderRef.current.onstop;
      mediaRecorderRef.current.onstop = (event) => {
        clearTimeout(stopTimeout);
        
        // Process the chunks to create the blob right here
        if (chunksRef.current.length === 0) {
          rejectStop(new Error('No audio data was recorded. Please check your microphone permissions.'));
          return;
        }

        const totalSize = chunksRef.current.reduce((total, chunk) => total + chunk.size, 0);
        if (totalSize === 0) {
          rejectStop(new Error('Audio recording failed - no audio data captured.'));
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: mediaRecorderRef.current.mimeType });
        
        // Update state
        setAudioBlob(blob);
        setAudioURL(URL.createObjectURL(blob));
        chunksRef.current = [];
        
        // Resolve with the newly created blob immediately
        resolveStop(blob);
      };

      try {
        mediaRecorderRef.current.stop();
      } catch (error) {
        clearTimeout(stopTimeout);
        rejectStop(error);
        return;
      }
      
      // Update state immediately
      setIsRecording(false);
      setIsPaused(false);
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      stopAudioVisualization();
    });
  }, [isRecording, isPaused, audioBlob]);

  // Toggle recording
  const toggleRecording = useCallback(() => {
    console.log('toggleRecording called with states:', { isRecording, isPaused });
    
    if (!isRecording) {
      console.log('Starting recording...');
      return startRecording();
    } else if (isPaused) {
      console.log('Resuming recording...');
      resumeRecording();
    } else {
      console.log('Pausing recording...');
      pauseRecording();
    }
  }, [isRecording, isPaused, startRecording, pauseRecording, resumeRecording]);

  // Audio visualization
  const startAudioVisualization = useCallback(() => {
    if (!analyzerRef.current) return;

    const analyzer = analyzerRef.current;
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const updateLevels = () => {
      const { isRecording: rec, isPaused: pause } = recordingStateRef.current;

      if (rec && !pause) {
        analyzer.getByteFrequencyData(dataArray);

        const barWidth = Math.floor(bufferLength / VISUALIZATION_BARS);
        const newLevels = [];

        for (let i = 0; i < VISUALIZATION_BARS; i++) {
          let sum = 0;
          for (let j = 0; j < barWidth; j++) {
            sum += dataArray[i * barWidth + j];
          }
          const average = sum / barWidth;
          newLevels.push(Math.min(100, (average / 255) * 100));
        }

        setAudioLevels(newLevels);
      }

      animationFrameRef.current = requestAnimationFrame(updateLevels);
    };

    updateLevels();
  }, []);

  const stopAudioVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    setAudioLevels(new Array(VISUALIZATION_BARS).fill(0));
  }, []);

  // Optimized WAV conversion
  const convertToWav = useCallback(async (webmBlob) => {
    return new Promise((resolve, reject) => {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const fileReader = new FileReader();
      
      fileReader.onload = async (e) => {
        try {
          const arrayBuffer = e.target.result;
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          
          const wav = audioBufferToWav(audioBuffer);
          const wavBlob = new Blob([wav], { type: 'audio/wav' });
          
          audioContext.close();
          resolve(wavBlob);
        } catch (error) {
          audioContext.close();
          reject(error);
        }
      };
      
      fileReader.onerror = (error) => {
        audioContext.close();
        reject(error);
      };
      
      fileReader.readAsArrayBuffer(webmBlob);
    });
  }, []);

  // Helper function for WAV conversion
  const audioBufferToWav = (audioBuffer) => {
    const length = audioBuffer.length;
    const numberOfChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const bytesPerSample = 2;
    const blockAlign = numberOfChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = length * blockAlign;
    const bufferSize = 44 + dataSize;

    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view = new DataView(arrayBuffer);
    
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    // WAV header
    writeString(0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    // Convert audio data
    let offset = 44;
    for (let i = 0; i < length; i++) {
      for (let channel = 0; channel < numberOfChannels; channel++) {
        const sample = Math.max(-1, Math.min(1, audioBuffer.getChannelData(channel)[i]));
        view.setInt16(offset, sample * 0x7FFF, true);
        offset += 2;
      }
    }

    return arrayBuffer;
  };

  // Convert blob to base64
  const getBase64Audio = useCallback(async (providedBlob = null) => {
    const blobToConvert = providedBlob || audioBlob;
    
    if (!blobToConvert) {
      throw new Error('No audio blob available for conversion');
    }

    if (blobToConvert.size === 0) {
      throw new Error('Audio blob is empty - no audio data was captured');
    }

    try {
      const wavBlob = await convertToWav(blobToConvert);

      if (wavBlob.size === 0) {
        throw new Error('Audio conversion failed - resulting WAV file is empty');
      }

      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result.split(',')[1];
          if (!base64 || base64.length === 0) {
            reject(new Error('Base64 conversion failed - no data generated'));
            return;
          }
          resolve(base64);
        };
        reader.onerror = () => {
          reject(new Error('Failed to convert audio to base64'));
        };
        reader.readAsDataURL(wavBlob);
      });
    } catch (error) {
      throw new Error(`Audio conversion failed: ${error.message}`);
    }
  }, [audioBlob, convertToWav]);

  // Change microphone device
  const changeDevice = useCallback(async (deviceId) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferredMicDeviceId', deviceId);
    }

    setSelectedDeviceId(deviceId);
    
    // Stop current recording if active
    if (isRecording || isPaused) {
      await stopRecording();
    }
    
    // Cleanup current stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
    }
    audioContextRef.current = null;
    
    setIsInitialized(false);
    
    // Re-initialize with new device
    await initializeRecording();
  }, [isRecording, isPaused, stopRecording, initializeRecording]);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
    }
    audioContextRef.current = null;
    
    if (audioURL) {
      URL.revokeObjectURL(audioURL);
    }
    
    setIsRecording(false);
    setIsPaused(false);
    setRecordingTime(0);
    setIsInitialized(false);
    setAudioURL(null);
    setAudioBlob(null);
  }, [audioURL]);

  // Format time as MM:SS
  const formatTime = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  // Auto-initialize on mount
  useEffect(() => {
    if (!isInitialized) {
      console.log('Auto-initializing audio recording...');
      initializeRecording().catch(console.error);
    }
  }, [isInitialized, initializeRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    isRecording,
    isPaused,
    recordingTime: formatTime(recordingTime),
    rawRecordingTime: recordingTime,
    audioBlob,
    audioURL,
    isInitialized,
    error,
    audioLevels,
    availableDevices,
    selectedDeviceId,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    toggleRecording,
    getBase64Audio,
    cleanup,
    initializeRecording,
    changeDevice,
    getAudioDevices
  };
};

export default useAudioRecording; 