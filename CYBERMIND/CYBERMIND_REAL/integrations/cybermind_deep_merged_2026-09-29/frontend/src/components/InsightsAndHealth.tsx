import React from "react";
import { ArrowRight, Sparkles, ShieldCheck, Loader2, Cpu, MemoryStick, Zap, FlaskConical } from "lucide-react";
import type { Attribution, HealthResponse, Counterfactual, AttackGravity } from "../lib/api";

/* --------------------------- Model Insights Card -------------------------- */
export const ModelInsightsCard: React.FC<{
  attributions: Attribution[] | null;
  attributionHost: string | null;
  busy: boolean;
  onRunExplain: () => void;
  hasState: boolean;
  nodeCount: number;
}> = ({ attributions, attributionHost, busy, onRunExplain, hasState, nodeCount }) => {
  const max = attributions ? Math.max(...attributions.map((a) => a.attribution), 1e-9) : 1;
  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-[#DE5B49]"><Sparkles className="w-4 h-4" /></div>
            <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Model Insights</h2>
          </div>
          <button onClick={onRunExplain} disabled={busy || !hasState || nodeCount === 0}
            className="flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            <span>{busy ? "Computing…" : attributions ? "Recompute" : "Run Explainer"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {!hasState || nodeCount === 0 ? (
          <div className="text-[11px] text-[#7A8696] mt-3 leading-relaxed">
            Attribution needs a graph state. Start a scenario or feed telemetry, then run the explainer to see
            gradient × input feature attributions from the trained model.
          </div>
        ) : attributions ? (
          <>
            <div className="mt-3.5">
              <div className="flex items-center justify-between text-[11px] font-semibold text-[#8C96A3] pb-1.5 border-b border-[#F0ECE4]">
                <span>Top contributing signals {attributionHost ? `· ${attributionHost}` : ""}</span>
                <span>attribution</span>
              </div>
              <div className="space-y-2 mt-2">
                {attributions.slice(0, 5).map((a) => (
                  <div key={a.feature}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#2B3542] font-medium truncate pr-2">{a.feature.replace(/_/g, " ")}</span>
                      <span className="font-bold text-[#35404F] text-[11px] font-mono">{a.attribution.toFixed(4)}</span>
                    </div>
                    <div className="h-1.5 bg-[#EFECE5] rounded-full overflow-hidden mt-1">
                      <div className="h-full bg-[#4B68B8] rounded-full transition-all duration-700" style={{ width: `${Math.max(3, (a.attribution / max) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="text-[10px] text-[#8C96A3] mt-3 leading-relaxed">
              Gradient × input attribution computed on the current window by the trained CYBERMIND model.
              Evidence, not SHAP, not causal proof.
            </div>
          </>
        ) : (
          <div className="text-[11px] text-[#7A8696] mt-3 leading-relaxed">
            Click <span className="font-semibold">Run Explainer</span> to attribute the current forecast to input features
            (flow counts, peer pressure, ports, timing…).
          </div>
        )}
      </div>
    </div>
  );
};

/* -------------------------- Defence Recommendation ------------------------ */
export const DefenceCard: React.FC<{
  cf: Counterfactual | null;
  gravity: AttackGravity | null;
  busyCf: boolean;
  busyGravity: boolean;
  onRunCf: () => void;
  onRunGravity: () => void;
  modelAvailable: boolean;
}> = ({ cf, gravity, busyCf, busyGravity, onRunCf, onRunGravity, modelAvailable }) => {
  const rec = cf?.recommended;
  const critical = gravity?.critical_asset;
  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-[#2EAA58]"><ShieldCheck className="w-4 h-4" /></div>
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Defence Recommendation</h2>
        </div>
        <span className="text-[9px] font-bold uppercase tracking-wider text-[#98A2AF]">counterfactual engine</span>
      </div>

      {!modelAvailable ? (
        <div className="text-[11px] text-[#B33A2B] mt-3 leading-relaxed bg-[#FDF2F0] border border-[#F9DCD7] rounded-xl p-3">
          Model not loaded — counterfactual simulation is unavailable. Check the configured model path in Settings.
        </div>
      ) : (
        <>
          <div className="flex gap-2 mt-3">
            <button onClick={onRunCf} disabled={busyCf}
              className="flex-1 py-2 px-3 rounded-xl text-xs font-bold bg-[#DE5B49] hover:bg-[#C94838] text-white shadow-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5">
              {busyCf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {busyCf ? "Simulating futures…" : "Run Counterfactual"}
            </button>
            <button onClick={onRunGravity} disabled={busyGravity}
              className="flex-1 py-2 px-3 rounded-xl text-xs font-bold bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#424F60] transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5">
              {busyGravity ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FlaskConical className="w-3.5 h-3.5" />}
              {busyGravity ? "Scoring…" : "Attack Gravity"}
            </button>
          </div>

          {critical && (
            <div className="mt-3 p-3 bg-[#FAF6F2] border border-[#EBE3D7] rounded-xl">
              <div className="text-[10px] font-semibold text-[#7C8796] uppercase">Critical Asset (highest gravity)</div>
              <div className="flex items-center justify-between mt-1">
                <span className="font-mono font-bold text-sm text-[#1F2731]">{critical.host}</span>
                <span className="font-mono text-xs text-[#E58B44] font-bold">gravity {critical.attack_gravity.toFixed(3)}</span>
              </div>
              <div className="text-[11px] text-[#556171] mt-1">
                baseline {critical.baseline_risk.toFixed(3)} → isolated {critical.counterfactual_risk.toFixed(3)}
              </div>
            </div>
          )}

          {rec ? (
            <div className="mt-3 border-2 border-[#DE5B49]/25 bg-[#FDF7F5] rounded-xl p-3.5">
              <div className="text-[10px] font-semibold text-[#B33A2B] uppercase tracking-wider">Recommended action</div>
              <div className="text-base font-black text-[#1C232B] mt-0.5">
                {rec.action_label}{rec.host ? ` · ${rec.host}` : ""}{rec.port ? ` · port ${rec.port}` : ""}
              </div>
              <div className="grid grid-cols-3 gap-2 mt-2.5 text-center">
                <div className="bg-white rounded-lg border border-[#EAE3D7] p-2">
                  <div className="text-[9px] uppercase font-bold text-[#8A95A4]">Baseline</div>
                  <div className="font-bold text-sm text-[#29323E]">{(cf!.baseline.risk * 100).toFixed(1)}%</div>
                </div>
                <div className="bg-white rounded-lg border border-[#EAE3D7] p-2">
                  <div className="text-[9px] uppercase font-bold text-[#8A95A4]">After action</div>
                  <div className="font-bold text-sm text-[#29323E]">{(rec.future_risk * 100).toFixed(1)}%</div>
                </div>
                <div className="bg-white rounded-lg border border-[#EAE3D7] p-2">
                  <div className="text-[9px] uppercase font-bold text-[#8A95A4]">Reduction</div>
                  <div className="font-bold text-sm text-[#2EAA58]">−{(rec.risk_reduction * 100).toFixed(1)}%</div>
                </div>
              </div>
              <div className="text-[10px] text-[#8C96A3] mt-2 leading-relaxed">{cf?.disclaimer}</div>
            </div>
          ) : cf ? (
            <div className="mt-3 p-3 bg-stone-50 rounded-xl text-[11px] text-stone-600">
              No intervention reduces predicted risk below baseline — the model expects no benefit from isolation in this state.
            </div>
          ) : (
            <div className="mt-3 text-[11px] text-[#7A8696] leading-relaxed">
              Simulate interventions (isolate each host, block ports, rate-limit) and rank them by predicted
              future risk using the trained world model.
            </div>
          )}

          {cf?.interventions?.length ? (
            <div className="mt-3 pt-3 border-t border-[#F0ECE4] overflow-y-auto max-h-44">
              <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-1.5">Ranked interventions</div>
              {cf.interventions.slice(0, 8).map((r, i) => (
                <div key={i} className="flex items-center justify-between text-[11px] py-1 border-b border-[#F5F2EB] last:border-0">
                  <span className="text-[#2B3542] font-medium truncate">{r.action_label}{r.host ? ` · ${r.host}` : ""}</span>
                  <span className="font-mono text-[#424D5B]">{(r.future_risk * 100).toFixed(1)}%</span>
                  <span className={`font-mono w-14 text-right ${r.risk_reduction > 0 ? "text-[#2EAA58]" : "text-[#B33A2B]"}`}>
                    {r.risk_reduction > 0 ? "−" : "+"}{Math.abs(r.risk_reduction * 100).toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
};

/* ----------------------------- SystemHealthCard --------------------------- */
export const SystemHealthCard: React.FC<{ health: HealthResponse | null; wsUp: boolean }> = ({ health, wsUp }) => {
  const m = health?.model;
  const rows = [
    { name: "Backend API", ok: !!health, note: health ? "operational" : "connecting…" },
    { name: "Model Inference", ok: !!m?.available, note: m ? (m.available ? `${m.device}` : m.status) : "…" },
    { name: "Telemetry Pipeline", ok: !!health, note: health ? `${health.telemetry_events} events` : "…" },
    { name: "State Windows", ok: (health?.state_windows ?? 0) > 0, note: `${health?.state_windows ?? 0} buffered` },
    { name: "WebSocket", ok: wsUp, note: wsUp ? "connected" : "reconnecting…" },
  ];
  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center gap-2">
          <div className="text-[#2EAA58]"><ShieldCheck className="w-4 h-4" /></div>
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">System Health</h2>
        </div>
        <div className="text-xs text-[#7A8696] font-medium mt-1">
          {m?.available ? "All core systems operational" : "Degraded — model checkpoint missing"}
        </div>
        <div className="space-y-2 mt-3.5 min-w-0">
          {rows.map((r) => (
            <div key={r.name} className="min-w-0 flex flex-wrap items-center justify-between gap-x-2 text-xs py-0.5">
              <div className="min-w-0 flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${r.ok ? "bg-[#2EAA58]" : "bg-[#E58B44]"}`} />
                <span className="font-medium text-[#2B3542]">{r.name}</span>
              </div>
              <span className="min-w-0 truncate font-mono text-[11px] text-[#8692A2]">{r.note}</span>
            </div>
          ))}
        </div>
        {m?.available && (
          <div className="min-w-0 flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-[#F0ECE4] text-[10px] text-[#7C8898] font-mono">
            <span className="flex items-center gap-1"><Cpu className="w-3 h-3" />{m.device}</span>
            <span className="flex items-center gap-1"><MemoryStick className="w-3 h-3" />{m.parameters != null ? `${(m.parameters / 1e6).toFixed(2)}M params` : "params unavailable"}</span>
            <span className="min-w-0 flex items-center gap-1 break-all"><Zap className="w-3 h-3 shrink-0" />{m.version}</span>
          </div>
        )}
      </div>
    </div>
  );
};
