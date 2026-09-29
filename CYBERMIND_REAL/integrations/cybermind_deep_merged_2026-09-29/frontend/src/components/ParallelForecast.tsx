import React, { useMemo, useState } from "react";
import {
  ArrowLeft, ArrowRight, Circle, Clock, ShieldAlert, ShieldCheck, Loader2,
  GitBranch, Sparkles, FlaskConical, ChevronRight, Info,
} from "lucide-react";
import type { LiveStore } from "../lib/live";
import type { Counterfactual, Intervention, ForecastStep } from "../lib/api";
import { STAGE_SHORT_NAMES, STAGE_COLORS, bandLabel } from "../lib/adapters";
import { ValidationPanel, DefencePanel, AttackLabPanel } from "./StrixValidation";

/* ------------------------------ branch model ------------------------------ */
interface FutureBranch {
  key: string;
  label: string;
  probability: number;
  riskTrajectory: number[];
  finalRisk: number;
  stageIds: number[];
  band: string;
  description: string;
  host?: string | null;
  port?: number | null;
  action: string;
  actionLabel: string;
  color: string;
  tier: "critical" | "high" | "medium" | "low";
}

const TIER_STYLE: Record<FutureBranch["tier"], { bg: string; border: string; chip: string; text: string; icon: React.ReactNode }> = {
  critical: { bg: "#FDF3F2", border: "#F2C9C3", chip: "bg-[#FBEAE7] text-[#B33A2B] border-[#F2C9C3]", text: "#B33A2B", icon: <ShieldAlert className="w-3.5 h-3.5" /> },
  high: { bg: "#FEF6F1", border: "#F4D6BC", chip: "bg-[#FDF1E3] text-[#B4611E] border-[#F4D6BC]", text: "#B4611E", icon: <ShieldAlert className="w-3.5 h-3.5" /> },
  medium: { bg: "#FDF8EE", border: "#EEDFC0", chip: "bg-[#FBF3DF] text-[#8C5424] border-[#EEDFC0]", text: "#8C5424", icon: <Clock className="w-3.5 h-3.5" /> },
  low: { bg: "#F2FAF4", border: "#C8E6CF", chip: "bg-[#E9F6EC] text-[#1E7A43] border-[#C8E6CF]", text: "#1E7A43", icon: <ShieldCheck className="w-3.5 h-3.5" /> },
};

const BAND_TIER: Record<string, FutureBranch["tier"]> = {
  CRITICAL: "critical", HIGH: "high", MEDIUM: "medium", LOW: "low",
};

/** Turn the counterfactual response into labeled parallel futures. */
function buildBranches(forecast: LiveStore["forecast"], cf: Counterfactual | null): FutureBranch[] {
  const branches: FutureBranch[] = [];
  const cur = forecast?.current;
  const k = forecast?.k ?? 0;

  // Future A — the unmitigated baseline rollout (what happens if we do nothing).
  if (cf?.baseline?.trajectory?.length) {
    const last = cf.baseline.trajectory[cf.baseline.trajectory.length - 1];
    branches.push({
      key: "baseline",
      label: `Future A (No Action)`,
      probability: 1.0,
      riskTrajectory: cf.baseline.trajectory,
      finalRisk: last,
      stageIds: cf.baseline.stage_ids ?? [],
      band: cf.baseline.band,
      description: "Unmitigated rollout from the current latent state — the do-nothing future.",
      action: "No Action", actionLabel: "No action (baseline)", color: "#DE5B49",
      tier: BAND_TIER[cf.baseline.band] ?? "high",
    });
  } else if (forecast?.steps?.length) {
    const risks = forecast.steps.map((s) => s.risk);
    branches.push({
      key: "baseline",
      label: "Future A (No Action)",
      probability: 1.0,
      riskTrajectory: risks,
      finalRisk: risks[risks.length - 1],
      stageIds: forecast.steps.map((s) => s.stage_id),
      band: bandLabel(risks[risks.length - 1]).label.toUpperCase(),
      description: "Unmitigated rollout from the current latent state.",
      action: "No Action", actionLabel: "No action (baseline)", color: "#DE5B49",
      tier: BAND_TIER[bandLabel(risks[risks.length - 1]).label.toUpperCase()] ?? "high",
    });
  }

  // Futures B..N — one simulated future per modeled intervention.
  if (cf) {
    const base = cf.baseline.risk || 1e-6;
    cf.interventions
      .filter((iv) => iv.action !== "No Action")
      .slice(0, 5)
      .forEach((iv, i) => {
        branches.push({
          key: `iv-${i}`,
          label: `Future ${String.fromCharCode(66 + i)} (${iv.action_label}${iv.host ? ` · ${iv.host}` : ""})`,
          probability: Math.max(0.01, base > 0 ? Math.min(1, iv.future_risk / base) : 0.1),
          riskTrajectory: iv.trajectory,
          finalRisk: iv.future_risk,
          stageIds: iv.stage_ids ?? [],
          band: iv.band,
          description: `Simulated future where the defender applies: ${iv.action_label}${iv.host ? ` on ${iv.host}` : ""}${iv.port ? ` (port ${iv.port})` : ""}.`,
          host: iv.host, port: iv.port, action: iv.action, actionLabel: iv.action_label,
          color: ["#E58B44", "#4B68B8", "#2EAA58", "#8A58D8", "#5AA9D6"][i % 5],
          tier: BAND_TIER[iv.band] ?? "medium",
        });
      });
  }
  void k; void cur;
  return branches;
}

