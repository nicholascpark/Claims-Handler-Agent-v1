import React, { useRef, useEffect, useState, memo, useMemo, useCallback } from 'react';
import styled, { keyframes, css } from 'styled-components';

// Memoized keyframes to avoid recreation
const waveAnimation = keyframes`
  0%, 100% {
    height: 6px;
  }
  50% {
    height: var(--wave-height, 24px);
  }
`;

const playbackAnimation = keyframes`
  0% {
    opacity: 0.3;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.3;
  }
`;

const SoundWaveContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 32px;
  padding: 0 12px;
  transition: all 0.3s ease;
  opacity: ${props => props.$show ? 1 : 0};
  transform: ${props => props.$show ? 'scaleY(1)' : 'scaleY(0.5)'};
  width: 100%;
`;

const WaveBar = styled.div.attrs(props => ({
  style: {
    height: `${props.$height || 6}px`,
    animationDelay: `${props.$delay || 0}s`,
    '--wave-height': `${props.$height || 24}px`,
  },
}))`
  width: 3px;
  background: ${props => {
    if (props.$isRecording) return '#dc3545';
    if (props.$isPaused) return '#ffc107';
    return '#6c757d';
  }};
  border-radius: 1.5px;
  transition: height 0.1s ease;
  will-change: height;
  
  ${props => props.$isRecording && css`
    animation: ${waveAnimation} ${0.5 + Math.random() * 0.5}s infinite alternate;
  `}
  
  ${props => props.$isPaused && css`
    background: linear-gradient(135deg, #ffc107 0%, #ffca28 100%);
    box-shadow: 0 1px 2px rgba(255, 193, 7, 0.3);
    animation: ${playbackAnimation} 2s infinite;
  `}
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

// Optimized random pattern generator with memoization
const generateStaticPattern = () => {
  return Array.from({ length: 8 }, (_, index) => {
    const baseLevel = 16 + Math.sin(index * 0.8) * 10;
    const variation = (Math.random() - 0.5) * 6; // More natural variation
    return Math.max(6, Math.min(28, baseLevel + variation));
  });
};

const SoundWaveVisualizer = memo(({ 
  audioLevels = [], 
  isRecording = false, 
  isPaused = false, 
  show = false,
  audioURL = null
}) => {
  const [playbackLevels, setPlaybackLevels] = useState([]);
  const animationFrameRef = useRef(null);
  const lastUpdateRef = useRef(0);

  // Memoize static pattern generation
  const staticPattern = useMemo(() => {
    if (isPaused && audioURL && !playbackLevels.length) {
      return generateStaticPattern();
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

  // Optimized level calculation with throttling
  const calculateLevel = useCallback((audioLevel, index) => {
    if (isPaused && staticPattern.length > 0) {
      return staticPattern[index];
    }
    
    // Use smoother scaling for live audio
    const level = audioLevel || 0;
    return Math.max(6, Math.min(28, level * 0.5 + 8)); // Adjusted for compact size
  }, [isPaused, staticPattern]);

  // Memoized bars generation with optimized rendering
  const bars = useMemo(() => {
    return Array.from({ length: 8 }, (_, index) => {
      const audioLevel = audioLevels[index] || 0;
      const height = calculateLevel(audioLevel, index);
      const delay = index * 0.1;
      
      return (
        <WaveBar
          key={index}
          $height={height}
          $isRecording={isRecording}
          $isPaused={isPaused}
          $delay={delay}
        />
      );
    });
  }, [audioLevels, isRecording, isPaused, calculateLevel]);

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
      {bars}
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