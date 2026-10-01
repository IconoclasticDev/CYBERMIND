import React from 'react';

export const ProgressionCard: React.FC = () => {
  const steps = [
    { label: 't+1', val: 76, x: 20, y: 50 },
    { label: 't+2', val: 84, x: 50, y: 35 },
    { label: 't+3', val: 91, x: 80, y: 18, tag: 't+3' },
    { label: 't+4', val: 92, x: 110, y: 16 },
    { label: 't+5', val: 88, x: 140, y: 24 }
  ];

  // SVG dimensions for sparkline
  const width = 160;
  const height = 65;

  // Path coordinates
  const pathD = "M 15 52 C 35 48, 40 38, 50 35 C 65 30, 72 20, 80 18 C 95 14, 100 15, 110 16 C 125 18, 130 22, 145 25";
  const areaD = `${pathD} L 145 62 L 15 62 Z`;

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full hover:shadow-md transition-shadow">
      <div className="text-xs font-semibold text-[#667280]">
        Attack Progression (Next 5 Steps)
      </div>

      {/* SVG Chart area */}
      <div className="relative mt-2 px-1">
        <svg viewBox="0 0 160 65" className="w-full h-16 overflow-visible">
          <defs>
            <linearGradient id="coralArea" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#DE5B49" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#DE5B49" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Area fill */}
          <path d={areaD} fill="url(#coralArea)" />

          {/* Curve stroke */}
          <path
            d={pathD}
            fill="none"
            stroke="#DE5B49"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points */}
          <circle cx="20" cy="50" r="3" fill="#DE5B49" stroke="#FFF" strokeWidth="1.5" />
          <text x="20" y="42" textAnchor="middle" fontSize="6.5" fill="#8A94A0" fontFamily="sans-serif">t+1</text>

          <circle cx="50" cy="35" r="3" fill="#DE5B49" stroke="#FFF" strokeWidth="1.5" />
          <text x="50" y="27" textAnchor="middle" fontSize="6.5" fill="#8A94A0" fontFamily="sans-serif">t+2</text>

          {/* Peak point with label */}
          <circle cx="80" cy="18" r="3.5" fill="#DE5B49" stroke="#FFF" strokeWidth="1.5" />
          <rect x="73" y="4" width="14" height="9" rx="2" fill="#FAF6F3" stroke="#E3DDD4" strokeWidth="0.8" />
          <text x="80" y="10.5" textAnchor="middle" fontSize="6" fontWeight="bold" fill="#DE5B49" fontFamily="sans-serif">t+3</text>

          <circle cx="110" cy="16" r="3" fill="#DE5B49" stroke="#FFF" strokeWidth="1.5" />
          <circle cx="140" cy="24" r="3" fill="#DE5B49" stroke="#FFF" strokeWidth="1.5" />
          <text x="140" y="16" textAnchor="middle" fontSize="6.5" fill="#8A94A0" fontFamily="sans-serif">t+5</text>
        </svg>
      </div>

      {/* Percentage metrics row */}
      <div className="grid grid-cols-5 text-center pt-2 border-t border-[#F1EBE2]">
        {steps.map((st) => (
          <div key={st.label}>
            <div className="text-[10px] text-[#8F98A6] font-medium">{st.label}</div>
            <div className="text-[11px] font-bold text-[#353F4C]">{st.val}%</div>
          </div>
        ))}
      </div>
    </div>
  );
};
