/**
 * Audio optimization utility for immediate playback and caching
 * Preloads common responses and manages audio cache for better performance
 */

// Audio cache for commonly used responses
const AUDIO_CACHE = new Map();
const MAX_CACHE_SIZE = 50;
const CACHE_EXPIRY_TIME = 30 * 60 * 1000; // 30 minutes

// Common phrases that can be preloaded
const COMMON_PHRASES = [
  "Welcome to the automated First Notice of Loss system. I'm here to help you report your loss. To begin, please tell me what happened.",
  "Thank you for providing that information.",
  "Could you please provide more details about",
  "I understand. Let me help you with that.",
  "Is there anything else you'd like to add?",
  "Perfect! I have all the information I need.",
  "Let me process that information for you.",
  "I'm processing your request..."
];

// Audio element pool for immediate playback
const AUDIO_POOL = [];
const POOL_SIZE = 5;

/**
 * Initialize the audio pool with pre-created audio elements
 */
export const initializeAudioPool = () => {
  for (let i = 0; i < POOL_SIZE; i++) {
    const audio = new Audio();
    audio.preload = 'auto';
    audio.load();
    AUDIO_POOL.push(audio);
  }
  console.log(`Audio pool initialized with ${POOL_SIZE} elements`);
};

/**
 * Get an available audio element from the pool
 */
const getAudioElement = () => {
  // Find an available audio element (not currently playing)
  for (const audio of AUDIO_POOL) {
    if (audio.paused || audio.ended) {
      return audio;
    }
  }
  
  // If all are busy, create a new temporary one
  console.log('Audio pool exhausted, creating temporary element');
  const audio = new Audio();
  audio.preload = 'auto';
  return audio;
};

/**
 * Convert base64 audio data to blob URL for immediate playback
 */
export const createAudioBlobUrl = (base64Data) => {
  try {
    // Remove data URL prefix if present
    const base64Audio = base64Data.replace(/^data:audio\/[^;]+;base64,/, '');
    
    // Convert to binary
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Create blob and URL
    const blob = new Blob([bytes], { type: 'audio/wav' });
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error('Failed to create audio blob URL:', error);
    return null;
  }
};

/**
 * Cache audio data with expiry
 */
export const cacheAudio = (text, audioData) => {
  const cacheKey = text.substring(0, 100); // Use first 100 chars as key
  const cacheEntry = {
    audioData,
    blobUrl: createAudioBlobUrl(audioData),
    timestamp: Date.now()
  };
  
  // Add to cache
  AUDIO_CACHE.set(cacheKey, cacheEntry);
  
  // Clean up cache if it gets too large
  if (AUDIO_CACHE.size > MAX_CACHE_SIZE) {
    cleanupAudioCache();
  }
};

/**
 * Get cached audio data
 */
export const getCachedAudio = (text) => {
  const cacheKey = text.substring(0, 100);
  const cacheEntry = AUDIO_CACHE.get(cacheKey);
  
  if (cacheEntry) {
    // Check if cache entry is still valid
    if (Date.now() - cacheEntry.timestamp < CACHE_EXPIRY_TIME) {
      return cacheEntry;
    } else {
      // Remove expired entry
             if (cacheEntry.blobUrl) {
         URL.revokeObjectURL(cacheEntry.blobUrl);
       }
       AUDIO_CACHE.delete(cacheKey);
    }
  }
  
  return null;
};

/**
 * Clean up expired cache entries
 */
