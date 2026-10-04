import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, ArrowLeft, ArrowRight, Download, FileText, Play, Pause, Loader2,
  ShieldCheck, TriangleAlert, ListRestart, AlertTriangle, Clock,
  LockKeyhole, UnlockKeyhole, Eye, EyeOff, X, Upload, CheckCircle2
} from "lucide-react";
import type { SidebarTab } from "./Sidebar";
import type { LiveStore } from "../lib/live";
import { api, type ExperimentRun, type RunDetail, type Forecast } from "../lib/api";
import { STAGE_SHORT_NAMES, STAGE_COLORS } from "../lib/adapters";
import { encryptIncidentBriefWithKey, decryptIncidentBrief } from "../lib/reportCrypto";
import { SystemHealthCard } from "./InsightsAndHealth";

const Back: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button onClick={onClick} className="inline-flex items-center gap-1.5 text-xs text-[#DE5B49] font-semibold mb-2 hover:underline">
    <ArrowLeft className="w-3.5 h-3.5" /> Back to Command Center
  </button>
);

/* ------------------------------ Live Monitor ------------------------------ */
export const LiveMonitorView: React.FC<{ store: LiveStore; onBack: () => void }> = ({ store, onBack }) => (
  <div className="space-y-6">
    <Back onClick={onBack} />
    <div className="flex items-center justify-between">
      <div>
        <h1 className="font-editorial text-2xl font-bold text-stone-900">Live Telemetry &amp; Threat Ingestion</h1>
        <p className="text-xs text-[#7A8696] mt-0.5">Normalized flow events feeding the temporal state engine.</p>
      </div>
      <span className={`flex items-center gap-1.5 border px-3 py-1 rounded-lg text-xs font-semibold ${
        store.ws === "online" ? "bg-[#E8F7ED] border-[#C6EBD1] text-[#248B47]" : "bg-[#FDF3E4] border-[#F2D9AF] text-[#8C5424]"}`}>
        <span className={`w-2 h-2 rounded-full ${store.ws === "online" ? "bg-[#2EAA58] animate-pulse" : "bg-[#E58B44]"}`} />
        Stream {store.ws === "online" ? "Active" : "Offline"} · {store.health?.telemetry_events ?? 0} events
      </span>
    </div>
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-white p-4 rounded-xl border border-[#EAE6DF] shadow-xs">
        <span className="text-[10px] font-bold uppercase text-stone-500">Ingested Events</span>
        <div className="text-2xl font-black text-stone-900 mt-1">{store.health?.telemetry_events ?? 0}</div>
        <span className="text-[11px] text-stone-500 font-semibold">{store.provenance} stream</span>
      </div>
      <div className="bg-white p-4 rounded-xl border border-[#EAE6DF] shadow-xs">
        <span className="text-[10px] font-bold uppercase text-stone-500">Observation Windows</span>
        <div className="text-2xl font-black text-stone-900 mt-1">{store.health?.state_windows ?? 0}</div>
        <span className="text-[11px] text-stone-500 font-semibold">60s windows / 30s stride</span>
      </div>
      <div className="bg-white p-4 rounded-xl border border-[#EAE6DF] shadow-xs">
        <span className="text-[10px] font-bold uppercase text-stone-500">Forecast Latency</span>
        <div className="text-2xl font-black text-stone-900 mt-1">{store.forecast?.latency_ms ?? "—"}<span className="text-sm font-bold text-stone-500"> ms</span></div>
        <span className="text-[11px] text-stone-500 font-semibold">K-step rollout on {store.health?.model?.device ?? "—"}</span>
      </div>
    </div>
    <div className="bg-[#181F26] text-stone-200 p-4 rounded-2xl border border-stone-800 font-mono text-xs shadow-lg space-y-1.5">
      <div className="flex items-center justify-between pb-2 border-b border-stone-800 text-stone-400">
        <span>Unified event stream (telemetry → state engine)</span>
        <span>offline-first · local only</span>
      </div>
      <div className="space-y-1.5 text-[11px] max-h-72 overflow-y-auto">
        {store.events.length ? [...store.events].reverse().slice(0, 40).map((e) => (
          <p key={e.id}>
            <span className={e.severity === "High" ? "text-[#DE5B49] font-bold" : e.severity === "Medium" ? "text-amber-400" : "text-emerald-400"}>
              [{e.time}]
            </span>{" "}
            <span className="text-stone-300">{e.source}</span>
            <span className="text-stone-500"> → </span>
            <span className="text-stone-300">{e.destination ?? "?"}</span>
            <span className="text-stone-500"> · {e.label}{e.protocol ? ` · ${e.protocol}` : ""}</span>
          </p>
        )) : <p className="text-stone-500">No events yet — start a scenario.</p>}
      </div>
    </div>
  </div>
);

/* ----------------------------- Threat Forecast ---------------------------- */
export const ThreatForecastView: React.FC<{ store: LiveStore; onBack: () => void }> = ({ store, onBack }) => {
  const f = store.forecast;
  return (
    <div className="space-y-6">
      <Back onClick={onBack} />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-editorial text-2xl font-bold text-stone-900">Predictive Threat Forecast</h1>
          <p className="text-xs text-[#7A8696] mt-0.5">K-step world-model rollout from the latest observation window.</p>
        </div>
        <span className="bg-[#FAF6F2] border border-[#DE5B49]/30 text-[#DE5B49] px-3 py-1 rounded-lg text-xs font-bold">
          Horizon: +{f?.k ?? "—"} steps
        </span>
      </div>

      {!f?.steps?.length ? (
        <div className="bg-white p-8 rounded-2xl border border-[#EAE6DF] text-center text-sm text-stone-500">
          {f?.model_available === false
            ? "Model not loaded — check models/best.pt to enable forecasting."
            : "Upload a PCAP or CSV with enough observation windows, then return here."}
        </div>
      ) : (
        <>
          <div className="bg-white p-5 rounded-2xl border border-[#EAE6DF]">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-sm text-stone-900">Risk trajectory (each step = one simulated transition)</h3>
              <span className="text-[10px] text-[#8C96A3] bg-[#FAF8F5] border border-[#EAE6DF] px-2 py-0.5 rounded-full">
                Shaded band = 95% CI (Monte Carlo)
              </span>
            </div>
            {/* SVG chart with uncertainty bands */}
            <div className="relative w-full" style={{ height: 128 }}>
              <svg width="100%" height="128" preserveAspectRatio="none" className="overflow-visible">
                {/* Uncertainty band (shaded area between lower_pct and upper_pct) */}
                {f.steps.some((s) => s.lower_pct != null) && (() => {
                  const n = f.steps.length;
                  const W = 100 / n;
                  const points = f.steps.map((s, i) => ({
                    x: (i + 0.5) * W,
                    lo: 100 - Math.min(100, Math.max(0, (s.lower_pct ?? s.risk * 100))),
                    hi: 100 - Math.min(100, Math.max(0, (s.upper_pct ?? s.risk * 100))),
                  }));
                  const topPath = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.hi.toFixed(2)}`).join(" ");
                  const botPath = [...points].reverse().map((p, i) => `${i === 0 ? "L" : "L"}${p.x.toFixed(2)},${p.lo.toFixed(2)}`).join(" ");
                  return (
                    <path
                      d={`${topPath} ${botPath} Z`}
                      fill="#DE5B49"
                      fillOpacity={0.12}
                      stroke="none"
                      vectorEffect="non-scaling-stroke"
                    />
                  );
                })()}
                {/* Mean risk bars */}
                {f.steps.map((s, i) => {
                  const n = f.steps.length;
                  const W = 100 / n;
                  const barH = Math.max(2, s.risk * 100);
                  return (
                    <g key={s.step}>
                      <rect
                        x={`${i * W + W * 0.15}%`}
                        y={`${100 - barH}%`}
                        width={`${W * 0.7}%`}
                        height={`${barH}%`}
                        rx="2"
                        fill="#DE5B49"
                        fillOpacity={0.85}
                        className="hover:fill-[#DE5B49] transition-all"
                      >
                        <title>t+{s.step}: {Math.round(s.risk * 100)}% risk · {s.stage}{s.lower_pct != null ? ` · 95% CI [${Math.round(s.lower_pct)}%–${Math.round(s.upper_pct ?? s.risk * 100)}%]` : ""}</title>
                      </rect>
                      <text
                        x={`${(i + 0.5) * W}%`}
                        y="100%"
                        textAnchor="middle"
                        fontSize="7"
                        fill="#98A2AF"
                        dy="10"
                        style={{ fontFamily: "monospace" }}
                      >t+{s.step}</text>
                    </g>
                  );
                })}
              </svg>
            </div>
            <div className="mt-4 text-[10px] text-[#8C96A3]">Confidence {f.confidence != null ? `${Math.round(f.confidence * 100)}%` : "—"} · OOD {f.ood_flag ? "HIGH — unstable rollout" : "LOW"} · {f.disclaimer}</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {f.steps.slice(0, 6).map((s) => (
              <div key={s.step} className="bg-white p-5 rounded-2xl border border-[#EAE6DF] space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-sm text-stone-900">t+{s.step} · {s.stage_short}</h3>
                  <span className="font-mono text-xs font-bold" style={{ color: STAGE_COLORS[s.stage_id] }}>{Math.round(s.risk * 100)}% risk</span>
                </div>
                <div className="text-xs text-stone-600 leading-relaxed">
                  {s.technique || "Transition"} · step confidence {Math.round((s.confidence ?? 0) * 100)}%
                  {s.stage_probs?.length ? ` · stage distribution [${s.stage_probs.map((p) => p.toFixed(2)).join(", ")}]` : ""}
                </div>
                <div className="p-3 bg-[#FAF6F2] border border-[#EBE3D7] rounded-xl text-[11px] text-[#556171]">
                  Predicted by rolling the learned dynamics forward from the current latent state.
                  {s.technique_id && s.technique_id !== "—" ? ` ATT&CK-aligned context: ${s.technique_id}.` : ""}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

/* ------------------------------- Attack Graph ----------------------------- */
export const AttackGraphView: React.FC<{
  store: LiveStore;
  onBack: () => void;
  onSelectHost?: (hostId: string) => void;
  onTakeToParallelFutures?: (hostId: string) => void;
  onAttackWithStrix?: (hostId: string) => void;
  onSuggestPatch?: (hostId: string) => void;
}> = ({ store, onBack, onSelectHost, onTakeToParallelFutures, onAttackWithStrix, onSuggestPatch }) => {
  const g = store.gravity;
  return (
    <div className="space-y-6">
      <Back onClick={onBack} />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-editorial text-2xl font-bold text-stone-900">Attack Gravity &amp; Critical Paths</h1>
          <p className="text-xs text-[#7A8696] mt-0.5">Which asset most reduces future compromise risk if isolated.</p>
        </div>
        <button onClick={store.runGravity} disabled={store.busy.gravity}
          className="px-4 py-2 bg-[#DE5B49] hover:bg-[#C94735] disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-sm flex items-center gap-2 cursor-pointer">
          {store.busy.gravity ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null} Compute Gravity
        </button>
      </div>

      {!g ? (
        <div className="bg-white p-8 rounded-2xl border border-[#EAE6DF] text-center text-sm text-stone-500">
          Run Attack Gravity to rank hosts by counterfactual risk reduction.
        </div>
      ) : (
        <div className="bg-white p-6 rounded-2xl border border-[#EAE6DF]">
          <div className="space-y-3">
            {g.gravity.map((row, i) => {
              const maxG = Math.max(...g.gravity.map((x) => Math.abs(x.attack_gravity)), 1e-6);
              return (
                <div key={row.host} className="flex flex-wrap items-center justify-between gap-3 p-2.5 rounded-xl hover:bg-[#FAF8F5] border border-transparent hover:border-[#EAE6DF] transition-colors">
                  <div className="flex items-center gap-3 flex-1 min-w-[280px]">
                    <span className="font-mono text-xs font-bold text-[#1F2731] w-36 truncate">{row.host}</span>
                    <div className="flex-1 h-3.5 bg-[#EFECE5] rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${Math.max(3, (Math.abs(row.attack_gravity) / maxG) * 100)}%`, backgroundColor: i === 0 ? "#DE5B49" : "#E58B44" }} />
                    </div>
                    <span className="font-mono text-xs font-bold text-[#424D5B] w-14 text-right">{row.attack_gravity.toFixed(3)}</span>
                    <span className="font-mono text-[10px] text-[#8C96A3] w-28 text-right">{row.baseline_risk.toFixed(2)}→{row.counterfactual_risk.toFixed(2)}</span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => onTakeToParallelFutures?.(row.host)}
                      className="px-2 py-1 bg-[#FAF6F2] hover:bg-[#F4ECE2] text-[#4F5968] border border-[#DDD6CC] rounded-lg text-[10px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                      title="Simulate isolating in Parallel Futures"
                    >
                      <span>Future</span>
                    </button>
                    <button
                      onClick={() => onAttackWithStrix?.(row.host)}
                      className="px-2 py-1 bg-[#FAF0ED] hover:bg-[#F7DDD7] text-[#DE5B49] border border-[#F4D0C9] rounded-lg text-[10px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
                      title="Probe host in Strix sandbox"
                    >
                      <span>Strix</span>
                    </button>
                    <button
                      onClick={() => onSuggestPatch?.(row.host)}
                      className="px-2 py-1 bg-[#1E7A43] hover:bg-[#176636] text-white rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-xs transition-colors cursor-pointer"
                      title="Suggest AI patch and defend"
                    >
                      <span>Defend</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 p-3 bg-[#FAF6F2] border border-[#EBE3D7] rounded-xl text-[11px] text-[#556171]">
            AttackGravity(i) = P(future compromise | current state) − P(future compromise | isolate i),
            computed by the trained world model. Model-based simulation, not a causal effect.
          </div>
        </div>
      )}
    </div>
  );
};

/* ------------------------------ Replay Analysis --------------------------- */
export const ReplayView: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const [files, setFiles] = useState<string[]>([]);
  const [loaded, setLoaded] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [pos, setPos] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [fc, setFc] = useState<Forecast | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { api.replayFiles().then((r) => { setFiles(r.files); setLoaded(r.loaded); }).catch(() => undefined); }, []);

  const seek = useCallback(async (idx: number) => {
    try {
      const r = await api.seekReplay(idx);
      setPos(r.index); setFc(r.forecast); setErr(null);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }, []);

  useEffect(() => {
    if (playing && loaded) {
      timer.current = setInterval(() => {
        setPos((p) => {
          const next = Math.min(p + 1, total);
          if (next >= total) setPlaying(false);
          void seek(next);
          return next;
        });
      }, 700);
    }
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing, loaded, total, seek]);

  return (
    <div className="space-y-6 max-w-5xl animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div className="flex items-center gap-3">
          <Back onClick={onBack} />
          <div>
            <h1 className="font-editorial text-3xl font-normal tracking-tight text-[#171F27]">Replay & Outcome Verification</h1>
            <p className="text-xs text-[#707C8C] mt-1 font-medium">Scrub recorded telemetry; the model re-predicts at every position.</p>
          </div>
        </div>
        <span className="bg-[#EBF7EE] border border-[#C3E8CA] text-[#1E7B3E] px-3.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest shadow-sm">REPLAY</span>
      </div>

      <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-[0_2px_8px_rgba(0,0,0,0.02)] overflow-hidden">
        <div className="p-5 border-b border-[#F0EBE1] bg-[#FCFBF9]">
          <h3 className="font-bold text-sm text-[#171F27]">Recordings Library</h3>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex flex-wrap gap-2.5">
            {files.length ? files.map((f) => (
              <button key={f} onClick={async () => {
                try { const r = await api.loadReplay(f); setLoaded(f); setTotal(r.events); setPos(0); setFc(null); }
                catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
              }}
                className={`px-4 py-2 rounded-xl text-[11px] font-bold font-mono transition-all flex items-center gap-2 border ${
                  loaded === f ? "bg-[#171F27] text-white border-[#171F27] shadow-sm" : "bg-white border-[#EAE6DF] text-[#424F60] hover:bg-[#F9F8F6] hover:border-[#D1C9BE]"
                }`}>
                <FileText className={`w-3.5 h-3.5 ${loaded === f ? "text-white" : "text-[#707C8C]"}`} />
                {f}
              </button>
            )) : <div className="text-xs text-[#8A95A4] flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-[#EAE6DF]"/>No files in data/replay/. Run a scenario, then export or copy its JSONL there.</div>}
          </div>

          {loaded && (
            <div className="pt-4 border-t border-[#F0EBE1] space-y-5">
              <div className="flex flex-col sm:flex-row items-center gap-4 bg-[#F9F8F6] p-4 rounded-xl border border-[#E4DFD6]">
                <button onClick={() => setPlaying(!playing)} disabled={pos >= total}
                  className={`p-3 rounded-xl transition-all shadow-sm disabled:opacity-40 flex items-center justify-center shrink-0 ${
                    playing 
                      ? "bg-[#FDF2F0] text-[#DE5B49] border border-[#F4D0C9] hover:bg-[#F9DCD7]" 
                      : "bg-[#171F27] text-white hover:bg-[#2C3642] border border-[#171F27]"
                  }`} aria-label={playing ? "Pause" : "Play"}>
                  {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                </button>
                <div className="flex-1 w-full flex flex-col justify-center px-2">
                  <input type="range" min={0} max={total} value={pos} onChange={(e) => { setPlaying(false); void seek(parseInt(e.target.value, 10)); }}
                    className="w-full accent-[#DE5B49] h-1.5 bg-[#EAE6DF] rounded-lg appearance-none cursor-pointer outline-none hover:h-2 transition-all focus:ring-2 focus:ring-[#DE5B49]/20" aria-label="Replay position" />
                </div>
                <div className="font-mono text-[11px] font-semibold text-[#171F27] bg-white px-3 py-1.5 rounded-lg border border-[#E4DFD6] shrink-0 shadow-sm">
                  {pos} <span className="text-[#A0AAB8] mx-0.5">/</span> {total}
                </div>
              </div>

              {err && <div className="text-[11px] text-[#B33A2B] bg-[#FDF2F0] border border-[#F9DCD7] rounded-lg p-3 font-medium flex items-center gap-2"><AlertTriangle className="w-3.5 h-3.5"/>{err}</div>}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-white border border-[#EAE6DF] shadow-sm rounded-xl flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-widest text-[#8A95A4]">Risk at scrub position</span>
                  <div className="font-editorial text-3xl tracking-tight text-[#171F27] mt-2">{fc?.horizon?.risk != null ? `${Math.round(fc.horizon.risk * 100)}%` : fc?.reason === "model_checkpoint_missing" ? "Missing" : "—"}</div>
                </div>
                <div className="p-4 bg-white border border-[#EAE6DF] shadow-sm rounded-xl flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-widest text-[#8A95A4]">Predicted stage</span>
                  <div className="font-mono text-xl font-bold text-[#DE5B49] mt-2">
                    {fc?.horizon?.stage_id != null ? STAGE_SHORT_NAMES[fc.horizon.stage_id] : "—"}
                  </div>
                </div>
                <div className="p-4 bg-white border border-[#EAE6DF] shadow-sm rounded-xl flex flex-col">
                  <span className="text-[10px] uppercase font-bold tracking-widest text-[#8A95A4]">Next-stage path</span>
                  <div className="font-mono text-[11px] text-[#424D5B] mt-2 font-medium bg-[#F9F8F6] p-2 rounded-lg border border-[#E4DFD6] flex-1 overflow-hidden text-ellipsis">
                    {fc?.steps?.slice(0, 5).map((s) => s.stage_short).join(" → ") || "—"}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* --------------------------- Scenario Lab (full) -------------------------- */
export const ScenarioLabView: React.FC<{ store: LiveStore; onBack: () => void }> = ({ store, onBack }) => (
  <div className="space-y-6 max-w-5xl animate-in fade-in duration-300">
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
      <div className="flex items-center gap-3">
        <Back onClick={onBack} />
        <div>
          <h1 className="font-editorial text-3xl font-normal tracking-tight text-[#171F27]">Scenario Emulation Lab</h1>
          <p className="text-xs text-[#707C8C] mt-1 font-medium">Live attack progression telemetry through the observe → predict → prevent pipeline.</p>
        </div>
      </div>
      <span className="bg-[#EBF7EE] border border-[#C3E8CA] text-[#1E7B3E] px-3.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest shadow-sm">REAL TELEMETRY · CONTROLLED LAB</span>
    </div>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {store.scenarioList.map((s) => (
        <div key={s.id} className="bg-white p-5 rounded-2xl border border-[#EAE6DF] shadow-[0_2px_8px_rgba(0,0,0,0.02)] transition-all hover:shadow-[0_4px_12px_rgba(0,0,0,0.04)] flex flex-col">
          <div className="flex items-start justify-between gap-4 mb-3">
            <h3 className="font-bold text-[#171F27] text-sm">{s.name}</h3>
            <button onClick={() => store.startScenario(s.id)} disabled={store.health?.scenario?.running}
              className="px-4 py-1.5 bg-[#171F27] hover:bg-[#2C3642] disabled:opacity-40 text-white text-[11px] font-bold rounded-lg shadow-sm transition-all shrink-0 flex items-center gap-1.5">
              <Play className="w-3 h-3" /> Start
            </button>
          </div>
          <p className="text-xs text-[#5D6978] leading-relaxed mb-4 flex-1">{s.description}</p>
          <div className="text-[10px] text-[#A0AAB8] font-mono font-medium flex items-center gap-1.5 bg-[#F9F8F6] p-2 rounded-lg border border-[#F0EBE1] w-fit">
            <Clock className="w-3 h-3" /> {s.duration_ticks} ticks <span className="text-[#D1C9BE]">•</span> deterministic seed <span className="text-[#D1C9BE]">•</span> RFC-5737 hosts
          </div>
        </div>
      ))}
      <div className="bg-[#FAF8F5] p-5 rounded-2xl border border-[#EAE6DF] text-xs text-[#5D6978] leading-relaxed flex flex-col justify-center">
        <div className="flex items-center gap-2 font-bold text-[#171F27] mb-2 text-sm">
          <ListRestart className="w-4 h-4 text-[#DE5B49]" /> Data Honesty Guarantee
        </div>
        Scenario telemetry is generated locally with fixed seeds and test-range IP addresses. It is never presented or masked as real-world traffic. The model reacts through the exact same PyTorch inference pipeline as live production telemetry.
      </div>
    </div>
  </div>
);

/* --------------------------------- Reports -------------------------------- */
export const ReportsView: React.FC<{ store: LiveStore; onBack: () => void }> = ({ store, onBack }) => {
  const [runs, setRuns] = useState<ExperimentRun[]>([]);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [reportAction, setReportAction] = useState<"encrypt" | "decrypt" | null>(null);
  const [reportKey, setReportKey] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [keyCopied, setKeyCopied] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [encryptedFile, setEncryptedFile] = useState<File | null>(null);
  const [reportError, setReportError] = useState("");
  const [decryptedReport, setDecryptedReport] = useState<Record<string, unknown> | null>(null);
  useEffect(() => { api.experiments().then((r) => setRuns(r.runs)).catch(() => undefined); }, []);

  const copyReportKey = async (key: string): Promise<boolean> => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const field = document.createElement("textarea");
    field.value = key;
    field.readOnly = true;
    field.style.position = "fixed";
    field.style.left = "-9999px";
    document.body.appendChild(field);
    field.focus();
    field.select();
    try {
      if (document.execCommand("copy")) return true;
    } catch { /* Use the Clipboard API below. */ }
    finally { field.remove(); previousFocus?.focus(); }

    if (!navigator.clipboard?.writeText) return false;
    let timeout = 0;
    try {
      return await Promise.race([
        navigator.clipboard.writeText(key).then(() => true).catch(() => false),
        new Promise<boolean>((resolve) => { timeout = window.setTimeout(() => resolve(false), 1500); }),
      ]);
    } catch { return false; }
    finally { window.clearTimeout(timeout); }
  };

  const downloadJson = async (contents: object, filename: string) => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(contents, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    const isDesktop = Boolean((window as Window & { __CYBERMIND_DESKTOP__?: boolean }).__CYBERMIND_DESKTOP__);
    const saved = isDesktop ? new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        window.removeEventListener("cybermind:download", onDownload);
        reject(new Error("The desktop app did not confirm that the report was saved."));
      }, 600_000);
      function onDownload(event: Event) {
        const detail = (event as CustomEvent<{ filename: string; status: string; error?: string }>).detail;
        if (detail?.filename !== filename) return;
        window.clearTimeout(timeout);
        window.removeEventListener("cybermind:download", onDownload);
        if (detail.status === "completed") resolve();
        else reject(new Error(detail.error || "The report was not saved."));
      }
      window.addEventListener("cybermind:download", onDownload);
    }) : Promise.resolve();
    document.body.appendChild(a);
    try {
      a.click();
      await saved;
    } finally {
      a.remove();
      if (isDesktop) URL.revokeObjectURL(url);
      else window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    }
  };

  const closeReportAction = () => {
    setReportAction(null); setReportKey(""); setKeyInput(""); setKeyCopied(false);
    setShowKey(false); setEncryptedFile(null); setReportError("");
  };

  const exportJson = async () => {
    setReportError("");
    setBusy(true);
    try {
      const [h, f, cf] = await Promise.all([api.health(), api.forecast().catch(() => null), store.counterfactual]);
      const report = {
        report_type: "CYBERMIND_Incident_Brief",
        generated_at: new Date().toISOString(),
        executive_summary:
          `CYBERMIND evaluated ${h.telemetry_events} telemetry events across ${h.state_windows} observation windows. ` +
          (f?.steps?.length
            ? `Current infiltration risk ${(f.current?.risk ?? 0) * 100 > 0 ? `${Math.round((f.current?.risk ?? 0) * 100)}` : "0"}/100 (${f.current?.stage ?? "unknown"}); predicted t+${f.k} risk ${Math.round((f.horizon?.risk ?? 0) * 100)}%.`
            : "No forecast available (insufficient windows or model missing).") +
          (store.counterfactual?.recommended
            ? ` Recommended intervention: ${store.counterfactual.recommended.action_label}${store.counterfactual.recommended.host ? ` (${store.counterfactual.recommended.host})` : ""}, predicted reduction ${Math.round((store.counterfactual.recommended.risk_reduction ?? 0) * 100)}%.`
            : ""),
        environment: { model: h.model, events: h.telemetry_events, windows: h.state_windows, scenario: h.scenario },
        current_risk: f?.current ?? null,
        predicted_trajectory: f?.steps ?? [],
        confidence: f?.confidence ?? null,
        ood_flag: f?.ood_flag ?? null,
        key_signals: store.attributions ?? null,
        counterfactual: cf ?? null,
        attack_gravity: store.gravity?.critical_asset ?? null,
        provenance: store.provenance,
        disclaimer: "Risk values are model scores. Counterfactual numbers are simulated model-based risk changes, not causal effects. Stage mapping is a research proxy for MITRE ATT&CK.",
      };
      const { envelope, reportKey: generatedKey } = await encryptIncidentBriefWithKey(report);
      await downloadJson(envelope, `cybermind_incident_brief_encrypted_${Date.now()}.json`);
      setReportKey(generatedKey);
      // Clipboard access is independent of the completed save and must never hold the spinner.
      void copyReportKey(generatedKey).then(setKeyCopied);
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "The incident brief could not be encrypted.");
    } finally { setBusy(false); }
  };

  const decryptJson = async () => {
    setReportError("");
    if (!encryptedFile) { setReportError("Choose an encrypted incident brief JSON file."); return; }
    if (encryptedFile.size > 20 * 1024 * 1024) { setReportError("The encrypted report exceeds the 20 MB limit."); return; }
    if (!keyInput) { setReportError("Enter the report key or legacy passphrase."); return; }
    setBusy(true);
    try {
      const report = await decryptIncidentBrief(JSON.parse(await encryptedFile.text()), keyInput);
      setDecryptedReport(report);
      closeReportAction();
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "The encrypted report could not be read.");
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-6 max-w-5xl animate-in fade-in duration-300">
      <div className="space-y-5 pb-2">
        <Back onClick={onBack} />
        <div>
          <h1 className="font-editorial text-3xl font-normal tracking-tight text-[#171F27]">Reports &amp; Experiment Records</h1>
          <p className="text-xs text-[#707C8C] mt-2 font-medium">Every scenario run persists trajectory predictions and interventions for provenance.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={() => { setReportError(""); setReportAction("encrypt"); }}
            className="px-4 py-2.5 bg-[#DE5B49] hover:bg-[#C94735] text-white text-xs font-bold rounded-xl shadow-sm inline-flex items-center gap-2 transition-all">
            <LockKeyhole className="w-3.5 h-3.5" /> Export Encrypted Incident Brief (JSON)
          </button>
          <button onClick={() => { setReportError(""); setReportAction("decrypt"); }}
            className="px-4 py-2.5 bg-white hover:bg-[#FAF8F5] text-[#B94B3B] border border-[#E9C8C0] text-xs font-bold rounded-xl shadow-sm inline-flex items-center gap-2 transition-all">
            <UnlockKeyhole className="w-3.5 h-3.5" /> Decrypt Encrypted Incident Brief
          </button>
        </div>
      </div>

      {decryptedReport && (
        <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-[0_2px_8px_rgba(0,0,0,0.02)] p-5 space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><h3 className="font-bold text-sm text-[#171F27]">Decrypted incident brief</h3>
              <p className="text-xs text-[#707C8C] mt-1">Readable in this session. A downloaded readable copy is no longer encrypted.</p></div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => { void downloadJson(decryptedReport, `cybermind_incident_brief_readable_${Date.now()}.json`).catch((error) => setReportError(error instanceof Error ? error.message : "The readable report could not be saved.")); }}
                className="px-3 py-2 bg-[#171F27] hover:bg-[#2C3642] text-white text-xs font-bold rounded-xl flex items-center gap-2"><Download className="w-3.5 h-3.5" /> Download readable JSON</button>
              <button onClick={() => setDecryptedReport(null)} className="px-3 py-2 border border-[#EAE6DF] rounded-xl text-xs font-semibold text-[#556171]">Close preview</button>
            </div>
          </div>
          <pre className="max-h-80 overflow-auto rounded-xl border border-[#EAE6DF] bg-[#FAF8F5] p-4 text-[11px] text-[#424D5B] whitespace-pre-wrap break-words">{JSON.stringify(decryptedReport, null, 2)}</pre>
        </div>
      )}

      {reportAction && (
        <div className="fixed inset-0 z-50 bg-[#171F27]/50 flex items-center justify-center p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) closeReportAction(); }}>
          <div role="dialog" aria-modal="true" aria-label={reportAction === "encrypt" ? "Encrypt incident brief" : "Decrypt incident brief"}
            className="w-full max-w-lg bg-white rounded-2xl border border-[#EAE6DF] shadow-2xl p-6 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-[#FAF0ED] text-[#DE5B49]">{reportAction === "encrypt" ? <LockKeyhole className="w-5 h-5" /> : <UnlockKeyhole className="w-5 h-5" />}</div>
                <div><h2 className="font-editorial font-semibold text-lg text-[#171F27]">{reportAction === "encrypt" ? "Export encrypted incident brief" : "Decrypt encrypted incident brief"}</h2>
                  <p className="text-xs text-[#707C8C] mt-1">{reportAction === "encrypt" ? "The report is protected before leaving this browser." : "Open a shared report with its separate key or legacy passphrase."}</p></div>
              </div>
              <button type="button" aria-label="Close" onClick={closeReportAction} disabled={busy} className="text-[#8A95A4] hover:text-[#171F27]"><X className="w-4 h-4" /></button>
            </div>
            {reportAction === "decrypt" && <>
              <label className="block text-xs font-bold text-[#424D5B]">Encrypted incident brief JSON
                <span className="mt-2 flex items-center gap-2 p-3 border border-[#DDD6CC] rounded-xl text-[#556171] font-normal"><Upload className="w-4 h-4 shrink-0" /><input type="file" accept=".json,application/json" onChange={(event) => setEncryptedFile(event.target.files?.[0] ?? null)} className="block w-full min-w-0 text-xs" /></span>
              </label>
              <label className="block text-xs font-bold text-[#424D5B]">Report key or legacy passphrase
                <span className="mt-2 flex items-center border border-[#DDD6CC] rounded-xl focus-within:ring-2 focus-within:ring-[#DE5B49]/20">
                  <input type={showKey ? "text" : "password"} autoComplete="off" value={keyInput} onChange={(event) => setKeyInput(event.target.value)} className="w-full min-w-0 p-3 text-sm outline-none rounded-xl" placeholder="Paste the separately shared key" />
                  <button type="button" aria-label={showKey ? "Hide key" : "Show key"} onClick={() => setShowKey(!showKey)} className="p-3 text-[#707C8C]">{showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button>
                </span>
              </label>
            </>}
            {reportAction === "encrypt" && reportKey && <div className="rounded-xl border border-[#E9C8C0] bg-[#FFF8F5] p-4 space-y-3">
              <p className="text-xs font-bold text-[#B94B3B]">Encrypted report saved. Save its one-time key before closing.</p>
              <div className="flex items-center border border-[#E9C8C0] bg-white rounded-xl min-w-0">
                <input aria-label="Generated report key" readOnly type={showKey ? "text" : "password"} value={reportKey} className="min-w-0 flex-1 p-3 font-mono text-xs outline-none rounded-xl" />
                <button type="button" aria-label={showKey ? "Hide key" : "Show key"} onClick={() => setShowKey(!showKey)} className="p-3 text-[#707C8C]">{showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button>
              </div>
              <button type="button" onClick={() => { void copyReportKey(reportKey).then((copied) => copied ? setKeyCopied(true) : setReportError("Clipboard unavailable. Reveal and copy the key manually.")); }} className="px-3 py-2 bg-white border border-[#E9C8C0] text-[#B94B3B] rounded-xl text-xs font-bold">{keyCopied ? "Copied key again" : "Copy report key"}</button>
              <p className="text-xs text-[#707C8C]">{keyCopied ? "Key copied to clipboard. " : "Reveal and copy the key manually if clipboard access failed. "}Send it separately from the JSON; the app does not store it.</p>
            </div>}
            <p className="text-xs text-[#707C8C] leading-relaxed">AES-256-GCM runs locally. The encrypted JSON contains no secret key. The recipient can decrypt it inside CYBERMIND.</p>
            {reportError && <p role="alert" className="text-xs text-[#B33A2B] bg-[#FDF2F0] border border-[#F9DCD7] rounded-xl p-3">{reportError}</p>}
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={closeReportAction} disabled={busy} className="px-4 py-2 border border-[#EAE6DF] rounded-xl text-xs font-semibold text-[#556171]">Close</button>
              <button onClick={reportAction === "encrypt" ? exportJson : decryptJson} disabled={busy || (reportAction === "encrypt" && !!reportKey)}
                className={`px-4 py-2 text-white rounded-xl text-xs font-bold flex items-center gap-2 disabled:cursor-default ${reportAction === "encrypt" ? "bg-[#DE5B49] hover:bg-[#C94735] disabled:hover:bg-[#DE5B49]" : "bg-[#171F27] hover:bg-[#2C3642] disabled:opacity-50"}`}>
                {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : reportAction === "encrypt" ? reportKey ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Download className="w-3.5 h-3.5" /> : <UnlockKeyhole className="w-3.5 h-3.5" />}
                {reportAction === "encrypt" ? reportKey ? "Report saved" : "Encrypt & download" : "Decrypt & view"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-[0_2px_8px_rgba(0,0,0,0.02)] overflow-hidden">
        <div className="p-5 border-b border-[#F0EBE1] bg-[#FCFBF9]">
          <h3 className="font-bold text-sm text-[#171F27]">Historical Runs</h3>
        </div>
        {runs.length ? (
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-[#FAF8F5] border-b border-[#F0EBE1] text-[10px] font-bold uppercase tracking-widest text-[#8A95A4]">
                <th className="py-2.5 px-5">Run ID</th>
                <th className="py-2.5 px-5">Scenario</th>
                <th className="py-2.5 px-5 hidden sm:table-cell">Model Checkpoint</th>
                <th className="py-2.5 px-5">Timestamp</th>
                <th className="py-2.5 px-5 text-right">Predictions</th>
                <th className="py-2.5 px-5 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0EBE1]">
              {runs.map((r, index) => (
                <tr key={r.run_id ?? `incomplete-${index}`} className={`group transition-colors ${r.run_id ? "hover:bg-[#FAF8F5] cursor-pointer" : "text-[#8A95A4]"}`} onClick={() => { if (r.run_id) api.experiment(r.run_id).then(setDetail).catch(() => undefined); }}>
                  <td className="py-3 px-5 font-mono text-[11px] text-[#171F27] font-semibold">{r.run_id?.slice(0, 12) ?? "Incomplete record"}</td>
                  <td className="py-3 px-5 text-[#424D5B] font-medium">{r.scenario_id ?? "—"}</td>
                  <td className="py-3 px-5 hidden sm:table-cell font-mono text-[10px] text-[#707C8C]">{r.model_version ?? "—"}</td>
                  <td className="py-3 px-5 text-[#556171]">{r.start_time ? new Date(r.start_time * 1000).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : "—"}</td>
                  <td className="py-3 px-5 text-right font-mono font-medium text-[#171F27]">{r.prediction_count}</td>
                  <td className="py-3 px-5 text-[#DE5B49] opacity-0 group-hover:opacity-100 transition-opacity"><ArrowRight className="w-4 h-4" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-8 text-center flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-[#FAF8F5] flex items-center justify-center mb-3">
              <FileText className="w-5 h-5 text-[#A0AAB8]" />
            </div>
            <div className="text-sm font-bold text-[#171F27]">No experiment runs yet</div>
            <div className="text-xs text-[#707C8C] mt-1">Upload a PCAP or CSV and run an analysis to generate case records.</div>
          </div>
        )}
      </div>

      {detail && (
        <div className="bg-[#1C2229] p-5 rounded-2xl shadow-xl animate-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
            <h3 className="font-bold text-sm text-white flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#2EAA58]" />
              Run Inspection <span className="font-mono text-[11px] text-white/50 ml-1">{detail.run_id}</span>
            </h3>
            <button onClick={() => setDetail(null)} className="text-[10px] uppercase font-bold tracking-widest text-white/50 hover:text-white transition-colors">close</button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs mb-4">
            <div><span className="text-white/40 text-[9px] uppercase font-bold tracking-widest">Scenario</span><div className="font-bold text-white mt-1">{detail.scenario_id ?? "—"}</div></div>
            <div><span className="text-white/40 text-[9px] uppercase font-bold tracking-widest">Model</span><div className="font-mono text-white/90 mt-1 text-[11px]">{detail.model_version ?? "—"}</div></div>
            <div><span className="text-white/40 text-[9px] uppercase font-bold tracking-widest">Source Stream</span><div className="text-white/90 mt-1">{detail.source ?? "—"}</div></div>
            <div><span className="text-white/40 text-[9px] uppercase font-bold tracking-widest">Predictions Made</span><div className="font-mono font-bold text-emerald-400 mt-1 text-sm">{detail.predictions.length}</div></div>
          </div>
          <div className="mt-3 h-48 overflow-y-auto font-mono text-[10px] text-white/60 bg-black/40 rounded-xl p-3 space-y-1.5 custom-scrollbar border border-white/5">
            {detail.predictions.slice(-15).map((p, i) => (
              <div key={i} className="hover:text-white transition-colors">{JSON.stringify(p)}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/* ------------------------------ Knowledge Base ---------------------------- */
export const KnowledgeBaseView: React.FC<{ onBack: () => void }> = ({ onBack }) => (
  <div className="space-y-6 max-w-5xl animate-in fade-in duration-300">
    <div className="flex items-center gap-3 pb-2">
      <Back onClick={onBack} />
      <div>
        <h1 className="font-editorial text-3xl font-normal tracking-tight text-[#171F27]">System Architecture & Knowledge Base</h1>
        <p className="text-xs text-[#707C8C] mt-1 font-medium">Core concepts and methodologies driving the CYBERMIND engine.</p>
      </div>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {[
        ["Stage mapping (research proxy)", "Dataset labels map to 4 coarse stages via knowledge/stage_mapping.yaml: 0 benign, 1 recon/initial access, 2 execution/lateral, 3 impact/exfil. This mapping aligns with MITRE ATT&CK."],
        ["Attack Gravity", "Gravity(i) = baseline future risk − isolate-host future risk, computed by rolling the trained world model forward on mutated graph windows. Highest gravity = highest-leverage defensive target."],
        ["Counterfactual Risk Simulation", "Interventions (isolate host, block port, rate-limit) are applied to a cloned graph window; the same trained model rolls both futures forward. Differences are model-based risk changes, not causal effects."],
        ["Confidence & OOD", "Rollout entropy drives the confidence score; erratic trajectories raise the OOD flag, warning that predictions may be unreliable (unseen regime)."],
        ["World model loop", "Telemetry → 60s graph windows (30s stride) → GATv2 graph encoder → temporal transformer → latent dynamics → K-step rollout → risk / stage / future state heads."],
        ["Data honesty", "REAL DATASET (CIC-IDS2018), REPLAY (recorded files), LIVE (ingested telemetry) labels always reflect the true data source. No metric is fabricated."],
      ].map(([title, body]) => (
        <div key={title} className="bg-white p-5 rounded-2xl border border-[#EAE6DF] shadow-[0_2px_8px_rgba(0,0,0,0.02)] transition-all hover:shadow-[0_4px_12px_rgba(0,0,0,0.04)]">
          <h4 className="text-[13px] font-extrabold text-[#171F27] flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[#DE5B49]" />
            {title}
          </h4>
          <p className="text-[#5D6978] mt-2.5 leading-relaxed text-[11px] font-medium">{body}</p>
        </div>
      ))}
    </div>
  </div>
);

/* -------------------------------- Settings -------------------------------- */
export const SettingsView: React.FC<{ store: LiveStore; onBack: () => void }> = ({ store, onBack }) => {
  const m = store.health?.model;
  return (
    <div className="space-y-6 max-w-2xl animate-in fade-in duration-300">
      <div className="flex items-center gap-3 pb-2">
        <Back onClick={onBack} />
        <div>
          <h1 className="font-editorial text-3xl font-normal tracking-tight text-[#171F27]">System & Model Configuration</h1>
          <p className="text-xs text-[#707C8C] mt-1 font-medium">Neural engine parameters and telemetry diagnostics.</p>
        </div>
      </div>
      <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-[0_2px_8px_rgba(0,0,0,0.02)] overflow-hidden">
        <div className="p-5 border-b border-[#F0EBE1] bg-[#FCFBF9]">
          <h2 className="text-sm font-bold text-[#171F27]">Neural Engine Status</h2>
        </div>
        <div className="p-5 space-y-0 text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3.5 border-b border-stone-100 group">
            <div>
              <div className="font-bold text-[#171F27] text-[13px]">Model Checkpoint</div>
              <div className="text-[#8A95A4] mt-0.5 font-medium">Primary PyTorch weights loaded in memory</div>
            </div>
            <div className="mt-2 sm:mt-0 flex flex-col sm:items-end gap-1.5">
              <span className={`text-[10px] px-2.5 py-0.5 rounded font-bold uppercase tracking-wider w-fit ${m?.available ? "bg-[#EBF7EE] text-[#1E7B3E]" : "bg-[#FAF0ED] text-[#DE5B49]"}`}>{m?.available ? "Active" : "Missing"}</span>
              <span className="text-[#556171] font-mono text-[10px] bg-[#F7F5F0] px-2 py-0.5 rounded border border-[#E4DFD6]">{m?.checkpoint ?? "—"}</span>
            </div>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3.5 border-b border-stone-100 group">
            <div>
              <div className="font-bold text-[#171F27] text-[13px]">Inference Hardware</div>
              <div className="text-[#8A95A4] mt-0.5 font-medium">CUDA execution when available, CPU fallback</div>
            </div>
            <span className="mt-2 sm:mt-0 font-mono text-[#556171] font-bold bg-[#F7F5F0] px-2.5 py-1 rounded-lg border border-[#E4DFD6] shadow-sm">{m?.device ?? "—"}</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3.5 border-b border-stone-100 group">
            <div>
              <div className="font-bold text-[#171F27] text-[13px]">Rollout Horizon K</div>
              <div className="text-[#8A95A4] mt-0.5 font-medium">Temporal steps predicted ahead</div>
            </div>
            <span className="mt-2 sm:mt-0 font-mono text-[#171F27] font-bold text-sm">{store.forecast?.k ?? "—"}</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between py-3.5 group">
            <div>
              <div className="font-bold text-[#171F27] text-[13px]">Offline Isolation</div>
              <div className="text-[#8A95A4] mt-0.5 font-medium">Runtime is offline-first; no cloud calls</div>
            </div>
            <span className="mt-2 sm:mt-0 flex items-center gap-1.5 text-[#2EAA58] font-bold bg-[#EBF7EE] px-2.5 py-1 rounded-lg border border-[#C3E8CA]"><ShieldCheck className="w-3.5 h-3.5" /> Enforced</span>
          </div>
        </div>
        
        {m?.load_error ? (
          <div className="p-4 bg-[#FDF2F0] border-t border-[#F9DCD7] text-[#B33A2B] flex items-start gap-2.5 text-xs">
            <TriangleAlert className="w-4 h-4 shrink-0 mt-0.5" /><span className="font-mono">{m.load_error}</span>
          </div>
        ) : (
          <div className="p-4 bg-[#FAF8F5] border-t border-[#EAE6DF] flex items-center gap-2 text-[#8A95A4] text-[11px] font-medium">
            <FileText className="w-3.5 h-3.5" /> Swap models in checkpoints directory to upgrade the system.
          </div>
        )}
      </div>
      <SystemHealthCard health={store.health} wsUp={store.ws === "online"} />
    </div>
  );
};
