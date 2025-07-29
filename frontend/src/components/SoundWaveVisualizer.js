import React, { useRef, useEffect, useState } from 'react';
import styled, { keyframes, css } from 'styled-components';

const waveAnimation = keyframes`
  0%, 100% {
    height: 8px;
  }
  50% {
    height: var(--wave-height, 30px);
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
  gap: 3px;
  height: 40px;
  padding: 0 20px;
  transition: all 0.3s ease;
  opacity: ${props => props.show ? 1 : 0};
  transform: ${props => props.show ? 'scaleY(1)' : 'scaleY(0.5)'};
`;

const WaveBar = styled.div`
  width: 4px;
  height: ${props => props.height || 8}px;
  background: ${props => {
    if (props.isRecording) return '#dc3545';
    if (props.isPaused) return '#ffc107';
    return '#6c757d';
  }};
  border-radius: 2px;
  transition: all 0.1s ease;
  
  ${props => props.isRecording && css`
    --wave-height: ${props.height || 30}px;
    animation: ${waveAnimation} ${0.5 + Math.random() * 0.5}s infinite alternate;
    animation-delay: ${props.delay || 0}s;
  `}
  
  ${props => props.isPaused && css`
    background: linear-gradient(135deg, #ffc107 0%, #ffca28 100%);
    box-shadow: 0 2px 4px rgba(255, 193, 7, 0.3);
    animation: ${playbackAnimation} 2s infinite;
    animation-delay: ${props.delay || 0}s;
  `}
`;

const PlaybackText = styled.div`
  color: #ffc107;
  font-size: 12px;
  font-weight: 500;
  margin-left: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  
  &::before {
    content: '🔊';
    font-size: 14px;
  }
`;

const PlaceholderText = styled.div`
  color: #666;
  font-size: 14px;
  font-style: italic;
  opacity: 0.7;
`;

const SoundWaveVisualizer = ({ 
  audioLevels = [], 
  isRecording = false, 
  isPaused = false, 
  show = false,
  audioURL = null
}) => {
  const [playbackLevels, setPlaybackLevels] = useState([]);
  const audioRef = useRef(null);
  const analyzerRef = useRef(null);

  // Generate playback visualization when paused and audioURL is available
  useEffect(() => {
    if (isPaused && audioURL && !playbackLevels.length) {
      // Generate static visualization pattern based on recorded audio
      const staticLevels = Array.from({ length: 8 }, (_, index) => {
        // Create a wave pattern that simulates recorded audio levels
        const baseLevel = 20 + Math.sin(index * 0.8) * 15;
        const variation = Math.random() * 10;
        return Math.max(8, Math.min(35, baseLevel + variation));
      });
      setPlaybackLevels(staticLevels);
    } else if (!isPaused) {
      setPlaybackLevels([]);
    }
  }, [isPaused, audioURL, playbackLevels.length]);

  // Generate 8 bars for visualization
  const bars = Array.from({ length: 8 }, (_, index) => {
    let height;
    
    if (isPaused && playbackLevels.length > 0) {
      // Use playback levels when paused
      height = playbackLevels[index];
    } else {
      // Use live audio levels when recording
      const level = audioLevels[index] || 0;
      height = Math.max(8, Math.min(35, level * 0.35 + 8));
    }
    
    const delay = index * 0.1;
    
    return (
      <WaveBar
        key={index}
        height={height}
        isRecording={isRecording}
        isPaused={isPaused}
        delay={delay}
      />
    );
  });

  if (!show) {
    return (
      <SoundWaveContainer show={false}>
        <PlaceholderText>
          Audio visualization will appear here during recording
        </PlaceholderText>
      </SoundWaveContainer>
    );
  }

  return (
    <SoundWaveContainer show={show}>
      {bars}
      {isPaused && audioURL && (
        <PlaybackText>
          Recorded Audio - Ready for Review
        </PlaybackText>
      )}
    </SoundWaveContainer>
  );
};

export default SoundWaveVisualizer; 