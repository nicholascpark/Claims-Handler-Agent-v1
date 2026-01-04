import { Mic } from 'lucide-react';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import clsx from 'clsx';

interface VoiceRecorderProps {
  onRecordComplete: (base64Audio: string) => void;
  isLoading: boolean;
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({ onRecordComplete, isLoading }) => {
  const { isRecording, startRecording, stopRecording, visualizerData } = useVoiceRecorder(onRecordComplete);

  const handleClick = () => {
    if (isLoading) return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center gap-6 py-4">
      {/* Visualizer */}
      <div className="h-12 flex items-center justify-center gap-1 min-w-[200px]">
        {isRecording ? (
          visualizerData.map((value, i) => (
            <div
              key={i}
              className="w-1.5 bg-primary-500 rounded-full transition-all duration-75"
              style={{
                height: `${Math.max(10, value * 48)}px`,
                opacity: 0.5 + value * 0.5
              }}
            />
          ))
        ) : (
          <div className="text-sm font-medium text-slate-400">
            Tap microphone to speak
          </div>
        )}
      </div>

      {/* Main Button */}
      <button
        onClick={handleClick}
        disabled={isLoading}
        className={clsx(
          "relative group w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300",
          isLoading ? "opacity-50 cursor-not-allowed" : "hover:scale-105 active:scale-95 cursor-pointer",
          isRecording 
            ? "bg-red-500 shadow-xl shadow-red-500/30" 
            : "bg-primary-600 shadow-xl shadow-primary-600/30 hover:shadow-primary-600/50"
        )}
      >
        {/* Ripple Effect when recording */}
        {isRecording && (
          <span className="absolute inset-0 rounded-full border-2 border-red-500 animate-ping opacity-75" />
        )}
        
        {isRecording ? (
          <div className="w-8 h-8 rounded-sm bg-white" /> // Stop square
        ) : (
          <Mic className="w-8 h-8 text-white" />
        )}
      </button>
      
      <p className={clsx(
        "text-sm font-medium transition-colors duration-300",
        isRecording ? "text-red-500" : "text-slate-500"
      )}>
        {isRecording ? "Listening..." : "Ready"}
      </p>
    </div>
  );
};
