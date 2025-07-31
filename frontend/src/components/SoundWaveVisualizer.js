import React, { useRef, useEffect, useState, memo, useMemo, useCallback } from 'react';
import styled from 'styled-components';

const SoundWaveContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  padding: 0 12px;
  transition: all 0.3s ease;
  opacity: ${props => props.$show ? 1 : 0};
  transform: ${props => props.$show ? 'scaleY(1)' : 'scaleY(0.5)'};
  width: 100%;
`;

const CanvasContainer = styled.div`
  width: 200px;
  height: 32px;
  border-radius: 4px;
  overflow: hidden;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const VisualizerCanvas = styled.canvas`
  width: 100%;
  height: 100%;
  border-radius: 4px;
`;

const PlaybackText = styled.div`
  color: #ffc107;
  font-size: 11px;
  font-weight: 500;
  margin-left: 8px;
  display: flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
  
  &::before {
    content: '🔊';
    font-size: 12px;
  }
`;

const PlaceholderText = styled.div`
  color: #666;
  font-size: 12px;
  font-style: italic;
  opacity: 0.7;
  text-align: center;
`;

// Enhanced frequency bar visualizer using native Canvas API
const FrequencyVisualizer = memo(({ 
  audioLevels, 
  isRecording, 
  isPaused, 
  isAISpeaking,
  show 
}) => {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const timeRef = useRef(0);
  const [smoothedLevels, setSmoothLevels] = useState(new Array(10).fill(0));

  // Animation loop for smooth rendering
  const animate = useCallback(() => {
    if (!show) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    
    // Set canvas size for high DPI displays
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);
    
         // Update time for animations (very slow for graceful movement)
     timeRef.current += 0.002;
     
     // Update smoothed levels
            setSmoothLevels(prev => {
         const targetBarCount = isAISpeaking ? 4 : 10;
         const target = audioLevels.length > 0 ? audioLevels : new Array(targetBarCount).fill(0);
         const padded = [...target, ...new Array(Math.max(0, targetBarCount - target.length)).fill(0)].slice(0, targetBarCount);
         
         return prev.slice(0, targetBarCount).map((current, i) => {
         let targetLevel;
         
                  if (isAISpeaking) {
           // Rhythmic AI speaking patterns - slower to match recording speed
           const wave1 = Math.sin(timeRef.current * 2 + i * 0.3) * 0.25;
           const wave2 = Math.sin(timeRef.current * 3 + i * 0.7) * 0.15;
           const wave3 = Math.cos(timeRef.current * 1.5 + i * 0.5) * 0.1;
           const baseLevel = 0.4 + Math.sin(i * 0.4) * 0.2; // Varied heights per bar
           targetLevel = baseLevel + wave1 + wave2 + wave3;
         } else if (isPaused) {
           // Paused state with same animation as recording but scaled by audio presence
           const baseLevel = padded[i] || 0;
           const hasAudio = baseLevel > 0.05; // Check if there's meaningful audio
           const pausedAnimation = Math.sin(timeRef.current * 0.8 + i * 0.4) * (hasAudio ? 0.25 : 0.05);
           targetLevel = baseLevel + pausedAnimation;
         } else {
           // Recording state with enhanced sensitivity, scaled by audio presence
           const baseLevel = padded[i] || 0;
           const hasAudio = baseLevel > 0.05; // Check if there's meaningful audio
           const recordingAnimation = isRecording ? Math.sin(timeRef.current * 0.8 + i * 0.4) * (hasAudio ? 0.25 : 0.05) : 0;
           targetLevel = baseLevel + recordingAnimation;
         }
         
         // Smooth interpolation (much slower for recording for graceful movement)
         const smoothFactor = isRecording ? 0.05 : 0.12;
         return current + (targetLevel - current) * smoothFactor;
       });
     });
    
         // Draw frequency bars (4 thick bars for AI speaking, 10 for others)
     const barCount = isAISpeaking ? 4 : 10;
     const barWidth = rect.width / barCount;
    const maxHeight = rect.height - 4;
    
    for (let i = 0; i < barCount; i++) {
      const level = smoothedLevels[i] || 0;
      const x = i * barWidth;
      
                    // Calculate height with more pronounced artistic variation
       const hasAudio = level > 0.1;
       const minHeight = hasAudio ? 3 : 1; // Smaller minimum when no audio
       const baseHeight = Math.max(minHeight, level * maxHeight);
       let artisticVariation;
       
       if (isAISpeaking) {
         // Multiple layered sine waves for AI speaking - slower and thicker bars
         artisticVariation = Math.sin(timeRef.current * 6 + i * 0.6) * 4 + 
                           Math.cos(timeRef.current * 4 + i * 0.4) * 2 +
                           Math.sin(timeRef.current * 8 + i * 0.8) * 1;
       } else if (isRecording) {
         // Much more pronounced vertical movement for recording, scaled by audio presence
         const amplitude = hasAudio ? 5 : 1; // Much smaller when no audio
         const secondaryAmplitude = hasAudio ? 3 : 0.5;
         artisticVariation = Math.sin(timeRef.current * 3 + i * 0.5) * amplitude + 
                           Math.cos(timeRef.current * 2 + i * 0.3) * secondaryAmplitude;
       } else {
         // Paused state with same scaling as recording
         const amplitude = hasAudio ? 5 : 1; // Much smaller when no audio
         const secondaryAmplitude = hasAudio ? 3 : 0.5;
         artisticVariation = Math.sin(timeRef.current * 3 + i * 0.5) * amplitude + 
                           Math.cos(timeRef.current * 2 + i * 0.3) * secondaryAmplitude;
       }
       
       const artisticHeight = baseHeight + artisticVariation;
       const finalMinHeight = hasAudio ? 3 : 1;
       const height = Math.min(maxHeight, Math.max(finalMinHeight, artisticHeight));
      
             // Create gradient based on state
       const gradient = ctx.createLinearGradient(0, rect.height - height, 0, rect.height);
       
       if (isAISpeaking) {
         // Cool blue-purple gradient for AI speaking with gentle pulsing
         const intensity = level;
         const pulse = Math.sin(timeRef.current * 3) * 0.2 + 0.8;
         const hueShift = Math.sin(timeRef.current * 2 + i * 0.3) * 30; // Color variation across bars
         gradient.addColorStop(0, `rgba(${Math.max(80, 120 - intensity * 100) * pulse}, ${Math.max(100, 180 - intensity * 80) * pulse}, ${Math.max(200, 255 - intensity * 55) * pulse}, 1)`);
         gradient.addColorStop(0.5, `rgba(${80 + hueShift}, ${120 + hueShift * 0.5}, ${200}, 0.8)`);
         gradient.addColorStop(1, `rgba(${60 * pulse}, ${90 * pulse}, ${180 * pulse}, 1)`);
               } else if (isRecording) {
          // Dynamic red gradient for recording with very gentle pulsing
          const intensity = level;
          const pulse = Math.sin(timeRef.current * 1.5) * 0.15 + 0.85;
          gradient.addColorStop(0, `rgba(${255 * pulse}, ${Math.max(30, 80 - intensity * 255) * pulse}, ${Math.max(30, 80 - intensity * 255) * pulse}, 1)`);
          gradient.addColorStop(1, `rgba(${180 * pulse}, 30, 30, 1)`);
       } else if (isPaused) {
         // Golden gradient for paused
         const intensity = level;
         const pulse = Math.sin(timeRef.current * 3) * 0.2 + 0.8;
         gradient.addColorStop(0, `rgba(${255 * pulse}, ${Math.max(150, 220 - intensity * 255) * pulse}, 20, 1)`);
         gradient.addColorStop(1, `rgba(${200 * pulse}, ${140 * pulse}, 0, 1)`);
       } else {
         // Neutral gradient
         const intensity = level * 150;
         gradient.addColorStop(0, `rgba(${100 + intensity}, ${100 + intensity}, ${120 + intensity}, 1)`);
         gradient.addColorStop(1, `rgba(60, 60, 80, 1)`);
       }
      
      // Draw the bar
      ctx.fillStyle = gradient;
      ctx.fillRect(x + 1, rect.height - height, barWidth - 2, height);
      
             // Add glow effect for active states
       if (isAISpeaking || isRecording || isPaused) {
         ctx.shadowBlur = isAISpeaking ? 12 : 8;
         if (isAISpeaking) {
           ctx.shadowColor = 'rgba(100, 150, 255, 0.7)';
           ctx.fillStyle = 'rgba(120, 180, 255, 0.2)';
         } else if (isRecording) {
           ctx.shadowColor = 'rgba(255, 80, 80, 0.6)';
           ctx.fillStyle = 'rgba(255, 80, 80, 0.3)';
         } else {
           ctx.shadowColor = 'rgba(255, 200, 0, 0.6)';
           ctx.fillStyle = 'rgba(255, 200, 0, 0.3)';
         }
         ctx.fillRect(x + 1, rect.height - height, barWidth - 2, height);
         ctx.shadowBlur = 0;
       }
      
             // Add subtle highlight line at the top
       const highlightThreshold = hasAudio ? 5 : 2;
       if (height > highlightThreshold) {
         ctx.strokeStyle = isAISpeaking ? 'rgba(200, 220, 255, 0.6)' : 'rgba(255, 255, 255, 0.5)';
         ctx.lineWidth = 0.5;
         ctx.beginPath();
         ctx.moveTo(x + 1, rect.height - height);
         ctx.lineTo(x + barWidth - 1, rect.height - height);
         ctx.stroke();
       }
     }
     
     // Add floating particles for active states
     ctx.shadowBlur = 0;
     if (isRecording) {
       for (let i = 0; i < 4; i++) {
         const x = (timeRef.current * 30 + i * 50) % (rect.width + 20) - 10;
         const y = rect.height/2 + Math.sin(timeRef.current * 1 + i) * 8;
         const alpha = (Math.sin(timeRef.current * 0.8 + i) * 0.5 + 0.5);
         const size = 2 + Math.sin(timeRef.current * 1.2 + i) * 1.5;
         
         ctx.fillStyle = `rgba(255, 120, 120, ${alpha})`;
         ctx.beginPath();
         ctx.arc(x, y, size, 0, Math.PI * 2);
         ctx.fill();
       }
     } else if (isAISpeaking) {
       // Gentle floating particles for AI speaking - more subtle and ethereal
       for (let i = 0; i < 6; i++) {
         const x = (timeRef.current * 60 + i * 40) % (rect.width + 30) - 15;
         const y = rect.height/2 + Math.sin(timeRef.current * 2 + i * 0.7) * 10;
         const alpha = (Math.sin(timeRef.current * 1.5 + i * 0.5) * 0.4 + 0.3);
         const size = 1.5 + Math.sin(timeRef.current * 3 + i * 0.8) * 1;
         
         ctx.fillStyle = `rgba(150, 200, 255, ${alpha})`;
         ctx.beginPath();
         ctx.arc(x, y, size, 0, Math.PI * 2);
         ctx.fill();
       }
     }
    
         animationFrameRef.current = requestAnimationFrame(animate);
   }, [audioLevels, isRecording, isPaused, isAISpeaking, show, smoothedLevels]);

  // Start/stop animation based on show prop
  useEffect(() => {
    if (show) {
      animate();
    } else {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    }
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [show, animate]);

  if (!show) return null;

  return (
    <CanvasContainer>
      <VisualizerCanvas ref={canvasRef} />
    </CanvasContainer>
  );
});

