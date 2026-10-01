import React from 'react';
import { ArrowUpRight } from 'lucide-react';

interface PredictedStageCardProps {
  predictedStage?: string;
  window?: string;
  confidence?: number;
}

export const PredictedStageCard: React.FC<PredictedStageCardProps> = ({
  predictedStage = 'Persistence',
  window = 'in 2–4 steps',
  confidence = 81
}) => {
  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full hover:shadow-md transition-shadow">
      <div className="text-xs font-semibold text-[#667280]">
        Predicted Next Stage
      </div>

      <div className="flex items-center gap-3.5 mt-2.5">
        <div className="w-11 h-11 rounded-xl bg-[#E58B44] flex items-center justify-center text-white shadow-sm shrink-0">
          <ArrowUpRight className="w-6 h-6 stroke-[2.4]" />
        </div>
        <div>
          <div className="text-base font-bold text-[#19222C] leading-snug">
            {predictedStage}
          </div>
          <div className="text-xs text-[#7F8B99] mt-0.5">
            {window}
          </div>
        </div>
      </div>

      <div className="mt-4 pt-2">
        <div className="text-xs text-[#7F8B99]">
          Confidence: <span className="font-semibold text-[#505C6B]">{confidence}%</span>
        </div>
        <div className="w-full bg-[#EFECE5] h-1.5 rounded-full mt-2 overflow-hidden">
          <div
            className="bg-[#E58B44] h-full rounded-full transition-all duration-700"
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>
    </div>
  );
};
