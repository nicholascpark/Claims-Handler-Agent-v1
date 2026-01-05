interface CostMeterProps {
  durationSeconds: number; // For demo estimation
}

export const CostMeter = ({ durationSeconds }: CostMeterProps) => {
  // Rough estimate logic: $0.06/min
  const cost = (durationSeconds / 60) * 0.06;
  const maxBudget = 1.00; // Demo budget
  const percent = Math.min((cost / maxBudget) * 100, 100);

  return (
    <div className="bg-white/90 backdrop-blur border border-gray-200 rounded-xl p-4 shadow-lg w-64">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-bold text-gray-800 text-sm">💰 Session Cost</h4>
        <span className="font-mono text-sm font-semibold text-primary-700">${cost.toFixed(3)}</span>
      </div>
      
      <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden mb-2">
        <div 
          className="h-full bg-gradient-to-r from-green-500 to-primary-600 transition-all duration-1000"
          style={{ width: `${percent}%` }}
        />
      </div>
      
      <div className="flex justify-between text-[10px] text-gray-500">
        <span>Voice: $0.02</span>
        <span>AI: $0.04</span>
      </div>
    </div>
  );
};