FrequencyVisualizer.displayName = 'FrequencyVisualizer';

// Optimized random pattern generator with memoization
const generateStaticPattern = (barCount = 10) => {
  return Array.from({ length: barCount }, (_, index) => {
    const baseLevel = 0.3 + Math.sin(index * 0.5) * 0.2;
    const variation = (Math.random() - 0.5) * 0.1;
    return Math.max(0.1, Math.min(0.8, baseLevel + variation));
  });
};

const SoundWaveVisualizer = memo(({ 
  audioLevels = [], 
  isRecording = false, 
  isPaused = false, 
  isAISpeaking = false,
  show = false,
  audioURL = null
}) => {
  const [playbackLevels, setPlaybackLevels] = useState([]);

  // Memoize static pattern generation
  const staticPattern = useMemo(() => {
    if (isPaused && audioURL && !playbackLevels.length) {
      return generateStaticPattern(10); // Always 10 bars for paused state
    }
    return playbackLevels;
  }, [isPaused, audioURL, playbackLevels.length]);

  // Generate playback visualization when paused and audioURL is available
  useEffect(() => {
    if (isPaused && audioURL && !playbackLevels.length) {
      setPlaybackLevels(staticPattern);
    } else if (!isPaused && playbackLevels.length > 0) {
      setPlaybackLevels([]);
    }
  }, [isPaused, audioURL, playbackLevels.length, staticPattern]);

  // Convert audio levels to normalized format
  const normalizedLevels = useMemo(() => {
    if (isPaused && staticPattern.length > 0) {
      return staticPattern;
    }
    
    // Normalize and extend audio levels
         const targetBarCount = isAISpeaking ? 4 : 10;
    const levels = audioLevels.length > 0 ? audioLevels : new Array(targetBarCount).fill(0);
    return levels.slice(0, targetBarCount).map(level => Math.max(0, Math.min(1, level / 100))); // Normalize to 0-1
  }, [audioLevels, isPaused, isAISpeaking, staticPattern]);

  // Early return for better performance
  if (!show) {
    return (
      <SoundWaveContainer $show={false}>
        <PlaceholderText>
          Audio visualization appears during recording
        </PlaceholderText>
      </SoundWaveContainer>
    );
  }

  return (
    <SoundWaveContainer $show={show}>
      <FrequencyVisualizer
        audioLevels={normalizedLevels}
        isRecording={isRecording}
        isPaused={isPaused}
        isAISpeaking={isAISpeaking}
        show={show}
      />
      {isPaused && audioURL && (
        <PlaybackText>
          Ready for Review
        </PlaybackText>
      )}
    </SoundWaveContainer>
  );
});

SoundWaveVisualizer.displayName = 'SoundWaveVisualizer';

export default SoundWaveVisualizer; 