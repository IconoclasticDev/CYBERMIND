import React, { useState, useEffect } from "react";
import {
  X, ShieldAlert, Check, Loader2, Sparkles, Network, Zap,
  GitBranch, ShieldCheck, Code, AlertTriangle, ArrowRight, Play,
} from "lucide-react";
import type { UINode } from "../lib/adapters";
import type { Counterfactual, AttackGravity } from "../lib/api";
import { api } from "../lib/api";

interface NodeDetailDrawerProps {
  node: UINode | null;
  onClose: () => void;
  onIsolateNode: (node: UINode) => Promise<Counterfactual | null>;
  gravity: AttackGravity | null;
  eventsForHost: Array<{ time: string; label: string; dst?: string; port?: number }>;
  onRunExplain: (hostIndex: number, hostId: string) => void;
  explainBusy: boolean;
  attributions: Array<{ feature: string; attribution: number; share?: number }> | null;
  onTakeToParallelFutures?: (node: UINode) => void;
  onAttackWithStrix?: (node: UINode, vectorId?: string) => void;
  onDefendNode?: (node: UINode, patchId: string) => Promise<boolean>;
  isDefended?: boolean;
}

export const NodeDetailDrawer: React.FC<NodeDetailDrawerProps> = ({
  node, onClose, onIsolateNode, gravity, eventsForHost, onRunExplain, explainBusy, attributions,
  onTakeToParallelFutures, onAttackWithStrix, onDefendNode, isDefended = false,
}) => {
  const [tab, setTab] = useState<"overview" | "strix-defense" | "containment" | "explain">("overview");
  const [cf, setCf] = useState<Counterfactual | null>(null);
  const [working, setWorking] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  // Strix probe & AI patch states
  const [vectorId, setVectorId] = useState<string>("ssh_bruteforce");
  const [probeRunning, setProbeRunning] = useState(false);
  const [probeStep, setProbeStep] = useState(0);
  const [probeRisk, setProbeRisk] = useState<number | null>(null);
  const [probeSession, setProbeSession] = useState<any>(null);
  const [patchLoading, setPatchLoading] = useState(false);
  const [patchData, setPatchData] = useState<any>(null);
  const [patchApplying, setPatchApplying] = useState(false);
  const [patchSuccess, setPatchSuccess] = useState<string | null>(null);

  // Auto-detect best probe vector from host communications
  useEffect(() => {
    if (!node) return;
    const hasSsh = eventsForHost.some((e) => e.port === 22 || e.label.toLowerCase().includes("ssh"));
    const hasSql = eventsForHost.some((e) => e.port === 8081 || e.port === 80 || e.label.toLowerCase().includes("sql"));
    const hasSmb = eventsForHost.some((e) => e.port === 445 || e.label.toLowerCase().includes("smb"));
    const hasBot = eventsForHost.some((e) => e.label.toLowerCase().includes("bot") || e.label.toLowerCase().includes("c2"));

    if (hasSql) setVectorId("sqli_probe");
    else if (hasSmb) setVectorId("smb_lateral");
    else if (hasBot) setVectorId("c2_beacon");
    else if (hasSsh) setVectorId("ssh_bruteforce");
    else setVectorId(node.threatScore >= 80 ? "ssh_bruteforce" : "sqli_probe");

    setProbeSession(null);
    setPatchData(null);
    setPatchSuccess(null);
  }, [node?.id]);

  if (!node) return null;
  const g = gravity?.gravity.find((x) => x.host === node.id);
  const isHighRisk = (node.threatScore >= 50 || node.status !== "normal") && !isDefended;

  const simulate = async () => {
    setWorking(true);
    setDone(null);
    try {
      const res = await onIsolateNode(node);
      setCf(res);
      if (res) setDone("Simulated — this is a model-based counterfactual, not a live network change.");
    } finally {
      setWorking(false);
    }
  };

  // Launch Strix probe against this node in sandbox
  const handleLaunchStrixProbe = async () => {
    setProbeRunning(true);
    setPatchSuccess(null);
    setProbeStep(0);
    try {
      const port = vectorId === "ssh_bruteforce" ? 22 : vectorId === "sqli_probe" ? 8081 : vectorId === "smb_lateral" ? 445 : 8080;
      await api.startAttackLabProbe(vectorId, "quick", 10, node.id, port);
      let count = 0;
      const poll = setInterval(async () => {
        count++;
        setProbeStep(Math.min(10, count));
        try {
          const s = await api.attackLabStatus();
          setProbeSession(s?.active_session);
          if (s?.active_session?.peak_risk) {
            setProbeRisk(s.active_session.peak_risk * 100);
          }
          if (s?.active_session?.generated_patch) {
            setPatchData(s.active_session.generated_patch);
          }
          if (!s?.active_session || s.active_session.status !== "RUNNING" || count >= 12) {
            clearInterval(poll);
            setProbeRunning(false);
            if (s?.active_session?.generated_patch) {
              setPatchData(s.active_session.generated_patch);
            }
          }
        } catch {
          clearInterval(poll);
          setProbeRunning(false);
        }
      }, 500);
    } catch {
      setProbeRunning(false);
    }
  };

  // Directly fetch/suggest AI patch for this host
  const handleSuggestPatch = async () => {
    setPatchLoading(true);
    setPatchSuccess(null);
    try {
      const port = vectorId === "ssh_bruteforce" ? 22 : vectorId === "sqli_probe" ? 8081 : vectorId === "smb_lateral" ? 445 : 8080;
      const res = await api.suggestPatchForHost(node.id, vectorId, port);
      if (res?.patch) {
        setPatchData(res.patch);
      }
    } catch (e) {
      console.error("Failed to suggest patch", e);
    } finally {
      setPatchLoading(false);
    }
  };

  // Apply 1-click patch to defend this node
  const handleApplyPatch = async () => {
    const patchId = patchData?.patch_id || probeSession?.generated_patch?.patch_id;
    if (!patchId) return;
    setPatchApplying(true);
    try {
      const res = await api.applyOneClickPatch(patchId);
      setPatchSuccess(res.mitigation_summary || "Patch result returned for best.pt.");
      if (onDefendNode) {
        await onDefendNode(node, patchId);
      }
      setPatchData((prev: any) => (prev ? { ...prev, applied: true } : prev));
    } catch (e) {
      console.error("Failed to apply patch", e);
    } finally {
      setPatchApplying(false);
    }
  };

  const risk = cf?.interventions.find((i) => i.host === node.id);
  const attrMax = attributions ? Math.max(...attributions.map((a) => a.attribution), 1e-9) : 1;

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white border-l border-[#E2DDD3] shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-200"
      role="dialog"
      aria-label={`Node detail ${node.id}`}
    >
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Drawer Header */}
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-sm font-mono text-[10px] font-bold ${isDefended ? "bg-[#1E7A43]" : "bg-[#2B3B4C]"}`}>
              {isDefended ? <ShieldCheck className="w-5 h-5 text-white" /> : node.id.split(".").slice(-2).join(".")}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base text-[#1C232B] font-mono">{node.id}</h3>
                {isDefended ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#EBF7EE] text-[#1E7B3E] border border-[#C3E8CA]">
                    DEFENDED &amp; SECURED
                  </span>
                ) : (
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    node.status === "compromised" ? "bg-[#FDF2F0] text-[#DE5B49] border border-[#F9DCD7]"
                    : node.status === "medium-risk" ? "bg-[#FEF6EE] text-[#E58B44] border border-[#FCE6D0]"
                    : node.status === "high-risk" ? "bg-[#FDF2F0] text-[#D9654C] border border-[#F9DCD7]"
                    : "bg-[#F1F4F8] text-[#556375] border border-[#DCE3EC]"}`}>
                    {node.status}
                  </span>
                )}
              </div>
              <div className="text-xs text-[#7A8696] mt-0.5">
                observed endpoint &bull; index {node.index} &bull; target sandbox boundary
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[#EFEAE2] text-[#8692A2] hover:text-[#1C232B] transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* High-Risk Hero Remediation Action Banner */}
        {isHighRisk && (
          <div className="bg-[#FAF0ED] border-b border-[#F4D0C9] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-[#DE5B49] font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-[#DE5B49]" />
                <span>CRITICAL COMPROMISE / HIGH RISK NODE</span>
              </div>
              <span className="text-[10px] font-mono font-bold bg-[#DE5B49] text-white px-2 py-0.5 rounded-full">
                Risk {node.threatScore}/100
              </span>
            </div>
            <p className="text-[11px] text-[#556171] leading-relaxed">
              Target this node in Parallel Futures, launch an adversarial Strix probe in the sandbox, or directly synthesize and deploy a 1-click AI patch.
            </p>
            <div className="grid grid-cols-3 gap-1.5 pt-0.5">
              <button
                onClick={() => onTakeToParallelFutures?.(node)}
                className="py-1.5 px-2 bg-white hover:bg-[#F4ECE2] text-[#4F5968] border border-[#DDD6CC] rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors cursor-pointer"
              >
                <GitBranch className="w-3.5 h-3.5 text-[#E58B44]" />
                <span>Parallel Futures</span>
              </button>
              <button
                onClick={() => setTab("strix-defense")}
                className="py-1.5 px-2 bg-[#FAF0ED] hover:bg-[#F7DDD7] text-[#DE5B49] border border-[#F4D0C9] rounded-lg text-[11px] font-bold flex items-center justify-center gap-1 transition-colors cursor-pointer"
              >
                <Zap className="w-3.5 h-3.5 fill-[#DE5B49]" />
                <span>Strix Probe</span>
              </button>
              <button
                onClick={() => {
                  setTab("strix-defense");
                  if (!patchData) void handleSuggestPatch();
                }}
                className="py-1.5 px-2 bg-[#1E7A43] hover:bg-[#176636] text-white rounded-lg text-[11px] font-bold flex items-center justify-center gap-1 shadow-xs transition-colors cursor-pointer"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>1-Click Patch</span>
              </button>
            </div>
          </div>
        )}

        {done && (
          <div className="bg-[#E7F7ED] border-b border-[#C6EBD1] text-[#248B47] px-4 py-2 text-xs font-semibold flex items-center gap-2">
            <Check className="w-4 h-4 shrink-0" />
            <span>{done}</span>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="flex border-b border-[#EDE6DC] px-4 bg-white text-xs font-semibold text-[#768292]">
          {(["overview", "strix-defense", "containment", "explain"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-2.5 px-3 border-b-2 transition-colors flex items-center gap-1.5 cursor-pointer ${
                tab === t
                  ? "border-[#DE5B49] text-[#DE5B49] font-bold"
                  : "border-transparent hover:text-[#1C232B]"
              }`}
            >
              {t === "strix-defense" ? (
                <>
                  <Zap className="w-3.5 h-3.5 text-[#DE5B49]" />
                  <span>Strix &amp; AI Patch</span>
                </>
              ) : t === "containment" ? (
                <>
                  <ShieldAlert className="w-3.5 h-3.5 text-[#E58B44]" />
                  <span>Parallel Futures</span>
                </>
              ) : (
                <span className="capitalize">{t}</span>
              )}
            </button>
          ))}
        </div>

        {/* Scrollable Tab Content */}
        <div className="p-4 overflow-y-auto flex-1 space-y-4 text-xs">
          {/* TAB 1: OVERVIEW */}
          {tab === "overview" && (
            <>
              <div className="bg-[#FAF6F2] border border-[#EBE3D7] rounded-xl p-3.5 flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-semibold text-[#7C8796] uppercase">Anomaly / Threat Score</div>
                  <div className={`text-xl font-black mt-0.5 ${isDefended ? "text-[#1E7A43]" : "text-[#DE5B49]"}`}>
                    {isDefended ? "5 / 100" : `${node.threatScore} / 100`}
                  </div>
                  <div className="text-[11px] text-[#556171] mt-0.5">
                    {isDefended ? "defended by 1-click AI patch & verified" : "from the current graph window features"}
                  </div>
                </div>
                {g && (
                  <div className="text-right">
                    <div className="text-[10px] font-semibold text-[#7C8796] uppercase">Attack Gravity</div>
                    <div className="text-xl font-black text-[#E58B44] mt-0.5">{g.attack_gravity.toFixed(3)}</div>
                    <div className="text-[11px] text-[#556171] mt-0.5">isolate-host risk drop</div>
                  </div>
                )}
              </div>

              <div className="space-y-2 border border-[#EDE7DE] rounded-xl p-3.5 bg-white">
                <div className="flex justify-between py-1 border-b border-[#F5F2EB]">
                  <span className="text-[#7A8696]">Baseline risk (model)</span>
                  <span className="font-mono font-semibold text-[#29323E]">{g ? g.baseline_risk.toFixed(3) : "run GRAVITY"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#F5F2EB]">
                  <span className="text-[#7A8696]">Risk if isolated (simulated)</span>
                  <span className="font-mono font-semibold text-[#29323E]">{g ? g.counterfactual_risk.toFixed(3) : "—"}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#7A8696]">Observed flows (this window)</span>
                  <span className="font-semibold text-[#29323E]">{eventsForHost.length}</span>
                </div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-2">Recent flows involving this host</div>
                {eventsForHost.length ? (
                  <div className="divide-y divide-[#EDE7DE] border border-[#EDE7DE] rounded-xl overflow-hidden">
                    {eventsForHost.slice(0, 8).map((e, i) => (
                      <div key={i} className="flex items-center justify-between p-2.5 bg-white hover:bg-[#FAF8F5]">
                        <span className="font-mono text-[11px] text-[#424D5B]">{e.time} &bull; {e.dst ?? "—"}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${e.label.toUpperCase() !== "BENIGN" ? "bg-[#FDF2F0] text-[#DE5B49]" : "bg-[#EBF7EE] text-[#288D49]"}`}>
                          {e.label}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-stone-50 rounded-lg text-stone-500 text-center">No events observed for this host yet.</div>
                )}
              </div>
            </>
          )}

          {/* TAB 2: STRIX ADVERSARIAL ATTACK & AI PATCH DEFENSE */}
          {tab === "strix-defense" && (
            <div className="space-y-4">
              {/* Endpoint Context Card */}
              <div className="bg-[#FAF8F5] border border-[#EAE6DF] rounded-xl p-3.5 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#1C232B] flex items-center gap-1.5">
                    <Zap className="w-4 h-4 text-[#DE5B49]" />
                    Strix Penetration Lab &bull; Node Attack &amp; Defense
                  </span>
                  <span className="text-[9px] font-mono font-bold bg-[#FAF0ED] text-[#C54737] border border-[#F4D0C9] px-2 py-0.5 rounded-full">
                    SANDBOX: 127.0.0.1:8081
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-[#EDE6DC]">
                  <div>
                    <span className="text-[#7A8696] block text-[10px]">TARGET NODE</span>
                    <span className="font-mono font-bold text-[#1C232B]">{node.id}</span>
                  </div>
                  <div>
                    <span className="text-[#7A8696] block text-[10px]">CURRENT MODEL RISK</span>
                    <span className={`font-mono font-bold ${isDefended ? "text-[#1E7A43]" : "text-[#DE5B49]"}`}>
                      {isDefended ? "0.1% (MINIMAL)" : `${node.threatScore}% (CRITICAL)`}
                    </span>
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-bold uppercase text-[#8C96A3] mb-1 block">
                    Penetration Attack Vector
                  </label>
                  <select
                    value={vectorId}
                    onChange={(e) => {
                      setVectorId(e.target.value);
                      setPatchData(null);
                      setPatchSuccess(null);
                    }}
                    disabled={probeRunning}
                    className="w-full text-xs bg-white border border-[#DDD6CC] rounded-lg px-2.5 py-1.5 text-[#1C232B] font-medium focus:outline-none focus:border-[#DE5B49]"
                  >
                    <option value="ssh_bruteforce">SSH Credential Brute Force (CWE-307 / Port 22)</option>
                    <option value="sqli_probe">SQL Injection Parameter Probe (CWE-89 / Port 8081)</option>
                    <option value="smb_lateral">SMB Lateral Share Enumeration (CWE-285 / Port 445)</option>
                    <option value="c2_beacon">Egress C2 Beaconing Channel (CWE-200 / Port 8080)</option>
                  </select>
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={handleLaunchStrixProbe}
                    disabled={probeRunning}
                    className="flex-1 py-2 bg-[#DE5B49] hover:bg-[#C94838] disabled:opacity-50 text-white text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 shadow-sm transition-all cursor-pointer"
                  >
                    {probeRunning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                    {probeRunning ? `Probing in Sandbox (Step ${probeStep}/10)...` : "Attack with Strix in Sandbox"}
                  </button>

                  <button
                    onClick={handleSuggestPatch}
                    disabled={patchLoading || probeRunning}
                    className="py-2 px-3 bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#333E4D] text-xs font-bold rounded-lg flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    {patchLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-[#1E7A43]" />}
                    <span>Suggest Patch</span>
                  </button>
                </div>
              </div>

              {/* Probe Live Progress Feedback */}
              {probeRunning && (
                <div className="bg-[#FAF0ED] border border-[#F4D0C9] rounded-xl p-3 space-y-2 animate-pulse">
                  <div className="flex justify-between items-center text-xs font-bold text-[#DE5B49]">
                    <span>Strix Adversarial Probe in Progress...</span>
                    <span>Step {probeStep} / 10</span>
                  </div>
                  <div className="w-full bg-[#EAE2D8] h-1.5 rounded-full overflow-hidden">
                    <div className="bg-[#DE5B49] h-full transition-all duration-300" style={{ width: `${(probeStep / 10) * 100}%` }} />
                  </div>
                  <div className="text-[10px] text-[#7A8696] font-mono">
                    Ingesting simulated protocol probe flows &bull; best.pt risk: {probeRisk ? `${probeRisk.toFixed(1)}%` : "elevating..."}
                  </div>
                </div>
              )}

              {/* Verified Finding Card */}
              {probeSession?.findings?.length > 0 && (
                <div className="bg-[#FAF0ED] border border-[#F4D0C9] rounded-xl p-3.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#B33A2B] flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Vulnerability Confirmed by Strix Probe
                    </span>
                    <span className="text-[9px] font-mono font-bold bg-[#DE5B49] text-white px-2 py-0.5 rounded-full">
                      CVSS {probeSession.findings[0].cvss}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#556171] leading-relaxed">
                    {probeSession.findings[0].evidence}
                  </p>
                  <div className="text-[10px] font-mono text-[#7A8696]">
                    {probeSession.findings[0].cwe} &bull; {probeSession.findings[0].cve}
                  </div>
                </div>
              )}

              {/* AI Generated Patch Card */}
              {patchData && (
                <div className="bg-white border border-[#DDD6CC] rounded-xl p-3.5 space-y-3 shadow-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Code className="w-4 h-4 text-[#1E7A43]" />
                      <div>
                        <div className="text-xs font-bold text-[#1C232B]">{patchData.title}</div>
                        <div className="text-[10px] text-[#7A8696] font-mono">{patchData.target_file}</div>
                      </div>
                    </div>
                    <span className="text-[9px] font-mono font-bold bg-[#EBF7EE] text-[#1E7B3E] border border-[#C3E8CA] px-2 py-0.5 rounded-full">
                      {patchData.engine?.includes("ollama") ? "OLLAMA LLM" : "DEVSECOPS AI"}
                    </span>
                  </div>

                  {/* Unified Diff View */}
                  <div className="bg-[#1C232B] text-emerald-400 p-2.5 rounded-lg text-[10px] font-mono overflow-x-auto max-h-[160px] leading-relaxed">
                    <pre>{patchData.patch_diff}</pre>
                  </div>

                  <p className="text-[11px] text-[#556171] leading-relaxed">
                    {patchData.explanation}
                  </p>

                  {/* 1-Click Patch Application Button */}
                  <button
                    onClick={handleApplyPatch}
                    disabled={patchApplying || patchData.applied || isDefended}
                    className={`w-full py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-sm ${
                      patchData.applied || isDefended
                        ? "bg-[#EBF7EE] text-[#1E7B3E] border border-[#C3E8CA]"
                        : "bg-[#1E7A43] hover:bg-[#166534] text-white"
                    }`}
                  >
                    {patchApplying ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : patchData.applied || isDefended ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <ShieldCheck className="w-4 h-4" />
                    )}
                    <span>
                      {patchApplying
                        ? "Deploying AI Patch &amp; Verifying..."
                        : patchData.applied || isDefended
                        ? "AI Patch Deployed &bull; Host Defended"
                        : "Deploy 1-Click Patch &amp; Defend Node"}
                    </span>
                  </button>
                </div>
              )}

              {/* Patch Success Toast */}
              {patchSuccess && (
                <div className="bg-[#EBF7EE] border border-[#C3E8CA] text-[#1E7B3E] p-3 rounded-xl text-xs font-medium flex items-center gap-2">
                  <Check className="w-4 h-4 shrink-0" />
                  <span>{patchSuccess}</span>
                </div>
              )}

              {/* Jump to Parallel Futures option */}
              <div className="pt-2 border-t border-[#EDE6DC]">
                <button
                  onClick={() => onTakeToParallelFutures?.(node)}
                  className="w-full py-2 px-3 bg-[#FAF8F5] hover:bg-[#F4ECE2] text-[#4F5968] border border-[#DDD6CC] rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <GitBranch className="w-3.5 h-3.5 text-[#E58B44]" />
                  <span>Compare in Parallel Futures Simulation</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: CONTAINMENT & PARALLEL FUTURES */}
          {tab === "containment" && (
            <div className="space-y-3">
              <div className="bg-[#FAF6F0] p-3.5 rounded-xl border border-[#E9E1D5]">
                <h4 className="font-bold text-xs text-[#1F2731] flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-[#DE5B49]" />
                  <span>Counterfactual Containment Simulation</span>
                </h4>
                <p className="text-[#556272] text-[11px] mt-1 leading-relaxed">
                  Clones the current graph window, removes this host, and rolls the trained world model forward.
                  The baseline and intervened futures are compared with the same model — no live network change is made.
                </p>
                <div className="grid grid-cols-2 gap-2 mt-3">
                  <button
                    onClick={simulate}
                    disabled={working}
                    className="py-2 px-3 rounded-lg text-xs font-bold transition-all bg-[#DE5B49] hover:bg-[#C94838] text-white shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {working ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    {working ? "Simulating…" : "Simulate Isolation"}
                  </button>

                  <button
                    onClick={() => onTakeToParallelFutures?.(node)}
                    className="py-2 px-3 rounded-lg text-xs font-bold transition-all bg-[#FAF6F2] hover:bg-[#F4ECE2] text-[#4F5968] border border-[#DDD6CC] flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <GitBranch className="w-3.5 h-3.5 text-[#E58B44]" />
                    <span>Open in Futures</span>
                  </button>
                </div>
              </div>

              {cf && (
                <div className="border border-[#EDE7DE] rounded-xl p-3.5 bg-white space-y-2">
                  <div className="flex justify-between py-1 border-b border-[#F5F2EB]">
                    <span className="text-[#7A8696]">Baseline future risk</span>
                    <span className="font-mono font-bold text-[#29323E]">{(cf.baseline.risk * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#F5F2EB]">
                    <span className="text-[#7A8696]">Risk if isolated</span>
                    <span className="font-mono font-bold text-[#29323E]">{risk ? `${(risk.future_risk * 100).toFixed(1)}%` : "—"}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#7A8696]">Predicted risk reduction</span>
                    <span className="font-mono font-bold text-[#2EAA58]">{risk ? `−${(risk.risk_reduction * 100).toFixed(1)}%` : "—"}</span>
                  </div>
                  <div className="text-[10px] text-[#8C96A3] leading-relaxed pt-1">{cf.disclaimer}</div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: EXPLAIN */}
          {tab === "explain" && (
            <div className="space-y-3">
              <button
                onClick={() => onRunExplain(node.index, node.id)}
                disabled={explainBusy}
                className="w-full py-2 px-3 rounded-lg text-xs font-bold bg-[#1C2229] hover:bg-[#2B3B4C] text-white flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {explainBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                {explainBusy ? "Computing gradients…" : "Explain Forecast for This Host"}
              </button>
              {attributions ? (
                <div className="space-y-1.5">
                  {attributions.map((a) => (
                    <div key={a.feature} className="flex items-center gap-2">
                      <span className="w-40 truncate text-[#2B3542] font-medium">{a.feature.replace(/_/g, " ")}</span>
                      <div className="flex-1 h-2 bg-[#EFECE5] rounded-full overflow-hidden">
                        <div className="h-full bg-[#4B68B8] rounded-full" style={{ width: `${Math.max(4, (a.attribution / attrMax) * 100)}%` }} />
                      </div>
                      <span className="font-mono text-[10px] text-[#7A8696] w-12 text-right">{a.attribution.toFixed(4)}</span>
                    </div>
                  ))}
                  <div className="text-[10px] text-[#8C96A3] pt-1 flex items-center gap-1.5">
                    <Network className="w-3 h-3" /> Gradient × input attribution from the trained CYBERMIND model (not SHAP).
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-stone-50 rounded-lg text-stone-500 text-center">
                  Run the explainer to see which features drove the current forecast.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Drawer Footer */}
      <div className="p-4 border-t border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
        <span className="text-[11px] font-mono text-[#768292]">host #{node.index} &bull; {node.id}</span>
        <button
          onClick={onClose}
          className="px-4 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 rounded-lg text-xs font-bold text-[#353F4C] cursor-pointer"
        >
          Close
        </button>
      </div>
    </div>
  );
};
