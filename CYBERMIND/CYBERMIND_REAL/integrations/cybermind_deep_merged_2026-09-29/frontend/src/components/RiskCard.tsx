import React from 'react';
import { ArrowUp } from 'lucide-react';

interface RiskCardProps {
  score?: number;
  delta?: string;
  level?: string;
  timeframe?: string;
}

export const RiskCard: React.FC<RiskCardProps> = ({
  score = 72,
  delta = '+18%',
  level = 'High',
  timeframe = '(last 5 min)'
}) => {
  // SVG donut calculation
  const radius = 38;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full hover:shadow-md transition-shadow">
      <div className="text-xs font-semibold text-[#667280]">
        Overall Risk Level
      </div>

      <div className="flex items-center justify-between mt-2.5">
        {/* Radial donut gauge */}
        <div className="relative flex items-center justify-center w-24 h-24">
          <svg className="w-24 h-24 -rotate-90 transform" viewBox="0 0 100 100">
            {/* Background ring */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              stroke="#EDE8DE"
              strokeWidth={strokeWidth}
              fill="transparent"
            />
            {/* Value progress arc */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              stroke="#DE5B49"
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
              className="transition-all duration-1000 ease-out"
            />
          </svg>

          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <div className="flex items-baseline justify-center">
              <span className="text-2xl font-extrabold text-[#19222C] tracking-tight">{score}</span>
              <span className="text-[11px] font-medium text-[#8F98A5] ml-0.5">/100</span>
            </div>
            <span className="text-xs font-bold text-[#DE5B49] leading-none mt-0.5">
              {level}
            </span>
          </div>
        </div>

        {/* Change indicator */}
        <div className="text-right">
          <div className="inline-flex items-center text-sm font-bold text-[#DE5B49]">
            <ArrowUp className="w-3.5 h-3.5 stroke-[2.5] mr-0.5" />
            <span>{delta}</span>
          </div>
          <div className="text-[11px] text-[#7F8B99] mt-0.5">
            {timeframe}
          </div>
        </div>
      </div>
    </div>
  );
};
