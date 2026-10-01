import React from "react";
import { ArrowUp, ArrowUpRight, TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { Forecast, ForecastStep } from "../lib/api";
import { STAGE_SHORT_NAMES } from "../lib/adapters";

const CARD = "bg-white border border-[#EAE6DF] rounded-2xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full hover:shadow-md transition-shadow";

/* ------------------------------- RiskCard ------------------------------- */
export const RiskCard: React.FC<{ forecast: Forecast | null; ready: boolean }> = ({ forecast, ready }) => {
  const cur = forecast?.current;
  const risk = cur?.risk;
  const score = risk != null ? Math.round(risk * 100) : null;
  const level = score == null ? "—" : score >= 75 ? "Critical" : score >= 50 ? "High" : score >= 25 ? "Medium" : "Low";
  const color = score == null ? "#8F98A5" : score >= 75 ? "#B33A2B" : score >= 50 ? "#DE5B49" : score >= 25 ? "#E58B44" : "#2EAA58";
  const first = forecast?.steps?.[0]?.risk;
  const last = forecast?.horizon?.risk;
  const delta = first != null && last != null ? Math.round((last - first) * 100) : null;

  const radius = 38, sw = 8, circ = 2 * Math.PI * radius;
  const offset = score == null ? circ : circ - (score / 100) * circ;

  return (
    <div className={CARD}>
      <div className="text-xs font-semibold text-[#667280]">Infiltration Risk (model score)</div>
      <div className="flex items-center justify-between mt-2.5">
        <div className="relative flex items-center justify-center w-24 h-24">
          <svg className="w-24 h-24 -rotate-90 transform" viewBox="0 0 100 100" aria-hidden>
            <circle cx="50" cy="50" r={radius} stroke="#EDE8DE" strokeWidth={sw} fill="transparent" />
            {score != null && (
              <circle cx="50" cy="50" r={radius} stroke={color} strokeWidth={sw} strokeDasharray={circ}
                strokeDashoffset={offset} strokeLinecap="round" fill="transparent" className="transition-all duration-1000 ease-out" />
            )}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <div className="flex items-baseline justify-center">
              <span className="text-2xl font-extrabold text-[#19222C] tracking-tight">{score ?? "—"}</span>
              <span className="text-[11px] font-medium text-[#8F98A5] ml-0.5">/100</span>
            </div>
            <span className="text-xs font-bold leading-none mt-0.5" style={{ color }}>{level}</span>
          </div>
        </div>
        <div className="text-right">
          {delta != null ? (
            <div className={`inline-flex items-center text-sm font-bold ${delta > 0 ? "text-[#DE5B49]" : delta < 0 ? "text-[#2EAA58]" : "text-[#7F8B99]"}`}>
              {delta > 0 ? <TrendingUp className="w-3.5 h-3.5 mr-0.5" /> : delta < 0 ? <TrendingDown className="w-3.5 h-3.5 mr-0.5" /> : <Minus className="w-3.5 h-3.5 mr-0.5" />}
              <span>{delta > 0 ? "+" : ""}{delta}</span>
            </div>
          ) : (
            <div className="text-sm font-bold text-[#7F8B99]">—</div>
          )}
          <div className="text-[11px] text-[#7F8B99] mt-0.5">horizon Δ (K={forecast?.k ?? "—"})</div>
        </div>
      </div>
      {!ready && <div className="text-[10px] text-[#8C96A3] mt-2">Insufficient observation windows — feed telemetry or start a scenario.</div>}
    </div>
  );
};

/* ---------------------------- AttackStageCard ---------------------------- */
export const AttackStageCard: React.FC<{ forecast: Forecast | null; dominantStage: number }> = ({ forecast, dominantStage }) => {
  const cur = forecast?.current;
  const stageId = cur?.stage_id ?? dominantStage ?? 0;
  const conf = cur?.confidence;
  const chain = ["Recon", "Initial Access", "Execution", "Lateral", "C2", "Impact"];
  const activeIdx = Math.min(3, stageId * 2); // coarse 4-stage → 6-node chain visual
  return (
    <div className={CARD}>
      <div className="text-xs font-semibold text-[#667280]">Current Attack Stage</div>
      <div className="flex items-center gap-3.5 mt-2.5">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center text-white shadow-sm shrink-0"
          style={{ backgroundColor: stageId === 0 ? "#2EAA58" : stageId === 1 ? "#E58B44" : "#DE5B49" }}>
          <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="22" y1="12" x2="18" y2="12" /><line x1="6" y1="12" x2="2" y2="12" />
            <line x1="12" y1="6" x2="12" y2="2" /><line x1="12" y1="22" x2="12" y2="18" />
          </svg>
        </div>
        <div>
          <div className="text-base font-bold text-[#19222C] leading-snug">{STAGE_SHORT_NAMES[stageId] ?? "Unknown"}</div>
          <div className="text-xs text-[#7F8B99] mt-0.5">
            stage confidence: <span className="font-semibold text-[#505C6B]">{conf != null ? `${Math.round(conf * 100)}%` : "—"}</span>
          </div>
        </div>
      </div>
      <div className="mt-4 pt-2">
        <div className="relative grid grid-cols-6 gap-0.5 items-start px-1">
          <div className="absolute left-2 right-2 top-1.5 h-0.5 bg-[#E6E0D5] z-0" />
          {chain.map((label, i) => {
            const isTarget = i === activeIdx;
            const done = i < activeIdx;
            return (
              <div key={label} className="relative z-10 min-w-0 flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full border-2 transition-all ${
                  isTarget ? "bg-[#DE5B49] border-[#DE5B49] ring-4 ring-[#DE5B49]/20 scale-125"
                  : done ? "bg-[#EAE5DC] border-[#D4CBBF]" : "bg-white border-[#DCD6CA]"}`} />
                <span className={`w-full text-[9px] mt-1.5 break-words text-center ${isTarget ? "font-bold text-[#DE5B49]" : "font-normal text-[#8E97A4]"}`}
                  style={{ lineHeight: 1.1 }}>{label}</span>
              </div>
            );
          })}
        </div>
        <div className="text-[9px] text-[#98A2AF] mt-2">Stage mapping is a research proxy (see knowledge/stage_mapping.yaml), aligned with MITRE ATT&amp;CK.</div>
      </div>
    </div>
  );
};

/* --------------------------- PredictedStageCard -------------------------- */
export const PredictedStageCard: React.FC<{ forecast: Forecast | null }> = ({ forecast }) => {
  const horizon = forecast?.horizon;
  const conf = forecast?.confidence;
  const stageId = horizon?.stage_id;
  const stageName = stageId != null ? STAGE_SHORT_NAMES[stageId] : null;
  return (
    <div className={CARD}>
      <div className="text-xs font-semibold text-[#667280]">Predicted Stage at t+K</div>
      <div className="flex items-center gap-3.5 mt-2.5">
        <div className="w-11 h-11 rounded-xl bg-[#E58B44] flex items-center justify-center text-white shadow-sm shrink-0">
          <ArrowUpRight className="w-6 h-6 stroke-[2.4]" />
        </div>
        <div>
          <div className="text-base font-bold text-[#19222C] leading-snug">{stageName ?? "—"}</div>
          <div className="text-xs text-[#7F8B99] mt-0.5">in {forecast?.k ?? "—"} steps · risk {horizon?.risk != null ? `${Math.round(horizon.risk * 100)}%` : "—"}</div>
        </div>
      </div>
      <div className="mt-4 pt-2">
        <div className="text-xs text-[#7F8B99]">
          Model confidence: <span className="font-semibold text-[#505C6B]">{conf != null ? `${Math.round(conf * 100)}%` : "—"}</span>
          {forecast?.ood_flag && <span className="ml-2 text-[#DE5B49] font-semibold">OOD HIGH</span>}
        </div>
        <div className="w-full bg-[#EFECE5] h-1.5 rounded-full mt-2 overflow-hidden">
          <div className="bg-[#E58B44] h-full rounded-full transition-all duration-700"
            style={{ width: `${conf != null ? Math.round(conf * 100) : 0}%` }} />
        </div>
        {forecast?.ood_flag && (
          <div className="text-[10px] text-[#B33A2B] mt-1.5">Unstable rollout — treat predictions cautiously.</div>
        )}
      </div>
    </div>
  );
};

/* ---------------------------- ProgressionCard ---------------------------- */
export const ProgressionCard: React.FC<{ forecast: Forecast | null }> = ({ forecast }) => {
  const steps: ForecastStep[] = (forecast?.steps ?? []).filter((s) => s.step > 0).slice(0, 6);
  const W = 160, H = 65;
  const maxR = Math.max(0.05, ...steps.map((s) => s.risk), 0.3);
  const pts = steps.length
    ? steps.map((s, i) => ({
        x: 15 + (i * (W - 25)) / Math.max(steps.length - 1, 1),
        y: 8 + (1 - s.risk / (maxR * 1.15)) * (H - 24),
        s,
      }))
    : [];
  const pathD = pts.length
    ? pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")
    : "";
  const areaD = pts.length > 1 ? `${pathD} L ${pts[pts.length - 1].x} ${H - 4} L ${pts[0].x} ${H - 4} Z` : "";

  return (
    <div className={CARD}>
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold text-[#667280]">Attack Progression (Next {steps.length || "—"} Steps)</div>
        <span className="text-[9px] text-[#98A2AF] font-mono">latency {forecast?.latency_ms ?? "—"}ms</span>
      </div>
      <div className="relative mt-2 px-1">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16 overflow-visible" aria-hidden>
          <defs>
            <linearGradient id="coralArea" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#DE5B49" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#DE5B49" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          {areaD && <path d={areaD} fill="url(#coralArea)" />}
          {pathD && <path d={pathD} fill="none" stroke="#DE5B49" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}
          {!steps.length && (
            <text x={W / 2} y={H / 2} textAnchor="middle" fontSize="7" fill="#8A94A0">waiting for forecast…</text>
          )}
          {pts.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r={i === pts.length - 1 ? 3.5 : 3} fill="#DE5B49" stroke="#FFF" strokeWidth="1.5" />
              <text x={p.x} y={p.y - 6} textAnchor="middle" fontSize="6" fill="#8A94A0" fontFamily="sans-serif">
                t+{p.s.step}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="grid text-center pt-2 border-t border-[#F1EBE2]" style={{ gridTemplateColumns: `repeat(${Math.max(steps.length, 1)}, minmax(0,1fr))` }}>
        {steps.map((s) => (
          <div key={s.step}>
            <div className="text-[10px] text-[#8F98A6] font-medium">t+{s.step}</div>
            <div className="text-[11px] font-bold text-[#353F4C]">{Math.round(s.risk * 100)}%</div>
          </div>
        ))}
        {!steps.length && <div className="text-[11px] text-[#8F98A6]">no rollout yet</div>}
      </div>
    </div>
  );
};
