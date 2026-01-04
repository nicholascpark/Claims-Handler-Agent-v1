import { ClaimPayload } from '../types';
import { CheckCircle2, Circle, FileText } from 'lucide-react';
import clsx from 'clsx';

interface PayloadDisplayProps {
  payload: ClaimPayload;
  isComplete: boolean;
}

const FIELD_LABELS: Record<string, string> = {
  incident_date: "Date of Incident",
  incident_time: "Time of Incident",
  incident_location: "Location",
  vehicle_info: "Vehicle Details",
  damage_description: "Damage Description",
  injury_info: "Injuries",
  police_report: "Police Report",
  other_party_info: "Other Parties"
};

export const PayloadDisplay: React.FC<PayloadDisplayProps> = ({ payload, isComplete }) => {
  const fields = Object.keys(FIELD_LABELS);
  const filledCount = fields.filter(f => payload[f] && payload[f] !== 'unknown').length;
  const progress = Math.round((filledCount / fields.length) * 100);

  return (
    <div className="h-full bg-slate-50 border-l border-slate-200 flex flex-col">
      <div className="p-6 border-b border-slate-200 bg-white">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-5 h-5 text-primary-600" />
          <h2 className="font-bold text-slate-800">Claim Details</h2>
        </div>
        <p className="text-sm text-slate-500 mb-4">
          Live extraction from conversation
        </p>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-semibold uppercase tracking-wider text-slate-500">
            <span>Completion</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div 
              className={clsx(
                "h-full rounded-full transition-all duration-500 ease-out",
                isComplete ? "bg-green-500" : "bg-primary-500"
              )}
              style={{ width: `${progress}%` }} 
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {fields.map(field => {
          const value = payload[field];
          const isFilled = value && value !== 'unknown' && value !== 'Not provided';
          
          return (
            <div key={field} className="group">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 shrink-0">
                  {isFilled ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500 fill-green-50" />
                  ) : (
                    <Circle className="w-5 h-5 text-slate-300" />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className={clsx(
                    "text-sm font-medium mb-1",
                    isFilled ? "text-slate-800" : "text-slate-400"
                  )}>
                    {FIELD_LABELS[field]}
                  </h3>
                  <div className={clsx(
                    "text-sm p-3 rounded-lg border transition-colors",
                    isFilled 
                      ? "bg-white border-slate-200 text-slate-700 shadow-sm" 
                      : "bg-slate-50/50 border-transparent text-slate-400 italic"
                  )}>
                    {isFilled ? value : "Pending..."}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {isComplete && (
        <div className="p-6 bg-green-50 border-t border-green-100">
          <div className="flex items-center gap-3 text-green-700">
            <CheckCircle2 className="w-6 h-6" />
            <div>
              <p className="font-bold">Claim Ready for Review</p>
              <p className="text-sm opacity-90">All required information collected.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
