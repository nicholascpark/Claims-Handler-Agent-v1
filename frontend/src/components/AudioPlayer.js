import React, { useRef, useEffect } from 'react';

const AudioPlayer = ({ 
  audioData, 
  onPlay, 
  onEnd, 
  autoPlay = true,
  isInitial = false,
  loop = false
}) => {
  const audioRef = useRef(null);

  useEffect(() => {
    if (audioData && audioRef.current) {
      try {
        const audioBlob = new Blob(
          [Uint8Array.from(atob(audioData), c => c.charCodeAt(0))], 
          { type: 'audio/wav' }
        );
        
        // Check if blob is valid before creating object URL
        if (audioBlob && audioBlob.size > 0) {
          const audioUrl = URL.createObjectURL(audioBlob);
          
          audioRef.current.src = audioUrl;
          audioRef.current.loop = loop; // Set loop property
          audioRef.current.load();

          // Always attempt autoplay
          const playPromise = audioRef.current.play();
          if (playPromise !== undefined) {
            playPromise
              .then(() => {
                console.log('Audio autoplay started successfully');
                if (onPlay) onPlay();
              })
              .catch(error => {
                // Autoplay restrictions (e.g. Chrome, Safari on iOS) often
                // block audio with sound until the user has interacted with
                // the page.  When that happens we register a one-off user
                // interaction handler that will retry playback on the first
                // click / key press.
                console.log('Autoplay was blocked, waiting for user interaction...', error);

                const resumePlayback = () => {
                  if (!audioRef.current) return;
                  audioRef.current.play().then(() => {
                    console.log('Audio playback started after user interaction');
                    if (onPlay) onPlay();
                  }).catch(err => {
                    console.error('Playback still blocked:', err);
                  });

                  document.removeEventListener('click', resumePlayback);
                  document.removeEventListener('keydown', resumePlayback);
                };

                document.addEventListener('click', resumePlayback, { once: true });
                document.addEventListener('keydown', resumePlayback, { once: true });
              });
          }

          // Cleanup – stop playback and revoke URL to avoid memory leaks and unintended replays
          return () => {
            if (audioRef.current) {
              try {
                audioRef.current.pause();
                audioRef.current.currentTime = 0;
              } catch (e) {
                // No-op – element may already be gone
              }
            }
            if (audioUrl) {
              URL.revokeObjectURL(audioUrl);
            }
          };
        }
      } catch (error) {
        console.error('Error creating audio blob:', error);
      }
    }
  }, [audioData, loop]);

  const handleAudioEnded = () => {
    if (onEnd) onEnd();
  };

  if (!audioData) return null;

  return (
    <audio
      ref={audioRef}
      onEnded={handleAudioEnded}
      preload="auto"
      autoPlay={autoPlay}
      playsInline
      style={{ display: 'none' }}
    />
  );
};

export default AudioPlayer; 