import React, { useState } from "react";
import { ArrowRight, X } from "lucide-react";
import type { UIMilestone } from "../lib/adapters";

interface AttackTimelineProps {
  milestones: UIMilestone[];
  onOpenFullTimeline?: () => void;
}

export const AttackTimeline: React.FC<AttackTimelineProps> = ({ milestones, onOpenFullTimeline }) => {
  const [selected, setSelected] = useState<UIMilestone | null>(null);
  if (!milestones.length) return null;
  const shown = milestones.slice(0, 6);

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <div className="text-[#DE5B49]">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20v-6M6 20V10M18 20V4" />
            </svg>
          </div>
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Attack Timeline — Observed → Predicted</h2>
        </div>
        {onOpenFullTimeline && (
          <button onClick={onOpenFullTimeline} className="flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors">
            <span>Forecast Detail</span><ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      <div className="relative px-4 py-2">
        <div className="absolute top-[28px] left-6 right-10 h-0.5 bg-[#E6E0D6] z-0" />
        <div className="absolute top-[24px] right-8 z-0"><ArrowRight className="w-3 h-3 text-[#B0B8C4]" /></div>
        <div className="relative z-10 grid gap-2 text-center" style={{ gridTemplateColumns: `repeat(${shown.length}, minmax(0,1fr))` }}>
          {shown.map((m) => {
            const isSelected = selected?.id === m.id;
            return (
              <div key={m.id} onClick={() => setSelected(isSelected ? null : m)}
                className="flex flex-col items-center cursor-pointer group" role="button" aria-label={`Milestone ${m.stage}`}>
                <span className="font-mono text-xs font-medium text-[#717E8E] mb-1.5 group-hover:text-[#DE5B49] transition-colors">{m.time}</span>
                <div className={`w-3.5 h-3.5 rounded-full border-2 border-white shadow-xs transition-transform duration-200 group-hover:scale-125 ${
                  isSelected ? "ring-4 ring-[#DE5B49]/20 scale-125" : ""
                } ${m.status === "predicted" ? "border-dashed" : ""}`} style={{ backgroundColor: m.color }} />
                <div className="mt-2 text-xs font-bold text-[#1E2732] leading-tight group-hover:text-[#DE5B49] transition-colors">{m.stage}</div>
                <div className="text-[11px] text-[#7E8B99] mt-0.5 font-medium">{m.detail}</div>
                {m.status === "predicted" && <div className="text-[9px] uppercase tracking-wider text-[#8A58D8] font-bold mt-0.5">predicted</div>}
                {m.status === "current" && <div className="text-[9px] uppercase tracking-wider text-[#2EAA58] font-bold mt-0.5">observed</div>}
              </div>
            );
          })}
        </div>
      </div>

      {selected && (
        <div className="mt-4 p-3.5 bg-[#FAF8F5] border border-[#E9E3D9] rounded-xl text-xs transition-all animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-2 border-b border-[#ECE5DA]">
            <div className="flex items-center gap-2">
              <span className="font-bold text-stone-900">{selected.stage}</span>
              <span className="font-mono text-[11px] text-[#717E8E]">{selected.time}</span>
              <span className="bg-[#EFECE5] text-[#556170] px-1.5 py-0.5 rounded text-[10px] font-mono font-medium">{selected.mitreId}</span>
            </div>
            <button onClick={() => setSelected(null)} className="text-stone-400 hover:text-stone-600 transition-colors cursor-pointer" aria-label="Close detail">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="mt-2 text-[#465261] leading-relaxed">{selected.description}</p>
          <div className="mt-2.5 flex flex-wrap gap-2 items-center">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#8C98A6]">Trace:</span>
            {selected.iocs.map((ioc, i) => (
              <span key={i} className="font-mono text-[10px] bg-white border border-[#E2DCD2] px-2 py-0.5 rounded text-[#374151]">{ioc}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
