import { useState, useRef } from 'react';

export const useVoiceRecorder = (onStop: (base64: string) => void) => {
  const [isRecording, setIsRecording] = useState(false);
  const [visualizerData, setVisualizerData] = useState<number[]>(new Array(20).fill(0));
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const animationFrameRef = useRef<number>();
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Setup audio context for visualization
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.fftSize = 64;
      
      analyserRef.current = analyser;
      audioContextRef.current = audioContext;
      
      // Setup recording
      const mediaRecorder = new MediaRecorder(stream); // Let browser choose best format (usually webm/opus)
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' }); // Chrome default
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64String = (reader.result as string).split(',')[1];
          onStop(base64String);
        };
        reader.readAsDataURL(blob);
        
        // Cleanup visualization
        cancelAnimationFrame(animationFrameRef.current!);
        stream.getTracks().forEach(track => track.stop());
        audioContext.close();
      };

      mediaRecorder.start();
      setIsRecording(true);
      visualize();

    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Microphone access denied or not available.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const visualize = () => {
    if (!analyserRef.current) return;
    
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Simplify data to fewer bars for UI
    const relevantData = Array.from(dataArray).slice(0, 20); // Take first 20 bins
    const normalizedData = relevantData.map(val => val / 255);
    
    setVisualizerData(normalizedData);
    animationFrameRef.current = requestAnimationFrame(visualize);
  };

  return {
    isRecording,
    startRecording,
    stopRecording,
    visualizerData
  };
};
