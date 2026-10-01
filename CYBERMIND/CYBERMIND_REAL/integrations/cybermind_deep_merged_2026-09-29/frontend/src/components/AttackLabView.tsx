import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  ArrowLeft, Loader2, Play, Square, RefreshCcw, ShieldCheck, Check, AlertTriangle
} from "lucide-react";
import type { LiveStore } from "../lib/live";
import { api } from "../lib/api";

interface VectorItem {
  id: string;
  name: string;
  target: string;
  protocol: string;
  mitre_technique: string;
  cwe: string;
  cve: string;
  severity: string;
  cvss: number;
  stage: number;
  description: string;
  is_patched: boolean;
  status: string;
}

const STAGE_LABEL: Record<number, string> = {
  1: "Initial Access",
  2: "Execution / Lateral",
};

const severityClass = (sev: string) =>
  sev === "CRITICAL"
    ? "text-[#B33A2B] border-[#F0C9C2] bg-[#FDF4F2]"
    : sev === "HIGH"
      ? "text-[#A05A1F] border-[#EBD9BC] bg-[#FCF7EC]"
      : "text-[#4B68B8] border-[#D3DBF0] bg-[#F4F7FD]";

export const AttackLabView: React.FC<{ store: LiveStore; onBack?: () => void }> = ({ store, onBack }) => {
  const [vectors, setVectors] = useState<VectorItem[]>([]);
  const [selectedVector, setSelectedVector] = useState("ssh_bruteforce");
  const [isProbing, setIsProbing] = useState(false);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [ollamaStatus, setOllamaStatus] = useState<any>(null);
  const [sandboxInfo, setSandboxInfo] = useState<any>(null);
  const [isResettingSandbox, setIsResettingSandbox] = useState(false);
  const [logs, setLogs] = useState<Array<{ text: string; color: string; time: string }>>([
    { text: "Attack Lab initialized. Target http://127.0.0.1:8081 [SANDBOX].", color: "text-slate-300", time: new Date().toLocaleTimeString() },
    { text: "Safety gate enforced. Non-destructive probes only.", color: "text-slate-300", time: new Date().toLocaleTimeString() },
    { text: "Neural world model connected for live risk scoring.", color: "text-emerald-400", time: new Date().toLocaleTimeString() }
  ]);
  const [isApplyingPatch, setIsApplyingPatch] = useState(false);
  const [patchSuccessMsg, setPatchSuccessMsg] = useState<string | null>(null);
  const [vectorPatches, setVectorPatches] = useState<Record<string, any>>({});
  const [riskAssessment, setRiskAssessment] = useState<any>(null);

  const termEndRef = useRef<HTMLDivElement | null>(null);

  const addLog = useCallback((text: string, color = "text-slate-300") => {
    setLogs((prev) => [...prev.slice(-80), { text, color, time: new Date().toLocaleTimeString() }]);
  }, []);

  useEffect(() => {
    termEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const refreshStatus = useCallback(async () => {
    try {
      const res = await api.attackLabStatus();
      if (res.vectors) setVectors(res.vectors);
      if (res.ollama_status) setOllamaStatus(res.ollama_status);
      if (res.active_session) setActiveSession(res.active_session);
      setSandboxInfo(res.sandbox_info ?? null);
      try {
        const ra = await api.attackLabRiskAssessment();
        setRiskAssessment(ra);
      } catch { /* assessment optional */ }
    } catch (err: any) {
      console.error(err);
    }
  }, []);

  const handleResetSandbox = async () => {
    setIsResettingSandbox(true);
    try {
      const res = await api.resetSandbox();
      addLog(`[SANDBOX] ${res.message || "Timer reset. Vulnerabilities reset."}`, "text-cyan-400 font-bold");
      setVectorPatches({});
      await refreshStatus();
    } catch (err: any) {
      addLog(`[ERROR] Failed to reset sandbox timer: ${err.message}`, "text-red-400");
    } finally {
      setIsResettingSandbox(false);
    }
  };

  useEffect(() => {
    refreshStatus();
    const timer = setInterval(refreshStatus, 2500);
    return () => clearInterval(timer);
  }, [refreshStatus]);

  const launchProbe = useCallback(async (vectorId: string) => {
    if (isProbing) return;
    const status = await api.attackLabStatus().catch(() => null);
    if (!status?.sandbox_online) {
      addLog("[ERROR] Bundled loopback sandbox is offline. Reopen CYBERMIND; no probe verdict was established.", "text-red-400 font-bold");
      setSandboxInfo(null);
      return;
    }
    setIsProbing(true);
    setPatchSuccessMsg(null);
    addLog(`>>> Strix probe launched: ${vectorId.toUpperCase()}`, "text-cyan-400 font-bold");

    try {
      const sess = await api.startAttackLabProbe(vectorId, "quick", 10);
      if (sess.error) {
        addLog(`[ERROR] ${sess.error}`, "text-red-400");
        setIsProbing(false);
        return;
      }
      setActiveSession(sess);

      let active = true;
      let count = 0;
      while (active && count < 60) {
        await new Promise((r) => setTimeout(r, 450));
        count++;
        const s = await api.attackLabStatus();
        if (s.active_session) {
          setActiveSession(s.active_session);
          const riskPct = ((s.active_session.final_risk || s.active_session.peak_risk || 0.02) * 100).toFixed(1);
          const summary = s.active_session.summary;
          const tally = summary ? ` (accepted ${summary.succeeded} / blocked ${summary.blocked}${summary.unreachable ? ` / down ${summary.unreachable}` : ""})` : "";
          addLog(`[PROBE] Step ${s.active_session.steps_completed}/${s.active_session.intensity}${tally}. Model risk ${riskPct}%`);            if (s.active_session.status !== "RUNNING") {
            active = false;
            if (s.active_session.status === "VECTOR_SUCCEEDED") {
              addLog(`[CONFIRMED] ${s.active_session.summary?.succeeded}/${s.active_session.intensity} probes accepted by target.`, "text-red-400 font-bold");
              if (s.active_session.llm_analysis) {
                addLog(`[LLM ANALYST] ${s.active_session.llm_analysis.analysis.slice(0, 160)}...`, "text-violet-300");
              }
              if (s.active_session.generated_patch) {
                addLog(`[AI PATCH] Remediation synthesized by ${s.active_session.generated_patch.engine}.`, "text-emerald-400 font-bold");
                setVectorPatches((prev) => ({ ...prev, [vectorId]: s.active_session.generated_patch }));
              }
            } else if (s.active_session.status === "PROBE_DEFLECTED") {
              addLog(`[DEFLECTED] All ${s.active_session.intensity} probes blocked by active defences. Target secured.`, "text-emerald-400 font-bold");
            } else if (s.active_session.status === "TARGET_UNREACHABLE") {
              addLog("[ERROR] Bundled sandbox target stopped during the probe. Reopen CYBERMIND; no verdict was established.", "text-red-400 font-bold");
            }
          }
        } else {
          active = false;
        }
      }
      refreshStatus();
    } catch (err: any) {
      addLog(`[ERROR] Probe failed: ${err.message}`, "text-red-400");
    } finally {
      setIsProbing(false);
    }
  }, [isProbing, addLog, refreshStatus]);

  const handleStopProbe = async () => {
    try {
      await api.stopAttackLabProbe();
      addLog("[STOP] Probe halted by analyst.", "text-amber-400");
      setIsProbing(false);
      refreshStatus();
    } catch (e: any) {
      console.error(e);
    }
  };

  const applyPatchForVector = useCallback(async (vectorId: string) => {
    const patchId = vectorPatches[vectorId]?.patch_id || activeSession?.generated_patch?.patch_id;
    if (!patchId) return;
    setIsApplyingPatch(true);
    setPatchSuccessMsg(null);
    addLog(`>>> Deploying patch ${patchId}...`, "text-emerald-400 font-bold");

    try {
      const res = await api.applyOneClickPatch(patchId, "security-analyst");
      const ver = res.verification;
      setPatchSuccessMsg(res.mitigation_summary || "Patch successfully deployed!");
      addLog(`[PATCH] ${res.mitigation_summary}`, "text-emerald-400 font-bold");
      if (ver) {
        addLog(`[VERIFIED] Re-probe: ${ver.blocked}/${ver.probes_sent} blocked, ${ver.succeeded} succeeded — ${ver.verified ? "vector CLOSED" : "vector STILL OPEN"}`, ver.verified ? "text-emerald-300 font-bold" : "text-red-400 font-bold");
      }
      if (res.activation_error) {
        addLog(`[WARN] Sandbox activation issue: ${res.activation_error}`, "text-amber-400");
      }
      setVectorPatches((prev) => ({
        ...prev,
        [res.vector_id]: { ...(prev[res.vector_id] || {}), patch_id: patchId, engine: res.engine || prev[res.vector_id]?.engine, target_file: res.target_file || prev[res.vector_id]?.target_file, patch_diff: prev[res.vector_id]?.patch_diff, what_happened: prev[res.vector_id]?.what_happened, what_to_do: prev[res.vector_id]?.what_to_do, applied: true, status: res.status, verification: res.verification },
      }));
      await refreshStatus();
      addLog("[VERIFICATION] Automatic re-probe to confirm target immunity...", "text-cyan-400");
      setTimeout(() => {
        void launchProbe(res.vector_id || vectorId);
      }, 800);
    } catch (err: any) {
      addLog(`[ERROR] Failed to apply patch: ${err.message}`, "text-red-400");
    } finally {
      setIsApplyingPatch(false);
    }
  }, [vectorPatches, activeSession, addLog, refreshStatus, launchProbe]);

  const sessionVector = activeSession?.vector_id || selectedVector;
  const generatedPatch = vectorPatches[sessionVector] || activeSession?.generated_patch;
  const currentRisk = ((activeSession?.final_risk || activeSession?.peak_risk || 0.018) * 100);
  const isHighRisk = currentRisk > 40;
  const selectedVec = vectors.find((v) => v.id === selectedVector);
  const sandboxVulns = sandboxInfo?.vulnerabilities || {};
  const riskByVector: Record<string, any> = {};
  (riskAssessment?.assessment || []).forEach((r: any) => { riskByVector[r.vector_id] = r; });

  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-[1500px] mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-[#EAE6DF]">
        <div className="flex items-center gap-3 min-w-0">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 rounded-lg hover:bg-[#F4F1EB] text-[#556171] hover:text-[#1C232B] transition-colors border border-transparent hover:border-[#E4DFD6]"
              title="Back to Command Center"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
          <div className="min-w-0">
            <h1 className="font-editorial text-2xl font-bold text-[#171F27] tracking-tight">Attack Labs</h1>
            <p className="text-xs text-[#707C8C] mt-0.5">
              Non-destructive adversarial probes against the isolated sandbox. Evidence-driven analysis, AI remediation, verified one-click patching.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5 text-[11px] font-mono shrink-0">
          <span className="px-3 py-1.5 rounded-lg bg-[#F8F6F0] border border-[#E2DBD0] text-[#333E4D]">
            TARGET <b className="text-[#171F27]">127.0.0.1:8081</b>
          </span>
          <span className="px-3 py-1.5 rounded-lg bg-[#F4FAF5] border border-[#CFE7D6] text-[#1E7B3E]">
            SAFETY <b>NON-EXPLOITING</b>
          </span>
          <span className="px-3 py-1.5 rounded-lg bg-[#F4F7FD] border border-[#D3DBF0] text-[#4B68B8]">
            ENGINE <b>{ollamaStatus?.available ? `Ollama ${ollamaStatus.active_model}` : "Codebuff"}</b>
          </span>
        </div>
      </div>

      {/* Sandbox status strip */}
      <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 px-6 py-4 border-b border-[#F0EBE1]">
          <div>
            <div className="flex items-center gap-2 flex-wrap text-sm font-bold text-[#171F27]">
              <span className={`w-2 h-2 rounded-full ${sandboxInfo ? "bg-emerald-500" : "bg-amber-500"}`} />
              Isolated sandbox target
              <span className="text-[11px] font-mono font-medium text-[#707C8C]">127.0.0.1:8081 · loopback only · host protected</span>
            </div>
            <div className="text-[11px] text-[#707C8C] mt-0.5">
              Probes execute in an isolated loopback process; flow telemetry feeds the trained world model for risk scoring.
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right font-mono text-[11px]">
              <span className="block text-[9px] text-[#8C95A3] uppercase tracking-wider">Self-destruct TTL</span>
              <span className="font-bold text-[#1C232B]">{sandboxInfo?.ttl_human || "3600s"}</span>
            </div>
            <button
              onClick={handleResetSandbox}
              disabled={isResettingSandbox}
              className="py-2 px-4 rounded-xl bg-white hover:bg-[#F8F6F0] border border-[#E2DBD0] text-[#333E4D] text-xs font-bold transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {isResettingSandbox ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCcw className="w-3.5 h-3.5" />}
              Reset Sandbox
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-[#F0EBE1]">
          {vectors.map((v) => (
            <button
              key={v.id}
              onClick={() => setSelectedVector(v.id)}
              className={`px-5 py-3.5 text-left transition-colors ${selectedVector === v.id ? "bg-[#FAF7F1]" : "hover:bg-[#FCFBF8]"}`}
            >
              <div className="text-[9px] font-mono uppercase tracking-wider text-[#8C95A3]">{v.cwe.split(":")[0]}</div>
              <div className="text-xs font-bold text-[#1C232B] mt-0.5 truncate">{v.name.split("&")[0].trim()}</div>
              <div className="flex items-center justify-between mt-1.5">
                <span className="text-[10px] font-mono text-[#707C8C]">{v.protocol}</span>
                <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
                  sandboxVulns[v.id] === "MITIGATED"
                    ? "bg-[#EBF7EE] text-[#1E7B3E]"
                    : "bg-[#FDF2F0] text-[#B33A2B]"
                }`}>
                  {sandboxInfo ? (sandboxVulns[v.id] || "UNKNOWN") : "TARGET OFFLINE"}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Console grid: vectors / analysis / remediation */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">

        {/* Vectors */}
        <section className="xl:col-span-4 space-y-4">
          <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] overflow-hidden">
            <div className="px-5 py-3.5 border-b border-[#F0EBE1] flex items-center justify-between bg-[#FCFBF9]">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#171F27]">Attack Vectors</h2>
              <span className="text-[10px] font-mono text-[#8C95A3]">
                {riskAssessment?.model_available
                  ? `GNN-ranked · baseline ${(riskAssessment.model_baseline_risk * 100).toFixed(1)}%`
                  : "manual execution"}
              </span>
            </div>
            <div className="divide-y divide-[#F0EBE1]">
              {vectors.map((vec) => {
                const isSelected = selectedVector === vec.id;
                const patch = vectorPatches[vec.id];
                const runningHere = isProbing && (activeSession?.vector_id === vec.id);
                return (
                  <div key={vec.id} className={`transition-colors ${isSelected ? "bg-[#FAF7F1]" : ""}`}>
                    <div className="px-5 py-4 cursor-pointer" onClick={() => setSelectedVector(vec.id)}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-[13px] font-bold text-[#171F27] leading-snug">
                            {riskByVector[vec.id] && (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-md bg-[#1C2329] text-white text-[10px] font-mono font-bold mr-1.5 align-[2px]">{riskByVector[vec.id].priority}</span>
                            )}
                            {vec.name}
                          </div>
                          <div className="text-[11px] font-mono text-[#707C8C] mt-1">
                            {vec.protocol} · {vec.cwe.split(":")[0]} · {vec.mitre_technique.split(" - ")[0]}
                          </div>
                          {riskByVector[vec.id] && (
                            <div className="mt-2 flex items-center gap-2">
                              <div className="w-24 h-1.5 rounded-full bg-[#EFEAE1] overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${riskByVector[vec.id].model_risk > 0.5 ? "bg-[#C54737]" : riskByVector[vec.id].model_risk > 0.25 ? "bg-[#E58B44]" : "bg-[#2EAA58]"}`}
                                  style={{ width: `${Math.min(100, Math.max(3, riskByVector[vec.id].model_risk * 100))}%` }}
                                />
                              </div>
                              <span className="text-[10px] font-mono text-[#707C8C]">GNN risk {riskByVector[vec.id].model_risk_pct}%</span>
                            </div>
                          )}
                        </div>
                        <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded uppercase shrink-0 border ${
                          vec.is_patched ? "bg-[#EBF7EE] text-[#1E7B3E] border-[#C3E8CA]" : "bg-[#FDF2F0] text-[#B33A2B] border-[#F9DCD7]"
                        }`}>
                          {vec.is_patched ? "SECURED" : "VULNERABLE"}
                        </span>
                      </div>

                      {isSelected && (
                        <dl className="mt-3 grid grid-cols-[86px_1fr] gap-x-3 gap-y-1.5 text-[11px]">
                          <dt className="text-[#8C95A3] font-mono uppercase text-[9px] pt-0.5">Affects</dt>
                          <dd className="font-mono text-[#333E4D]">{vec.target}</dd>
                          <dt className="text-[#8C95A3] font-mono uppercase text-[9px] pt-0.5">Severity</dt>
                          <dd>
                            <span className={`inline-block px-1.5 py-0.5 rounded border font-mono text-[9px] font-bold uppercase ${severityClass(vec.severity)}`}>
                              {vec.severity} · CVSS {vec.cvss}
                            </span>
                          </dd>
                          <dt className="text-[#8C95A3] font-mono uppercase text-[9px] pt-0.5">Stage</dt>
                          <dd className="text-[#333E4D]">{STAGE_LABEL[vec.stage] || "Other"}</dd>
                          <dt className="text-[#8C95A3] font-mono uppercase text-[9px] pt-0.5">Detail</dt>
                          <dd className="text-[#556171] leading-relaxed">{vec.description}</dd>
                        </dl>
                      )}
                    </div>

                    <div className="px-5 pb-4 flex items-center gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelectedVector(vec.id); launchProbe(vec.id); }}
                        disabled={isProbing}
                        className={`flex-1 py-2 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 disabled:opacity-40 ${
                          vec.is_patched
                            ? "bg-white text-[#1E7B3E] border border-[#C3E8CA] hover:bg-[#F4FAF5]"
                            : "bg-[#B33A2B] hover:bg-[#9E2F23] text-white"
                        }`}
                      >
                        {runningHere ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                        {vec.is_patched ? "Verify Defence" : "Try Attack"}
                      </button>
                      {patch && (
                        <span className={`text-[9px] font-mono font-bold px-2 py-1 rounded uppercase border ${
                          patch.verification?.verified
                            ? "bg-[#EBF7EE] text-[#1E7B3E] border-[#C3E8CA]"
                            : patch.applied
                              ? "bg-[#FDF2F0] text-[#B33A2B] border-[#F9DCD7]"
                              : "bg-[#FFF9E8] text-[#A05A1F] border-[#EBD9BC]"
                        }`}>
                          {patch.verification?.verified ? "FIXED" : patch.applied ? "FIX FAILED" : "FIX READY"}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="px-5 py-3 border-t border-[#F0EBE1] bg-[#FCFBF9] flex items-center justify-between">
              <span className="text-[10px] text-[#8C95A3] font-mono">
                {isProbing ? `Probe running on ${activeSession?.vector_id}` : "Idle"}
              </span>
              <button
                onClick={handleStopProbe}
                disabled={!isProbing}
                className="px-3 py-1.5 rounded-lg bg-white hover:bg-[#F8F6F0] border border-[#E2DBD0] text-[#333E4D] text-[11px] font-bold transition-all flex items-center gap-1.5 disabled:opacity-40"
              >
                <Square className="w-3 h-3" /> Stop
              </button>
            </div>
          </div>
        </section>

        {/* Live analysis */}
        <section className="xl:col-span-4 space-y-4">
          <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
            <div className="px-5 py-3.5 border-b border-[#F0EBE1] flex items-center justify-between bg-[#FCFBF9]">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#171F27]">Model Risk Assessment</h2>
              <span className="text-[10px] font-mono text-[#8C95A3]">best.pt</span>
            </div>
            <div className="px-5 py-5">
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-[#8C95A3]">Assessed risk</div>
                  <div className={`text-5xl font-extrabold font-mono tracking-tight mt-1 ${isHighRisk ? "text-[#B33A2B]" : "text-[#1E7B3E]"}`}>
                    {currentRisk.toFixed(1)}
                    <span className="text-xl text-[#98A2AF]">%</span>
                  </div>
                  <div className={`text-[11px] font-bold uppercase tracking-wide mt-1 ${isHighRisk ? "text-[#B33A2B]" : "text-[#1E7B3E]"}`}>
                    {isHighRisk ? "Elevated vulnerability detected" : "Benign — secured"}
                  </div>
                </div>
                <div className="text-right font-mono text-[11px] text-[#707C8C] space-y-1">
                  <div>PEAK <b className="text-[#171F27]">{((activeSession?.peak_risk || 0.018) * 100).toFixed(1)}%</b></div>
                  <div>FLOWS <b className="text-[#171F27]">{activeSession?.flows_generated || 0}</b></div>
                  <div>STATE <b className="text-[#171F27]">{activeSession?.status || "IDLE"}</b></div>
                </div>
              </div>
              <div className="w-full bg-[#EFEAE1] h-2 rounded-full overflow-hidden mt-4">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${isHighRisk ? "bg-[#C54737]" : "bg-[#2EAA58]"}`}
                  style={{ width: `${Math.min(100, Math.max(3, currentRisk))}%` }}
                />
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] overflow-hidden">
            <div className="px-5 py-3.5 border-b border-[#F0EBE1] flex items-center justify-between bg-[#FCFBF9]">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#171F27]">Probe Telemetry</h2>
              <span className={`text-[10px] font-mono font-bold flex items-center gap-1.5 ${isProbing ? "text-emerald-600" : "text-[#8C95A3]"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${isProbing ? "bg-emerald-500 animate-pulse" : "bg-[#C4CBD4]"}`} />
                {isProbing ? "STREAMING" : "IDLE"}
              </span>
            </div>
            <div className="h-[320px] bg-[#0D141D] px-4 py-3 text-[11px] leading-[1.7] font-mono overflow-y-auto custom-scroll text-slate-300">
              {logs.map((l, i) => (
                <div key={i} className={l.color}>
                  <span className="text-slate-600">[{l.time}]</span> {l.text}
                </div>
              ))}
              <div ref={termEndRef} />
            </div>
          </div>
        </section>

        {/* Analysis result + remediation */}
        <section className="xl:col-span-4 space-y-4">
          <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
            <div className="px-5 py-3.5 border-b border-[#F0EBE1] flex items-center justify-between bg-[#FCFBF9]">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#171F27]">Analysis Outcome</h2>
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                activeSession?.status === "VECTOR_SUCCEEDED"
                  ? "bg-[#FDF2F0] text-[#B33A2B] border-[#F9DCD7]"
                  : activeSession?.status === "PROBE_DEFLECTED"
                    ? "bg-[#EBF7EE] text-[#1E7B3E] border-[#C3E8CA]"
                    : "bg-[#F2EFE9] text-[#707C8C] border-[#E4DFD6]"
              }`}>
                {activeSession?.status || "AWAITING PROBE"}
              </span>
            </div>
            <div className="px-5 py-4">
              {activeSession?.status === "PROBE_DEFLECTED" ? (
                <div className="text-xs text-[#1E7B3E] flex items-start gap-2">
                  <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>All probes were blocked by active defences. The target held against this vector.</span>
                </div>
              ) : activeSession?.findings?.length > 0 ? (
                <div className="space-y-2.5">
                  <div className="text-[13px] font-bold text-[#171F27] leading-snug">{activeSession.findings[0].title}</div>
                  <div className="text-[11px] font-mono text-[#707C8C]">
                    {activeSession.findings[0].target} · CVSS {activeSession.findings[0].cvss} · {activeSession.findings[0].cwe.split(":")[0]}
                  </div>
                  <p className="text-[11px] text-[#556171] leading-relaxed bg-[#FAF8F5] border border-[#E8E2D7] p-3 rounded-xl">
                    {activeSession.findings[0].evidence}
                  </p>
                </div>              ) : (
              <div className="text-xs text-[#707C8C] py-2 leading-relaxed">
                  Run an attack from the vector list. Verdicts are derived from the sandbox's actual HTTP responses, never assumed.
                </div>
              )}
              {activeSession?.llm_analysis && (
                <div className="mt-3 rounded-xl border border-[#DED9EE] bg-[#F8F6FC] px-3.5 py-2.5">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-[#5B4B9E] mb-1">
                    LLM analyst · {activeSession.llm_analysis.provider}
                  </div>
                  <p className="text-[11px] text-[#556171] leading-relaxed">{activeSession.llm_analysis.analysis}</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
            <div className="px-5 py-3.5 border-b border-[#F0EBE1] flex items-center justify-between bg-[#FCFBF9]">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#171F27]">AI Remediation</h2>
              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-[#EBF7EE] text-[#1E7B3E] font-bold uppercase">
                {generatedPatch?.engine ? generatedPatch.engine : "standby"}
              </span>
            </div>

            {generatedPatch ? (
              <div className="px-5 py-4 space-y-3.5">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#707C8C] truncate">{generatedPatch.target_file}</span>
                  <span className={`font-bold shrink-0 ${generatedPatch.verification?.verified ? "text-[#1E7B3E]" : "text-[#A05A1F]"}`}>
                    {generatedPatch.status || "READY_TO_APPLY"}
                  </span>
                </div>

                {generatedPatch.patch_diff && (
                  <div className="bg-[#0D141D] text-emerald-400 px-4 py-3 rounded-xl text-[10px] leading-[1.7] font-mono overflow-x-auto max-h-[200px] custom-scroll">
                    <pre className="whitespace-pre">{generatedPatch.patch_diff}</pre>
                  </div>
                )}

                {generatedPatch.what_happened && (
                  <div>
                    <div className="text-[9px] font-bold uppercase tracking-wider text-[#B33A2B] mb-1">What happened</div>
                    <p className="text-[11px] text-[#556171] leading-relaxed">{generatedPatch.what_happened}</p>
                  </div>
                )}

                {(generatedPatch.what_to_do || generatedPatch.mitigation_actions)?.length > 0 && (
                  <div>
                    <div className="text-[9px] font-bold uppercase tracking-wider text-[#1E7B3E] mb-1">What to do</div>
                    <ul className="space-y-1">
                      {(generatedPatch.what_to_do || generatedPatch.mitigation_actions).map((a: string, i: number) => (
                        <li key={i} className="text-[11px] text-[#556171] leading-relaxed flex gap-2">
                          <span className="font-mono text-[#98A2AF] shrink-0">{String(i + 1).padStart(2, "0")}</span>
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {generatedPatch.verification && (
                  <div className="rounded-xl border border-[#E4DFD6] bg-[#FAF8F5] px-3.5 py-2.5 text-[11px] font-mono text-[#333E4D]">
                    Verification — blocked {generatedPatch.verification.blocked}/{generatedPatch.verification.probes_sent}, succeeded {generatedPatch.verification.succeeded} · hash {generatedPatch.verification.verification_hash}
                  </div>
                )}

                <button
                  onClick={() => applyPatchForVector(sessionVector)}
                  disabled={isApplyingPatch || generatedPatch.applied}
                  className="w-full py-3 rounded-xl bg-[#1E7B3E] hover:bg-[#186634] disabled:opacity-40 text-white font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2"
                >
                  {isApplyingPatch ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  {generatedPatch.applied ? "Patch Deployed — Target Secured" : "Apply Fix Patch"}
                </button>

                {patchSuccessMsg && (
                  <div className="bg-[#F4FAF5] border border-[#C3E8CA] text-[#1E7B3E] px-3.5 py-2.5 rounded-xl text-[11px] leading-relaxed">
                    {patchSuccessMsg}
                  </div>
                )}
              </div>
            ) : activeSession?.status === "PROBE_DEFLECTED" ? (
              <div className="px-5 py-6 text-xs text-[#707C8C] text-center">
                Target is already secured against this vector. No patch required.
              </div>
            ) : (
              <div className="px-5 py-6 text-xs text-[#707C8C] text-center leading-relaxed">
                When a probe confirms an unmitigated vector, the AI engine synthesizes the remediation diff and a one-click verified fix appears here.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};
