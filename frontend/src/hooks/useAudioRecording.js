import { useState, useRef, useCallback, useEffect } from 'react';

const useAudioRecording = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState(null);
  const [audioLevels, setAudioLevels] = useState(new Array(8).fill(0));
  const [availableDevices, setAvailableDevices] = useState([]);
  // Persist preferred microphone in localStorage so the selection made on the start screen
  // is honoured later when the recording hook is re-created (e.g. inside the chat interface).
  // We read the value lazily to avoid accessing window during server-side rendering.
  const [selectedDeviceId, setSelectedDeviceId] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('preferredMicDeviceId') || null;
    }
    return null;
  });

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const animationFrameRef = useRef(null);
  const analyzerRef = useRef(null);
  const audioContextRef = useRef(null);

  // Get available audio input devices
  const getAudioDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter(device => device.kind === 'audioinput');
      console.log('Available audio input devices:', audioInputs);
      setAvailableDevices(audioInputs);
      
      // Select the first available device if none selected
      if (audioInputs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(audioInputs[0].deviceId);
        console.log('Auto-selected device:', audioInputs[0].label || 'Default microphone');
        if (typeof window !== 'undefined') {
          localStorage.setItem('preferredMicDeviceId', audioInputs[0].deviceId);
        }
      }
      
      return audioInputs;
    } catch (err) {
      console.error('Error getting audio devices:', err);
      setError(`Failed to get microphone devices: ${err.message}`);
      return [];
    }
  }, [selectedDeviceId]);

  // Initialize audio recording
  const initializeRecording = useCallback(async () => {
    try {
      setError(null);
      console.log('Initializing audio recording...');
      
      // Get available devices first
      await getAudioDevices();
      
      const constraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
          deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
        },
      };

      console.log('Requesting microphone access with constraints:', constraints);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      // Verify the stream has audio tracks
      const audioTracks = stream.getAudioTracks();
      if (audioTracks.length === 0) {
        throw new Error('No audio tracks found in the stream');
      }
      
      console.log('Successfully got microphone stream with', audioTracks.length, 'audio tracks');
      console.log('Active audio track:', audioTracks[0].label || 'Unknown device');

      streamRef.current = stream;

      // Set up audio analysis for visualization
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyzer = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      analyzer.fftSize = 256;
      microphone.connect(analyzer);
      
      audioContextRef.current = audioContext;
      analyzerRef.current = analyzer;

      // Check if MediaRecorder is supported
      if (!MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        console.warn('WebM/Opus not supported, trying alternatives...');
      }

      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = ''; // Let the browser choose
          }
        }
      }

      console.log('Using MIME type:', mimeType || 'browser default');

      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        console.log('Data available event fired, size:', event.data.size, 'bytes');
        console.log('Event data type:', event.data.type);
        console.log('Total chunks so far:', chunksRef.current.length);
        
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
          console.log('Chunk added. New chunk count:', chunksRef.current.length);
        } else {
          console.warn('Received empty data chunk');
        }
      };

      mediaRecorder.onstop = () => {
        console.log('=== MediaRecorder stopped ===');
        console.log('Total chunks collected:', chunksRef.current.length);
        console.log('Chunk sizes:', chunksRef.current.map(chunk => chunk.size));
        
        if (chunksRef.current.length === 0) {
          console.error('No audio chunks were collected during recording');
          setError('No audio data was recorded. Please check your microphone and try again.');
          return;
        }

        // Calculate total size
        const totalSize = chunksRef.current.reduce((total, chunk) => total + chunk.size, 0);
        console.log('Total audio data size:', totalSize, 'bytes');

        if (totalSize === 0) {
          console.error('All audio chunks are empty');
          setError('Audio recording failed - no audio data captured. Please check your microphone permissions.');
          return;
        }
        
        const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType });
        console.log('Created blob with size:', blob.size, 'bytes, type:', blob.type);
        setAudioBlob(blob);
        setAudioURL(URL.createObjectURL(blob));
        chunksRef.current = [];
      };

      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setError(`Recording error: ${event.error.message}`);
      };

      setIsInitialized(true);
      console.log('Audio recording initialized successfully');
    } catch (err) {
      console.error('Audio recording initialization error:', err);
      setError(`Failed to initialize recording: ${err.message}`);
    }
  }, [selectedDeviceId, getAudioDevices]);

  // Start recording
  const startRecording = useCallback(async () => {
    console.log('=== Starting recording ===');
    console.log('isInitialized:', isInitialized);
    console.log('MediaRecorder exists:', !!mediaRecorderRef.current);
    console.log('Stream exists:', !!streamRef.current);

    if (!isInitialized) {
      console.log('Not initialized, initializing recording...');
      await initializeRecording();
    }

    if (mediaRecorderRef.current && streamRef.current) {
      try {
        setError(null);
        setAudioBlob(null);
        
        // Clean up previous audio URL if it exists
        if (audioURL) {
          URL.revokeObjectURL(audioURL);
        }
        setAudioURL(null);

        // Verify stream is active and has audio tracks
        const audioTracks = streamRef.current.getAudioTracks();
        console.log('Audio tracks available:', audioTracks.length);
        if (audioTracks.length === 0) {
          throw new Error('No audio tracks found in the stream');
        }

        // Check if tracks are enabled and live
        const activeTrack = audioTracks[0];
        console.log('Primary audio track:', {
          label: activeTrack.label,
          enabled: activeTrack.enabled,
          readyState: activeTrack.readyState,
          muted: activeTrack.muted
        });

        if (activeTrack.readyState !== 'live') {
          throw new Error('Audio track is not live');
        }

        if (activeTrack.muted) {
          console.warn('Audio track is muted');
        }

        // Test microphone input level
        if (analyzerRef.current) {
          const analyzer = analyzerRef.current;
          const dataArray = new Uint8Array(analyzer.frequencyBinCount);
          analyzer.getByteFrequencyData(dataArray);
          const avgLevel = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
          console.log('Current microphone input level:', avgLevel);
        }
        
        console.log('Starting MediaRecorder...');
        console.log('MediaRecorder state before start:', mediaRecorderRef.current.state);
        mediaRecorderRef.current.start(100); // Collect data every 100ms
        console.log('MediaRecorder state after start:', mediaRecorderRef.current.state);
        
        setIsRecording(true);
        setIsPaused(false);
        setRecordingTime(0);

        // Start timer
        timerRef.current = setInterval(() => {
          setRecordingTime(prev => prev + 1);
        }, 1000);

        // Start audio level visualization
        startAudioVisualization();
        console.log('Recording started successfully');
      } catch (err) {
        console.error('Failed to start recording:', err);
        setError(`Failed to start recording: ${err.message}`);
      }
    } else {
      console.error('MediaRecorder or stream not available');
      console.error('MediaRecorder:', mediaRecorderRef.current);
      console.error('Stream:', streamRef.current);
      setError('Recording not properly initialized. Please refresh and try again.');
    }
  }, [isInitialized, initializeRecording, audioURL]);

  // Pause recording
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      console.log('Pausing recording...');
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      
      // Pause timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      stopAudioVisualization();
    }
  }, [isRecording, isPaused]);

  // Resume recording
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      console.log('Resuming recording...');
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      
      // Resume timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
      startAudioVisualization();
    }
  }, [isRecording, isPaused]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && (isRecording || isPaused)) {
      console.log('Stopping recording...');
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      stopAudioVisualization();
    }
  }, [isRecording, isPaused]);

  // Toggle recording (start/pause/resume)
  const toggleRecording = useCallback(() => {
    if (!isRecording) {
      startRecording();
    } else if (isPaused) {
      resumeRecording();
    } else {
      pauseRecording();
    }
  }, [isRecording, isPaused, startRecording, pauseRecording, resumeRecording]);

  // Start audio visualization
  const startAudioVisualization = useCallback(() => {
    if (!analyzerRef.current) return;

    const analyzer = analyzerRef.current;
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const updateLevels = () => {
      if (!isRecording || isPaused) return;

      analyzer.getByteFrequencyData(dataArray);
      
      // Calculate average amplitude for each bar
      const barWidth = Math.floor(bufferLength / 8);
      const newLevels = [];
      
      for (let i = 0; i < 8; i++) {
        let sum = 0;
        for (let j = 0; j < barWidth; j++) {
          sum += dataArray[i * barWidth + j];
        }
        const average = sum / barWidth;
        newLevels.push(Math.min(100, (average / 255) * 100));
      }
      
      setAudioLevels(newLevels);
      animationFrameRef.current = requestAnimationFrame(updateLevels);
    };

    updateLevels();
  }, [isRecording, isPaused]);

  // Stop audio visualization
  const stopAudioVisualization = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    setAudioLevels(new Array(8).fill(0));
  }, []);

  // Convert WebM audio to WAV format
  const convertToWav = useCallback(async (webmBlob) => {
    return new Promise((resolve, reject) => {
      let audioContext = null;
      
      try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const fileReader = new FileReader();
        
        fileReader.onload = async (e) => {
          try {
            const arrayBuffer = e.target.result;
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            
            // Convert to WAV
            const wav = audioBufferToWav(audioBuffer);
            const wavBlob = new Blob([wav], { type: 'audio/wav' });
            
            // Close the AudioContext
            if (audioContext && audioContext.state !== 'closed') {
              audioContext.close();
            }
            
            resolve(wavBlob);
          } catch (error) {
            console.error('Error converting audio:', error);
            // Close the AudioContext on error
            if (audioContext && audioContext.state !== 'closed') {
              audioContext.close();
            }
            reject(error);
          }
        };
        
        fileReader.onerror = (error) => {
          // Close the AudioContext on file read error
          if (audioContext && audioContext.state !== 'closed') {
            audioContext.close();
          }
          reject(error);
        };
        
        fileReader.readAsArrayBuffer(webmBlob);
      } catch (error) {
        // Close the AudioContext on immediate error
        if (audioContext && audioContext.state !== 'closed') {
          audioContext.close();
        }
        reject(error);
      }
    });
  }, []);

  // Helper function to convert AudioBuffer to WAV
  const audioBufferToWav = (audioBuffer) => {
    const length = audioBuffer.length;
    const numberOfChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const bytesPerSample = 2; // 16-bit
    const blockAlign = numberOfChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = length * blockAlign;
    const bufferSize = 44 + dataSize; // WAV header is 44 bytes

    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view = new DataView(arrayBuffer);
    
    // WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true); // PCM chunk size
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true); // bits per sample
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
  const getBase64Audio = useCallback(async () => {
    return new Promise(async (resolve, reject) => {
      console.log('=== getBase64Audio called ===');
      console.log('audioBlob exists:', !!audioBlob);
      console.log('audioBlob size:', audioBlob?.size);
      console.log('mediaRecorder state:', mediaRecorderRef.current?.state);
      console.log('chunks collected:', chunksRef.current?.length);

      if (!audioBlob) {
        console.error('No audio blob available');
        reject(new Error('No audio recorded'));
        return;
      }

      console.log('Converting audio blob to base64, blob size:', audioBlob.size);
      
      if (audioBlob.size === 0) {
        console.error('Audio blob is empty - no audio data was captured');
        reject(new Error('Audio blob is empty - no audio data was captured. Please check your microphone permissions and try again.'));
        return;
      }

      try {
        // Convert WebM to WAV first
        console.log('Converting WebM to WAV format...');
        const wavBlob = await convertToWav(audioBlob);
        console.log('Converted to WAV, size:', wavBlob.size);

        if (wavBlob.size === 0) {
          console.error('WAV conversion resulted in empty blob');
          reject(new Error('Audio conversion failed - resulting file is empty'));
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result.split(',')[1];
          console.log('Successfully converted to base64, length:', base64.length);
          if (!base64 || base64.length === 0) {
            reject(new Error('Base64 conversion failed - no data generated'));
            return;
          }
          resolve(base64);
        };
        reader.onerror = () => {
          console.error('Failed to convert audio to base64');
          reject(new Error('Failed to convert audio to base64'));
        };
        reader.readAsDataURL(wavBlob);
      } catch (error) {
        console.error('Error in audio conversion:', error);
        reject(new Error(`Audio conversion failed: ${error.message}`));
      }
    });
  }, [audioBlob, convertToWav]);

  // Change microphone device
  const changeDevice = useCallback(async (deviceId) => {
    console.log('Changing to device:', deviceId);

    // Persist the user selection so that future hook instances pick it up automatically.
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferredMicDeviceId', deviceId);
    }

    setSelectedDeviceId(deviceId);
    
    // If currently recording, stop it first
    if (isRecording || isPaused) {
      stopRecording();
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

  // Cleanup
  const cleanup = useCallback(() => {
    console.log('Cleaning up audio recording...');
    
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
    
    // Clean up object URL
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

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  // Auto-initialize recording on mount
  useEffect(() => {
    const initOnMount = async () => {
      if (!isInitialized) {
        await initializeRecording();
      }
    };
    
    initOnMount();
  }, []); // Empty dependency array ensures this runs only once on mount

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
    getAudioDevices,
  };
};

export default useAudioRecording; 