const cleanupAudioCache = () => {
  const now = Date.now();
  const expiredKeys = [];
  
  for (const [key, entry] of AUDIO_CACHE.entries()) {
    if (now - entry.timestamp > CACHE_EXPIRY_TIME) {
      expiredKeys.push(key);
      if (entry.blobUrl) {
        URL.revokeObjectURL(entry.blobUrl);
      }
    }
  }
  
  expiredKeys.forEach(key => AUDIO_CACHE.delete(key));
  
  // If still too large, remove oldest entries
  if (AUDIO_CACHE.size > MAX_CACHE_SIZE) {
    const entries = Array.from(AUDIO_CACHE.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
    
    const toRemove = entries.slice(0, AUDIO_CACHE.size - MAX_CACHE_SIZE);
    toRemove.forEach(([key, entry]) => {
      if (entry.blobUrl) {
        URL.revokeObjectURL(entry.blobUrl);
      }
      AUDIO_CACHE.delete(key);
    });
  }
  
  console.log(`Audio cache cleaned up, ${AUDIO_CACHE.size} entries remaining`);
};

/**
 * Play audio immediately with minimal delay
 */
export const playAudioImmediate = (audioData, onPlay = null, onEnd = null) => {
  return new Promise((resolve, reject) => {
    try {
      // Check cache first
      const cached = getCachedAudio(audioData.substring ? audioData.substring(0, 100) : '');
      let blobUrl;
      
      if (cached && cached.blobUrl) {
        blobUrl = cached.blobUrl;
        console.log('Using cached audio for immediate playback');
      } else {
        // Create blob URL for immediate playback
        blobUrl = createAudioBlobUrl(audioData);
        if (!blobUrl) {
          reject(new Error('Failed to create audio blob URL'));
          return;
        }
      }
      
      // Get audio element from pool
      const audio = getAudioElement();
      
      // Set up event handlers
      const handlePlay = () => {
        console.log('Audio playback started');
        if (onPlay) onPlay();
        audio.removeEventListener('play', handlePlay);
      };
      
      const handleEnd = () => {
        console.log('Audio playback ended');
        if (onEnd) onEnd();
        audio.removeEventListener('ended', handleEnd);
        audio.removeEventListener('error', handleError);
        
        // Clean up blob URL if it was created temporarily
        if (!cached) {
          URL.revokeObjectURL(blobUrl);
        }
        
        resolve();
      };
      
      const handleError = (error) => {
        console.error('Audio playback error:', error);
        audio.removeEventListener('play', handlePlay);
        audio.removeEventListener('ended', handleEnd);
        audio.removeEventListener('error', handleError);
        
        if (!cached) {
          URL.revokeObjectURL(blobUrl);
        }
        
        reject(error);
      };
      
      // Attach event listeners
      audio.addEventListener('play', handlePlay);
      audio.addEventListener('ended', handleEnd);
      audio.addEventListener('error', handleError);
      
      // Set source and play
      audio.src = blobUrl;
      audio.currentTime = 0;
      
      // Attempt to play
      const playPromise = audio.play();
      if (playPromise) {
        playPromise.catch(handleError);
      }
      
    } catch (error) {
      reject(error);
    }
  });
};

/**
 * Preload common audio responses for instant playback
 */
export const preloadCommonAudio = async (generateAudioFunction) => {
  console.log('Preloading common audio responses...');
  
  for (const phrase of COMMON_PHRASES) {
    try {
      // Check if already cached
      if (!getCachedAudio(phrase)) {
        // Generate and cache audio
        const audioData = await generateAudioFunction(phrase);
        if (audioData) {
          cacheAudio(phrase, audioData);
          console.log(`Preloaded audio for: ${phrase.substring(0, 50)}...`);
        }
      }
    } catch (error) {
      console.warn(`Failed to preload audio for phrase: ${phrase.substring(0, 50)}...`, error);
    }
  }
  
  console.log('Audio preloading completed');
};

/**
 * Stop all currently playing audio immediately
 */
export const stopAllAudio = () => {
  AUDIO_POOL.forEach(audio => {
    if (!audio.paused) {
      audio.pause();
      audio.currentTime = 0;
    }
  });
  
  // Also stop any audio elements in the document
  const audioElements = document.getElementsByTagName('audio');
  for (let audio of audioElements) {
    if (!audio.paused) {
      audio.pause();
      audio.currentTime = 0;
    }
  }
  
  console.log('All audio playback stopped');
};

/**
 * Get cache statistics for performance monitoring
 */
export const getAudioCacheStats = () => {
  return {
    cacheSize: AUDIO_CACHE.size,
    maxCacheSize: MAX_CACHE_SIZE,
    poolSize: AUDIO_POOL.length,
    activeAudio: AUDIO_POOL.filter(audio => !audio.paused).length
  };
};

/**
 * Clear all audio cache
 */
export const clearAudioCache = () => {
  // Revoke all blob URLs
  for (const [key, entry] of AUDIO_CACHE.entries()) {
    if (entry.blobUrl) {
      URL.revokeObjectURL(entry.blobUrl);
    }
  }
  
  AUDIO_CACHE.clear();
  console.log('Audio cache cleared');
};

// Initialize audio pool on module load
if (typeof window !== 'undefined') {
  // Delay initialization to ensure DOM is ready
  setTimeout(initializeAudioPool, 100);
} 