/* ------------------------------- stage chain ------------------------------ */
const StageChain: React.FC<{ stageIds: number[]; risks: number[]; max: number; color: string }> = ({ stageIds, risks, max, color }) => {
  const steps = stageIds.slice(0, 4);
  return (
    <div className="flex items-center gap-1.5">
      {steps.map((sid, i) => (
        <React.Fragment key={i}>
          {i > 0 && <ArrowRight className="w-3 h-3 text-[#C9C0B4] shrink-0" />}
          <div className="flex flex-col items-center min-w-[74px]">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[9px] font-bold shadow-sm"
              style={{ backgroundColor: STAGE_COLORS[sid] ?? "#2B3B4C" }}
              title={STAGE_SHORT_NAMES[sid] ?? "Unknown"}>
              {sid === 0 ? "0" : sid === 3 ? "!" : sid}
            </div>
            <span className="text-[9px] font-semibold text-[#54606E] mt-1 leading-tight text-center">{STAGE_SHORT_NAMES[sid] ?? "?"}</span>
            {risks[i] !== undefined && (
              <span className="text-[8px] font-mono text-[#98A2AF]">{Math.round((risks[i] / max) * 100)}%</span>
            )}
            {i < steps.length - 1 && <span className="text-[7px] text-[#B8B0A4] mt-0.5">t+{i + 1}</span>}
          </div>
        </React.Fragment>
      ))}
      {!steps.length && <span className="text-[10px] text-[#98A2AF]">no stage rollout</span>}
    </div>
  );
};

/* ------------------------------ trajectory chart -------------------------- */
const TrajectoryChart: React.FC<{ branches: FutureBranch[]; selectedKey: string | null }> = ({ branches, selectedKey }) => {
  const W = 560, H = 200;
  const maxSteps = Math.max(...branches.map((b) => b.riskTrajectory.length), 1);
  const allRisks = branches.flatMap((b) => b.riskTrajectory);
  const yMax = Math.max(0.3, ...allRisks) * 1.15;
  const px = (i: number) => 44 + (i * (W - 60)) / Math.max(maxSteps - 1, 1);
  const py = (r: number) => H - 28 - (r / yMax) * (H - 52);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * yMax);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Risk trajectory of all futures">
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1="44" x2={W - 16} y1={py(t)} y2={py(t)} stroke="#EFEAE2" strokeWidth="1" />
          <text x="38" y={py(t) + 3} textAnchor="end" fontSize="8" fill="#98A2AF" className="font-mono">{Math.round(t * 100)}</text>
        </g>
      ))}
      {branches.map((b) => {
        const pts = b.riskTrajectory.map((r, i) => `${i === 0 ? "M" : "L"} ${px(i).toFixed(1)} ${py(r).toFixed(1)}`).join(" ");
        const dim = selectedKey !== null && selectedKey !== b.key;
        return (
          <g key={b.key} opacity={dim ? 0.25 : 1}>
            <path d={pts} fill="none" stroke={b.color} strokeWidth={selectedKey === b.key ? 2.8 : 1.8} strokeLinecap="round" />
            {b.riskTrajectory.map((r, i) => (
              <circle key={i} cx={px(i)} cy={py(r)} r={selectedKey === b.key ? 3.4 : 2.4} fill={b.color} stroke="#fff" strokeWidth="1" />
            ))}
          </g>
        );
      })}
      <text x="44" y={H - 8} fontSize="8" fill="#98A2AF" className="font-mono">now</text>
      {[1, 2, 3].map((i) => (
        <text key={i} x={px(i)} y={H - 8} fontSize="8" fill="#98A2AF" className="font-mono">t+{i}</text>
      ))}
    </svg>
  );
};

