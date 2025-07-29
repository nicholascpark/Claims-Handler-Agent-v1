// Audio test utility to debug microphone and conversion issues

export const testMicrophoneAccess = async () => {
  try {
    console.log('Testing microphone access...');
    
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100,
      },
    });
    
    console.log('✅ Microphone access granted');
    console.log('Audio tracks:', stream.getAudioTracks().map(track => ({
      label: track.label || 'Unknown device',
      enabled: track.enabled,
      readyState: track.readyState,
      settings: track.getSettings()
    })));
    
    // Test if MediaRecorder is supported
    if (typeof MediaRecorder !== 'undefined') {
      console.log('✅ MediaRecorder is supported');
      
      // Test supported MIME types
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
        'audio/wav'
      ];
      
      console.log('Supported MIME types:');
      mimeTypes.forEach(mimeType => {
        const supported = MediaRecorder.isTypeSupported(mimeType);
        console.log(`  ${mimeType}: ${supported ? '✅' : '❌'}`);
      });
    } else {
      console.error('❌ MediaRecorder is not supported');
    }
    
    // Test AudioContext
    if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
      console.log('✅ AudioContext is supported');
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      console.log('AudioContext state:', audioContext.state);
      console.log('Sample rate:', audioContext.sampleRate);
    } else {
      console.error('❌ AudioContext is not supported');
    }
    
    // Clean up
    stream.getTracks().forEach(track => track.stop());
    
    return { success: true, message: 'All audio tests passed' };
  } catch (error) {
    console.error('❌ Audio test failed:', error);
    return { success: false, message: error.message, error };
  }
};

export const testAudioConversion = async () => {
  try {
    console.log('Testing audio conversion...');
    
    // Create a simple test audio buffer
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const sampleRate = audioContext.sampleRate;
    const duration = 1; // 1 second
    const buffer = audioContext.createBuffer(1, sampleRate * duration, sampleRate);
    
    // Fill with a simple sine wave
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.sin(2 * Math.PI * 440 * i / sampleRate) * 0.1; // 440Hz tone at low volume
    }
    
    console.log('✅ Test audio buffer created');
    console.log('Sample rate:', sampleRate);
    console.log('Duration:', duration);
    console.log('Samples:', data.length);
    
    return { success: true, buffer, message: 'Audio conversion test setup complete' };
  } catch (error) {
    console.error('❌ Audio conversion test failed:', error);
    return { success: false, message: error.message, error };
  }
};

// Run tests when this module is imported in development
if (process.env.NODE_ENV === 'development') {
  window.audioTest = {
    testMicrophoneAccess,
    testAudioConversion,
    runAllTests: async () => {
      console.log('🎤 Running audio diagnostics...');
      const micTest = await testMicrophoneAccess();
      const conversionTest = await testAudioConversion();
      
      console.log('\n📋 Test Results:');
      console.log('Microphone access:', micTest.success ? '✅' : '❌', micTest.message);
      console.log('Audio conversion:', conversionTest.success ? '✅' : '❌', conversionTest.message);
      
      return {
        microphoneAccess: micTest,
        audioConversion: conversionTest,
        allPassed: micTest.success && conversionTest.success
      };
    }
  };
} 