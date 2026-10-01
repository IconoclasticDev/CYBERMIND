import React, { useState } from "react";
import { Database, TrendingUp, GitBranch, ShieldCheck, ArrowRight } from "lucide-react";

type Phase = "ingest" | "forecast" | "simulate" | "validate";

interface ClosedLoopHUDProps {
  currentPhase?: Phase;
  onSelectPhase?: (phase: Phase) => void;
}

export const ClosedLoopHUD: React.FC<ClosedLoopHUDProps> = ({ currentPhase: propPhase, onSelectPhase }) => {
  const [internalPhase, setInternalPhase] = useState<Phase>("ingest");
  const currentPhase = propPhase ?? internalPhase;
  const handleSelect = (p: Phase) => {
    setInternalPhase(p);
    onSelectPhase?.(p);
  };

  const steps = [
    {
      id: "ingest" as const,
      num: "01",
      title: "Ingest State",
      subtitle: "Telemetry & PCAP / CSV",
      icon: Database,
    },
    {
      id: "forecast" as const,
      num: "02",
      title: "Forecast Branches",
      subtitle: "GNN + Temporal Transformer",
      icon: TrendingUp,
    },
    {
      id: "simulate" as const,
      num: "03",
      title: "Simulate What-If",
      subtitle: "Defensive Counterfactuals",
      icon: GitBranch,
    },
    {
      id: "validate" as const,
      num: "04",
      title: "Adversarial Validate",
      subtitle: "Sandbox Probes & 1-Click Patch",
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-3 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-1 mb-2 px-1">
        <div className="min-w-0 text-[11px] font-extrabold uppercase tracking-wider text-[#171F27] flex flex-wrap items-center gap-2">
          <span className="w-2 h-2 shrink-0 rounded-full bg-[#DE5B49] animate-pulse" />
          <span>CYBERMIND Closed-Loop World Model Architecture</span>
          <span className="text-[10px] text-[#8C95A3] font-mono normal-case font-medium">
            (Forecast &rarr; Simulate &rarr; Validate &rarr; Calibrate)
          </span>
        </div>
        <div className="text-[10px] font-mono text-[#707C8C] hidden sm:block">
          Slide 12: Judge Demo Flow
        </div>
      </div>

      <div className="grid grid-cols-1 min-[480px]:grid-cols-2 lg:grid-cols-4 gap-2">
        {steps.map((step, idx) => {
          const isActive = currentPhase === step.id;
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              onClick={() => handleSelect(step.id)}
              className={`min-w-0 p-2.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between gap-2.5 ${
                isActive
                  ? "bg-[#FAF4EE] border-[#DE5B49] shadow-xs text-[#DE5B49]"
                  : "bg-[#FAF8F5] border-[#E8E2D7] hover:border-[#D0C8BB] text-[#556171] hover:text-[#1C232B]"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                    isActive ? "bg-[#DE5B49] text-white" : "bg-white border border-[#DDD6CC] text-[#707C8C]"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono font-bold opacity-60">{step.num}</span>
                    <span className="text-xs font-bold truncate text-[#1C232B]">{step.title}</span>
                  </div>
                  <div className="text-[10px] text-[#707C8C] truncate font-mono">{step.subtitle}</div>
                </div>
              </div>

              {idx < steps.length - 1 && (
                <ArrowRight className="w-3.5 h-3.5 text-[#DDD6CC] shrink-0 hidden md:block" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