/* --------------------------------- main view ------------------------------ */
export const ParallelForecastView: React.FC<{ store: LiveStore; onBack: () => void }> = ({ store, onBack }) => {
  const [filter, setFilter] = useState<"all" | "critical" | "medium" | "low">("all");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const runSimulation = async () => {
    setRunning(true);
    try { await store.runGravity(); await store.runCounterfactual(); } finally { setRunning(false); }
  };

  const branches = useMemo(() => buildBranches(store.forecast, store.counterfactual), [store.forecast, store.counterfactual]);
  const filtered = branches.filter((b) => {
    if (filter === "all") return true;
    if (filter === "critical") return b.tier === "critical" || b.tier === "high";
    if (filter === "medium") return b.tier === "medium";
    return b.tier === "low";
  });
  const selected = branches.find((b) => b.key === selectedKey) ?? null;
  const cf = store.counterfactual;
  const rec = cf?.recommended;
  const reduction = rec ? cf!.baseline.risk - rec.future_risk : null;

  return (
    <div className="space-y-5">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-xs text-[#DE5B49] font-semibold mb-1 hover:underline">
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Command Center
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-editorial text-[28px] font-bold text-stone-900 tracking-tight">Parallel Threat Forecast</h1>
          <p className="text-xs text-[#7A8696] mt-1 max-w-2xl leading-relaxed">
            Explore multiple possible futures simulated by the trained world model from the current system state.
            Each branch is a genuine model rollout — the do-nothing baseline plus one future per candidate intervention.
          </p>
        </div>
        <button onClick={runSimulation} disabled={running || !store.health?.model?.available}
          className="px-4 py-2.5 bg-[#DE5B49] hover:bg-[#C94838] disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm flex items-center gap-2 shrink-0">
          {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />}
          {running ? "Simulating futures…" : "Simulate Parallel Futures"}
        </button>
      </div>

      {/* status strip */}
      <div className="flex items-center gap-3 flex-wrap text-xs">
        <span className="px-3 py-1.5 rounded-lg bg-white border border-[#EAE6DF] font-semibold text-[#3C4755]">
          Current: <span className="text-[#DE5B49]">{store.forecast?.current ? `${STAGE_SHORT_NAMES[store.forecast.current.stage_id]} · ${Math.round((store.forecast.current.risk ?? 0) * 100)}/100` : "no state"}</span>
        </span>
        <span className="px-3 py-1.5 rounded-lg bg-white border border-[#EAE6DF] font-semibold text-[#3C4755]">
          Horizon: <span className="text-[#3C4755]">{store.forecast?.k ?? "—"} steps</span>
        </span>
        <span className="px-3 py-1.5 rounded-lg bg-white border border-[#EAE6DF] font-semibold text-[#3C4755]">
          Branches: <span className="text-[#3C4755]">{branches.length}</span>
        </span>
        {!store.counterfactual && (
          <span className="text-[11px] text-[#8C5424] bg-[#FDF3E4] border border-[#F2D9AF] px-3 py-1.5 rounded-lg">
            Run the simulation to generate intervention futures
          </span>
        )}
      </div>

      {!branches.length ? (
        <div className="bg-white p-10 rounded-2xl border border-[#EAE6DF] text-center">
          <GitBranch className="w-10 h-10 text-[#D4CBBF] mx-auto mb-3" />
          <div className="text-sm font-bold text-[#3C4755]">No futures to show yet</div>
          <p className="text-xs text-[#7A8696] mt-1 max-w-md mx-auto leading-relaxed">
            The parallel engine needs a current graph state (telemetry or a scenario) and the model.
            {store.health?.model?.available ? " Click “Simulate Parallel Futures” above." : " Check the configured model path in Settings."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          {/* Branch cards */}
          <div className="xl:col-span-8 space-y-5">
            <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center flex-wrap gap-2">
                  {(["all", "critical", "medium", "low"] as const).map((f) => (
                    <button key={f} onClick={() => setFilter(f)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                        filter === f ? "bg-[#DE5B49] text-white" : "bg-[#F4F1EB] text-[#586474] hover:bg-[#EAE2D8]"}`}>
                      {f === "all" ? "All Futures" : f === "critical" ? "High Risk" : f === "medium" ? "Medium Risk" : "Low Risk"}
                    </button>
                  ))}
                </div>
                <span className="text-[10px] text-[#98A2AF] font-mono hidden lg:block shrink-0">{filtered.length} shown · model rollouts</span>
              </div>

              <div className="relative pl-4">
                {/* connector trunk */}
                <div className="absolute left-0 top-0 bottom-0 w-px bg-[#E6E0D5]" />
                <div className="space-y-3">
                  {filtered.map((b) => {
                    const st = TIER_STYLE[b.tier];
                    const isSelected = selectedKey === b.key;
                    const maxR = Math.max(...b.riskTrajectory, 0.01);
                    return (
                      <button key={b.key} onClick={() => setSelectedKey(isSelected ? null : b.key)}
                        className={`w-full text-left rounded-xl border p-3.5 transition-all ${isSelected ? "ring-2 ring-[#DE5B49]/30 border-[#DE5B49]/40" : "hover:border-[#D9CFBF]"} ${b.tier === "low" ? "bg-[#F7FBF8]" : b.tier === "critical" ? "bg-[#FEF7F6]" : "bg-white"}`}
                        style={{ borderColor: st.border }}>
                        <div className="flex items-center gap-4">
                          {/* branch id */}
                          <div className="w-28 shrink-0">
                            <div className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: b.color }} />
                              <span className="text-xs font-bold text-[#1C232B] truncate" title={b.label}>{b.label.match(/^Future [A-Z]/)?.[0] ?? b.label}</span>
                            </div>
                            <div className="text-[10px] text-[#7A8696] mt-0.5">{Math.round(b.probability * 100)}% relative risk</div>
                          </div>
                          {/* stage chain */}
                          <div className="flex-1 overflow-x-auto">
                            <StageChain stageIds={b.stageIds} risks={b.riskTrajectory} max={maxR} color={b.color} />
                          </div>
                          {/* verdict */}
                          <div className="w-32 shrink-0 text-right">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase tracking-wide ${st.chip}`}>
                              {st.icon}{b.band}
                            </span>
                            <div className="text-[11px] text-[#7A8696] mt-1">Final risk</div>
                            <div className="text-sm font-black" style={{ color: st.text }}>
                              {Math.round(b.finalRisk * 100)}<span className="text-[10px] font-bold text-[#98A2AF]">/100</span>
                            </div>
                          </div>
                          <ChevronRight className={`w-4 h-4 text-[#B8B0A4] transition-transform ${isSelected ? "rotate-90" : ""}`} />
                        </div>
                        {isSelected && (
                          <div className="mt-3 pt-3 border-t border-[#F0ECE4] text-[11px] text-[#556171] leading-relaxed">
                            {b.description}
                            {b.host && <span className="font-mono"> · target {b.host}</span>}
                            {cf && <span className="text-[#8C96A3]"> · risk reduction vs baseline: {b.key === "baseline" ? "—" : `${((cf.baseline.risk - b.finalRisk) * 100).toFixed(1)}%`}</span>}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* summary table */}
            <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5">
              <h3 className="font-bold text-sm text-[#1C232B] mb-3">Parallel Futures Summary</h3>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#F0ECE4] text-[11px] font-semibold text-[#8C96A3]">
                    <th className="py-2 px-2">Path</th><th className="py-2 px-2">Rel. risk</th><th className="py-2 px-2">Final stage</th>
                    <th className="py-2 px-2">Final risk</th><th className="py-2 px-2">Band</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F4F1EA]">
                  {branches.map((b) => {
                    const lastStage = b.stageIds[b.stageIds.length - 1];
                    return (
                      <tr key={b.key} onClick={() => setSelectedKey(b.key)} className="hover:bg-[#FAF8F5] cursor-pointer">
                        <td className="py-2 px-2 font-semibold text-[#2B3542]">
                          <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: b.color }} />{b.label}
                        </td>
                        <td className="py-2 px-2 font-mono">{Math.round(b.probability * 100)}%</td>
                        <td className="py-2 px-2">{lastStage != null ? STAGE_SHORT_NAMES[lastStage] : "—"}</td>
                        <td className="py-2 px-2 font-mono font-bold">{Math.round(b.finalRisk * 100)}/100</td>
                        <td className="py-2 px-2"><span className={`px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase ${TIER_STYLE[b.tier].chip}`}>{b.band}</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right sidebar */}
          <div className="xl:col-span-4 space-y-5">
            {/* trajectory chart */}
            <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5">
              <h3 className="font-bold text-sm text-[#1C232B] mb-2">Risk Trajectory (All Futures)</h3>
              <TrajectoryChart branches={branches} selectedKey={selectedKey} />
              <div className="flex flex-wrap gap-2 mt-1">
                {branches.map((b) => (
                  <button key={b.key} onClick={() => setSelectedKey(selectedKey === b.key ? null : b.key)}
                    className={`flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-md border transition-all ${selectedKey === b.key ? "border-[#DE5B49]/40 bg-[#FDF7F6]" : "border-transparent hover:bg-[#FAF8F5]"}`}>
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: b.color }} />
                    <span className="text-[#54606E]">{b.label.match(/Future [A-Z]/)?.[0]}</span>
                    <span className="text-[#98A2AF] font-mono">{Math.round(b.probability * 100)}%</span>
                  </button>
                ))}
              </div>
            </div>

            {/* detail panel */}
            <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-[#DE5B49]" />
                <h3 className="font-bold text-sm text-[#1C232B]">Forecast Details</h3>
              </div>
              {selected ? (
                <div className="space-y-2.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#1C232B]">{selected.label}</span>
                    <span className={`px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase ${TIER_STYLE[selected.tier].chip}`}>{selected.band}</span>
                  </div>
                  <div className="flex justify-between border-b border-[#F5F2EB] pb-1.5"><span className="text-[#7A8696]">Final risk</span><span className="font-mono font-bold">{Math.round(selected.finalRisk * 100)}/100</span></div>
                  <div className="flex justify-between border-b border-[#F5F2EB] pb-1.5"><span className="text-[#7A8696]">Steps</span><span className="font-mono">{selected.riskTrajectory.length}</span></div>
                  <div className="flex justify-between border-b border-[#F5F2EB] pb-1.5"><span className="text-[#7A8696]">Final stage</span><span className="font-semibold">{STAGE_SHORT_NAMES[selected.stageIds[selected.stageIds.length - 1] ?? 0]}</span></div>
                  <p className="text-[11px] text-[#556171] leading-relaxed pt-1">{selected.description}</p>
                  <div className="text-[10px] text-[#8C96A3] leading-relaxed bg-[#FAF9F6] border border-[#EDE7DE] rounded-lg p-2.5">
                    <Info className="w-3 h-3 inline mr-1" />
                    Every branch is produced by the same trained model on the same starting window — differences come only from the simulated intervention.
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-[#7A8696] leading-relaxed">Select a future branch to inspect its rollout, stages and risk trajectory.</p>
              )}
            </div>

            {/* scenario analysis */}
            <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <FlaskConical className="w-4 h-4 text-[#DE5B49]" />
                <h3 className="font-bold text-sm text-[#1C232B]">Scenario Analysis</h3>
              </div>
              {rec && cf ? (
                <>
                  <p className="text-[11px] text-[#7A8696] mb-3">What if we {rec.action_label.toLowerCase()}{rec.host ? ` (${rec.host})` : ""}? Compare the do-nothing future with the intervened future.</p>
                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="p-3 rounded-xl bg-[#FEF7F6] border border-[#F2C9C3]">
                      <div className="text-[9px] uppercase font-bold text-[#B33A2B] flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> No action</div>
                      <div className="text-lg font-black text-[#1C232B] mt-1">{Math.round(cf.baseline.risk * 100)}<span className="text-[10px]">/100</span></div>
                      <div className="text-[10px] font-bold text-[#B33A2B]">{cf.baseline.band}</div>
                    </div>
                    <div className="p-3 rounded-xl bg-[#F2FAF4] border border-[#C8E6CF]">
                      <div className="text-[9px] uppercase font-bold text-[#1E7A43] flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> With {rec.action_label.toLowerCase()}</div>
                      <div className="text-lg font-black text-[#1C232B] mt-1">{Math.round(rec.future_risk * 100)}<span className="text-[10px]">/100</span></div>
                      <div className="text-[10px] font-bold text-[#1E7A43]">{rec.band}</div>
                    </div>
                  </div>
                  {reduction != null && reduction > 0 && (
                    <div className="mt-3 flex items-center justify-between bg-[#E9F6EC] border border-[#C8E6CF] rounded-xl px-3.5 py-2.5">
                      <span className="text-[11px] font-semibold text-[#1E7A43]">Predicted risk reduction</span>
                      <span className="text-lg font-black text-[#1E7A43] flex items-center gap-1">−{Math.round(reduction * 100)}<Circle className="w-2 h-2 fill-current" /> pts</span>
                    </div>
                  )}
                  <div className="text-[10px] text-[#8C96A3] mt-2 leading-relaxed">{cf.disclaimer}</div>
                </>
              ) : (
                <p className="text-[11px] text-[#7A8696] leading-relaxed">
                  Run “Simulate Parallel Futures” to compare the do-nothing future against isolation, port-block and rate-limit futures.
                </p>
              )}
            </div>

            {/* Strix validation + defence recommendation */}
            <AttackLabPanel store={store} />
            <ValidationPanel store={store} />
            <DefencePanel store={store} />
          </div>
        </div>
      )}
    </div>
  );
};
