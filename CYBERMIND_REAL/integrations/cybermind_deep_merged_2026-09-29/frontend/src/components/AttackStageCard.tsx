import React from 'react';
import { Target, Crosshair } from 'lucide-react';

interface AttackStageCardProps {
  currentStage?: string;
  confidence?: number;
}

export const AttackStageCard: React.FC<AttackStageCardProps> = ({
  currentStage = 'Lateral Movement',
  confidence = 78
}) => {
  const stages = [
    { id: 'recon', label: 'Recon', completed: true },
    { id: 'initial-access', label: 'Initial Access', completed: true },
    { id: 'execution', label: 'Execution', completed: true },
    { id: 'lateral-movement', label: 'Lateral Movement', active: true },
    { id: 'persistence', label: 'Persistence', pending: true },
    { id: 'c2', label: 'C2', pending: true },
    { id: 'exfiltration', label: 'Exfiltration', pending: true }
  ];

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full hover:shadow-md transition-shadow">
      <div>
        <div className="text-xs font-semibold text-[#667280]">
          Current Attack Stage
        </div>

        {/* Stage icon & name */}
        <div className="flex items-center gap-3.5 mt-2.5">
          <div className="w-11 h-11 rounded-xl bg-[#DE5B49] flex items-center justify-center text-white shadow-sm shrink-0">
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <line x1="22" y1="12" x2="18" y2="12"/>
              <line x1="6" y1="12" x2="2" y2="12"/>
              <line x1="12" y1="6" x2="12" y2="2"/>
              <line x1="12" y1="22" x2="12" y2="18"/>
            </svg>
          </div>
          <div>
            <div className="text-base font-bold text-[#19222C] leading-snug">
              {currentStage}
            </div>
            <div className="text-xs text-[#7F8B99] mt-0.5">
              Confidence: <span className="font-semibold text-[#505C6B]">{confidence}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* 7-stage progress chain */}
      <div className="mt-4 pt-2">
        <div className="relative flex items-center justify-between px-1">
          {/* Connecting line */}
          <div className="absolute left-2 right-2 top-1.5 h-0.5 bg-[#E6E0D5] z-0" />
          
          {stages.map((stage) => {
            const isTarget = stage.active;
            return (
              <div key={stage.id} className="relative z-10 flex flex-col items-center">
                <div
                  className={`w-3 h-3 rounded-full border-2 transition-all ${
                    isTarget
                      ? 'bg-[#DE5B49] border-[#DE5B49] ring-4 ring-[#DE5B49]/20 scale-125'
                      : stage.completed
                      ? 'bg-[#EAE5DC] border-[#D4CBBF]'
                      : 'bg-white border-[#DCD6CA]'
                  }`}
                />
                <span
                  className={`text-[9px] mt-1.5 whitespace-nowrap text-center ${
                    isTarget
                      ? 'font-bold text-[#DE5B49]'
                      : 'font-normal text-[#8E97A4]'
                  }`}
                  style={{ maxWidth: '42px', lineHeight: '1.1' }}
                >
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
