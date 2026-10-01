import React from 'react';
import { ShieldCheck, ArrowRight } from 'lucide-react';

interface SystemHealthCardProps {
  onViewDetails?: () => void;
}

export const SystemHealthCard: React.FC<SystemHealthCardProps> = ({
  onViewDetails
}) => {
  const services = [
    { name: 'Model Inference', status: 'Operational', latency: '42ms' },
    { name: 'Data Pipeline', status: 'Operational', latency: '1.2M EPS' },
    { name: 'Sandbox (Docker)', status: 'Operational', latency: '8 Active' },
    { name: 'WebSocket', status: 'Operational', latency: 'Connected' },
    { name: 'Database', status: 'Operational', latency: '8ms' }
  ];

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <div className="text-[#2EAA58]">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">
            System Health
          </h2>
        </div>

        <div className="text-xs text-[#7A8696] font-medium mt-1">
          All Systems Operational
        </div>

        {/* Services status list */}
        <div className="space-y-2 mt-3.5">
          {services.map((srv) => (
            <div key={srv.name} className="flex items-center justify-between text-xs py-0.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#2EAA58]" />
                <span className="font-medium text-[#2B3542]">{srv.name}</span>
              </div>
              <span className="font-mono text-[11px] text-[#8692A2]">{srv.latency}</span>
            </div>
          ))}
        </div>
      </div>

      {/* View Details link */}
      <div className="pt-3 border-t border-[#F2ECE4] mt-3">
        <button
          onClick={onViewDetails}
          className="w-full flex items-center justify-end gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors"
        >
          <span>View Details</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
