import React, { useEffect, useState } from "react";
import { Search, ShieldCheck, ShieldX, Loader2 } from "lucide-react";
import type { HealthResponse } from "../lib/api";
import type { WsStatus } from "../lib/live";

interface HeaderProps {
  health: HealthResponse | null;
  ws: WsStatus;
  provenance: string;
  onOpenCommandPalette: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, ws, provenance, onOpenCommandPalette }) => {
  const [clock, setClock] = useState<string>("");
  const [date, setDate] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setClock(now.toLocaleTimeString([], { hour12: false }));
      setDate(now.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }));
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  const model = health?.model;
  const modelUp = !!model?.available;

  const wsColor = ws === "online" ? "bg-[#2EAA58]" : ws === "offline" ? "bg-[#DE5B49]" : "bg-[#E58B44]";
  const wsText = ws === "online" ? "Live stream connected" : ws === "offline" ? "Live stream offline — retrying" : "Connecting…";

  return (
    <header className="w-full bg-[#F7F5F0] border-b border-[#EAE6DF] px-3 sm:px-6 py-3 flex items-center justify-between gap-2 sticky top-0 z-30 select-none">
      <div className="flex items-center gap-8 min-w-0 sm:min-w-[220px]">
        <div>
          <span className="font-editorial text-lg sm:text-2xl font-bold tracking-[0.14em] text-[#192027] uppercase">CYBERMIND</span>
          <div className="text-[10px] uppercase tracking-[0.25em] text-[#7A8492] font-medium mt-[-2px]">
            Predict <span className="mx-0.5 opacity-60">·</span> Prevent <span className="mx-0.5 opacity-60">·</span> Protect
          </div>
        </div>
      </div>

      <div className="hidden md:block flex-1 max-w-2xl px-4">
        <button
          onClick={onOpenCommandPalette}
          className="w-full bg-white border border-[#E4DFD6] hover:border-[#D1C9BE] text-left px-3.5 py-2 rounded-lg flex items-center justify-between shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-all group"
          title="Search hosts and events (Ctrl+K)"
        >
          <div className="flex items-center gap-2.5 text-[#8A94A0] group-hover:text-[#636C77] text-xs">
            <Search className="w-3.5 h-3.5" />
            <span className="truncate">Search hosts, events, techniques…</span>
          </div>
          <div className="flex items-center gap-1 bg-[#F5F2EC] border border-[#DDD7CD] px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-[#7A8492]">
            <span>Ctrl</span><span>K</span>
          </div>
        </button>
      </div>

      <div className="flex items-center gap-2 lg:gap-6 min-w-0 lg:min-w-[360px] justify-end">
        {/* Provenance badge — honest data labeling */}
        <span
          className={`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide border ${
            provenance === "REAL DATASET" || provenance === "LIVE"
              ? "bg-[#EBF7EE] border-[#C3E8CA] text-[#1E7B3E]"
              : provenance === "REPLAY"
              ? "bg-[#EEF2FB] border-[#C9D4EE] text-[#4B68B8]"
              : "bg-[#F1F4F8] border-[#DCE3EC] text-[#556375]"
          }`}
          title="Every value on this dashboard is traceable to the pipeline: telemetry → state → forecast → recommendation → experiment."
        >
          {provenance === "—" ? "NO DATA" : provenance}
        </span>

        {/* Model status */}
        <div className="hidden sm:flex items-center gap-2.5" title={model?.checkpoint ?? ""}>
          {model === null ? (
            <Loader2 className="w-4 h-4 animate-spin text-[#8A94A0]" />
          ) : modelUp ? (
            <ShieldCheck className="w-5 h-5 text-[#2EAA58]" />
          ) : (
            <ShieldX className="w-5 h-5 text-[#E58B44]" />
          )}
          <div className="text-left">
            <div className="text-xs font-semibold text-[#1F262E] leading-tight">
              {model === null ? "Checking…" : modelUp ? "Model Online" : "Model Not Loaded"}
            </div>
            <div className="text-[10px] text-[#7A8492] leading-tight font-mono">
              {model === null ? "" : modelUp ? `${model.version} · ${model.device}` : "check model path in Settings"}
            </div>
          </div>
        </div>

        {/* WS status */}
        <div className="hidden lg:flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            <div className={`w-2.5 h-2.5 rounded-full ${wsColor}`} />
            {ws === "online" && <div className="absolute w-4 h-4 rounded-full bg-[#2EAA58]/25 animate-ping" />}
          </div>
          <div className="text-left">
            <div className="text-xs font-semibold text-[#1F262E] leading-tight">{wsText.split(" — ")[0]}</div>
            <div className="text-[10px] text-[#7A8492] leading-tight">{wsText.includes("—") ? wsText.split(" — ")[1] : ws === "online" ? "streaming" : ""}</div>
          </div>
        </div>

        <div className="hidden lg:block text-right px-2 py-1 rounded hover:bg-[#EFECE5] transition-colors">
          <div className="text-[11px] font-medium text-[#505A66] leading-tight">{date}</div>
          <div className="text-[11px] font-mono font-medium text-[#7A8492] leading-tight">{clock}</div>
        </div>
      </div>
    </header>
  );
};
