import React from 'react';
import { ArrowRight, ArrowUp, Hexagon, ShieldAlert, Network } from 'lucide-react';

interface ModelInsightsCardProps {
  onSelectTechnique: (techId: string) => void;
  onViewDetails: () => void;
}

export const ModelInsightsCard: React.FC<ModelInsightsCardProps> = ({
  onSelectTechnique,
  onViewDetails
}) => {
  const riskFactors = [
    { rank: 1, name: 'Lateral movement (SMB)', confidence: 87 },
    { rank: 2, name: 'Unusual outbound traffic', confidence: 74 },
    { rank: 3, name: 'Privilege escalation indicators', confidence: 68 }
  ];

  const techniques = ['T1021', 'T1059', 'T1078', 'T1003', 'T1140'];

  const keyIndicators = [
    {
      icon: <ArrowUp className="w-3.5 h-3.5 text-[#DE5B49] stroke-[2.5]" />,
      text: 'Suspicious connection patterns'
    },
    {
      icon: <Hexagon className="w-3.5 h-3.5 text-[#DE5B49] stroke-[2.5]" />,
      text: 'New process execution'
    },
    {
      icon: <ShieldAlert className="w-3.5 h-3.5 text-[#DE5B49] stroke-[2.5]" />,
      text: 'Privilege escalation attempt'
    },
    {
      icon: <Network className="w-3.5 h-3.5 text-[#DE5B49] stroke-[2.5]" />,
      text: 'Data exfiltration pattern (predicted)'
    }
  ];

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-[#DE5B49]">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </div>
            <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">
              Model Insights
            </h2>
          </div>

          <button
            onClick={onViewDetails}
            className="flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors"
          >
            <span>View Details</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Top Risk Factors */}
        <div className="mt-3.5">
          <div className="flex items-center justify-between text-[11px] font-semibold text-[#8C96A3] pb-1.5 border-b border-[#F0ECE4]">
            <span>Top Risk Factors</span>
            <span>Confidence</span>
          </div>
          <div className="space-y-1.5 mt-2">
            {riskFactors.map((item) => (
              <div key={item.rank} className="flex items-center justify-between text-xs">
                <span className="text-[#2B3542] font-medium truncate pr-2">
                  <span className="text-[#8E99A8] mr-1">{item.rank}.</span>
                  {item.name}
                </span>
                <span className="font-bold text-[#35404F] text-[11px]">
                  {item.confidence}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Related ATT&CK Techniques */}
        <div className="mt-4 pt-3 border-t border-[#F0ECE4]">
          <div className="text-[11px] font-semibold text-[#8C96A3] mb-2">
            Related ATT&amp;CK Techniques
          </div>
          <div className="flex flex-wrap gap-1.5">
            {techniques.map((tech) => (
              <button
                key={tech}
                onClick={() => onSelectTechnique(tech)}
                className="bg-[#F6F3ED] hover:bg-[#EAE3D7] border border-[#DDD7CD] px-2.5 py-1 rounded-md text-xs font-mono font-semibold text-[#424C58] transition-colors"
                title={`Inspect technique ${tech}`}
              >
                {tech}
              </button>
            ))}
          </div>
        </div>

        {/* Key Indicators */}
        <div className="mt-4 pt-3 border-t border-[#F0ECE4]">
          <div className="text-[11px] font-semibold text-[#8C96A3] mb-2">
            Key Indicators
          </div>
          <div className="space-y-2">
            {keyIndicators.map((ind, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-[#303B48]">
                <div className="shrink-0">{ind.icon}</div>
                <span className="font-medium">{ind.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
