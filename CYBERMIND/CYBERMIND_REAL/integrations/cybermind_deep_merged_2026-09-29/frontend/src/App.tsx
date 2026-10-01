import React, { useEffect, useMemo, useState } from "react";
import { X, Database, Zap, RotateCcw, Loader2, AlertTriangle, Upload } from "lucide-react";
import { Header } from "./components/Header";
import { Sidebar, type SidebarTab } from "./components/Sidebar";
import { RiskCard, AttackStageCard, PredictedStageCard, ProgressionCard } from "./components/MetricCards";
import { NetworkGraph } from "./components/NetworkGraph";
import { LiveEventFeed, RecentEventsTable } from "./components/EventPanels";
import { AttackTimeline } from "./components/AttackTimeline";
import { ModelInsightsCard, DefenceCard, SystemHealthCard } from "./components/InsightsAndHealth";
import { ScenarioLabCard, ScenarioLabModal } from "./components/ScenarioPanels";
import { NodeDetailDrawer } from "./components/NodeDetailDrawer";
import {
  LiveMonitorView, ThreatForecastView, AttackGraphView, ReplayView,
  ScenarioLabView, ReportsView, KnowledgeBaseView, SettingsView,
} from "./components/OtherViews";
import { ParallelForecastView } from "./components/ParallelForecast";
import { AttackLabView } from "./components/AttackLabView";
import { FlaggedFlowsView } from "./components/FlaggedFlowsView";
import { UploadModal } from "./components/UploadModal";
import { BenchmarkModal } from "./components/BenchmarkModal";
import { FloatingAnalystChat } from "./components/FloatingAnalystChat";
import { ClosedLoopHUD } from "./components/ClosedLoopHUD";
import { ValidationPanel } from "./components/StrixValidation";
import { useLiveStore } from "./lib/live";
import { api as cyApi } from "./lib/api";
import { toMilestones, type UINode, type UIEvent } from "./lib/adapters";
import type { Counterfactual } from "./lib/api";

/* ------------------------------ Command Palette --------------------------- */
const CommandPalette: React.FC<{
  isOpen: boolean; onClose: () => void; nodes: UINode[]; events: UIEvent[];
  onSelectNode: (n: UINode) => void; onSelectEvent: (e: UIEvent) => void;
}> = ({ isOpen, onClose, nodes, events, onSelectNode, onSelectEvent }) => {
  const [q, setQ] = useState("");
  useEffect(() => { if (isOpen) setQ(""); }, [isOpen]);
  if (!isOpen) return null;
  const hosts = nodes.filter((n) => n.id.toLowerCase().includes(q.toLowerCase())).slice(0, 6);
  const evs = events.filter((e) => `${e.source} ${e.destination ?? ""} ${e.label}`.toLowerCase().includes(q.toLowerCase())).slice(0, 8);
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-28 p-4 bg-black/40" onClick={onClose}>
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search hosts, events…"
          className="w-full px-4 py-3.5 text-sm border-b border-[#EDE6DC] focus:outline-none" />
        <div className="max-h-80 overflow-y-auto p-2 text-xs">
          {hosts.length > 0 && <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[#8C96A3]">Hosts</div>}
          {hosts.map((n) => (
            <button key={n.id} onClick={() => { onSelectNode(n); onClose(); }}
              className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#FAF8F5] flex justify-between">
              <span className="font-mono font-semibold text-[#1C232B]">{n.id}</span>
              <span className="text-[#7A8696]">risk {n.threatScore}</span>
            </button>
          ))}
          {evs.length > 0 && <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[#8C96A3]">Events</div>}
          {evs.map((e) => (
            <button key={e.id} onClick={() => { onSelectEvent(e); onClose(); }}
              className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#FAF8F5] flex justify-between">
              <span className="font-mono text-[#424D5B]">{e.time} · {e.source} → {e.destination}</span>
              <span className={e.severity === "High" ? "text-[#DE5B49] font-bold" : "text-[#7A8696]"}>{e.label}</span>
            </button>
          ))}
          {!hosts.length && !evs.length && <div className="px-3 py-6 text-center text-[#8C96A3]">No matches.</div>}
        </div>
      </div>
    </div>
  );
};

/* ------------------------------ Event Modal ------------------------------- */
const EventModal: React.FC<{ event: UIEvent | null; onClose: () => void }> = ({ event, onClose }) => {
  if (!event) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <h3 className="font-bold text-sm text-[#1C232B]">Event Detail</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#EFEAE2] text-[#8692A2]" aria-label="Close"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-2.5 text-xs">
          {[
            ["Time", event.time], ["Source", event.source], ["Destination", event.destination ?? "—"],
            ["Label", event.label], ["Protocol", event.protocol ?? "—"], ["Severity", event.severity],
            ["Scenario", event.scenario_id ?? "—"], ["Stream", event.source_stream ?? "—"],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-[#F5F2EB] pb-1.5">
              <span className="text-[#7A8696]">{k}</span><span className="font-mono font-semibold text-[#29323E]">{v}</span>
            </div>
          ))}
          <p className="text-[10px] text-[#8C96A3] pt-1">
            Provenance preserved from ingestion. Severity derives from the dataset-label→stage research mapping, not ATT&CK ground truth.
          </p>
        </div>
      </div>
    </div>
  );
};

/* ---------------------------------- App ----------------------------------- */
export function App() {
  const store = useLiveStore();
  const [tab, setTab] = useState<SidebarTab>("command-center");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [scenarioModalOpen, setScenarioModalOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<UINode | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<UIEvent | null>(null);
  const [defendedNodeIds, setDefendedNodeIds] = useState<Set<string>>(new Set());
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [benchmarkModalOpen, setBenchmarkModalOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaletteOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const milestones = useMemo(
    () => toMilestones(store.forecast?.steps ?? [], store.state?.dominant_stage),
    [store.forecast, store.state]
  );

  const handleIsolate = async (node: UINode): Promise<Counterfactual | null> => {
    try { return await cyApi.counterfactualHost(node.id, "Isolate Host"); }
    catch { return null; }
  };

  const handleTakeToParallelFutures = (nodeOrHost: UINode | string) => {
    const hostId = typeof nodeOrHost === "string" ? nodeOrHost : nodeOrHost.id;
    const node = typeof nodeOrHost === "string" ? store.nodes.find((n) => n.id === nodeOrHost) : nodeOrHost;
    if (node) setSelectedNode(node);
    setTab("parallel-forecast");
    void cyApi.counterfactualHost(hostId, "Isolate Host");
  };

  const handleAttackWithStrix = (nodeOrHost: UINode | string) => {
    const node = typeof nodeOrHost === "string" ? store.nodes.find((n) => n.id === nodeOrHost) : nodeOrHost;
    if (node) setSelectedNode(node);
    setTab("attack-lab");
  };

  const handleSuggestPatch = (nodeOrHost: UINode | string) => {
    const node = typeof nodeOrHost === "string" ? store.nodes.find((n) => n.id === nodeOrHost) : nodeOrHost;
    if (node) setSelectedNode(node);
  };

  const handleDefendNode = async (node: UINode, patchId: string): Promise<boolean> => {
    setDefendedNodeIds((prev) => new Set([...prev, node.id]));
    if (selectedNode && selectedNode.id === node.id) {
      setSelectedNode({ ...selectedNode, threatScore: 5, status: "normal" });
    }
    await store.refresh();
    return true;
  };

  const modelAvailable = !!store.health?.model?.available;
  const scenarioRunning = !!store.health?.scenario?.running;
  const currentScenarioId = store.health?.scenario?.scenario_id ?? null;

  return (
    <div className="min-h-screen bg-[#F7F5F0] text-[#1C2229] flex flex-col font-sans selection:bg-[#DE5B49]/20 selection:text-[#DE5B49]">
      <Header health={store.health} ws={store.ws} provenance={store.provenance} onOpenCommandPalette={() => setPaletteOpen(true)} />

      <div className="flex-1 flex h-[calc(100vh-61px)] min-w-0 overflow-hidden">
        <Sidebar
          currentTab={tab} onTabChange={setTab} health={store.health}
          scenarios={store.scenarioList} activeScenarioId={currentScenarioId}
          scenarioRunning={scenarioRunning}
          onStartScenario={(id) => { void store.startScenario(id); }}
          onStopScenario={() => { void store.stopScenario(); }}
          onResetScenario={() => { void store.resetScenario(); }}
          onLoadTestCase={(id) => { void store.loadTestCase(id); }}
          activeTestCaseId={store.activeTestCase}
          testCaseBusy={store.busy.testCase}
        />

        <main className="flex-1 min-w-0 p-3 sm:p-6 max-w-[1600px] mx-auto w-full overflow-y-auto overflow-x-hidden space-y-5">
          {store.error && (
            <div className="bg-[#FDF2F0] border border-[#F9DCD7] text-[#B33A2B] px-4 py-2.5 rounded-xl text-xs font-semibold flex flex-wrap items-center justify-between gap-2">
              <span className="min-w-0 break-words">{store.error}</span>
              <div className="flex items-center gap-3">
                {store.error.includes("service is unavailable") && (
                  <button onClick={() => void store.refresh(true)} className="underline underline-offset-2 hover:text-[#8E281D]">
                    Retry connection
                  </button>
                )}
                <button onClick={store.dismissError} className="hover:underline">dismiss</button>
              </div>
            </div>
          )}

          {tab === "command-center" && (
            <>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-1 pb-1">
                <div>
                  <h1 className="font-editorial text-[25px] sm:text-[32px] font-normal tracking-tight text-[#171F27] leading-tight">
                    Observe. Predict. Prevent.
                  </h1>
                  <p className="text-xs text-[#707C8C] mt-1 font-medium">
                    AI-driven cyber defence with temporal understanding of evolving system behavior.
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 flex-wrap">
                  <button
                    onClick={() => { store.pausePolling(true); setUploadModalOpen(true); }}
                    className="py-2 px-3.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-xs bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#333E4D]"
                  >
                    <Upload className="w-3.5 h-3.5 text-[#556171]" />
                    <span>Upload PCAP / CSV</span>
                  </button>
                  <button
                    onClick={() => setBenchmarkModalOpen(true)}
                    className="py-2 px-3.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-xs bg-[#EEF2FB] hover:bg-[#DDE4F5] border border-[#C9D4EE] text-[#4B68B8]"
                  >
                    <span>Benchmark (Track A)</span>
                  </button>
                  <div className="hidden sm:block text-right">
                    <div className="font-editorial italic text-xs text-[#4F5968]">"The best defence is a step ahead."</div>
                    <div className="text-[10px] uppercase tracking-[0.2em] text-[#8C97A5] font-semibold mt-0.5">— CYBERMIND</div>
                  </div>
                </div>
              </div>

              {/* Closed-Loop HUD (Slide 12: Ingest → Forecast → Simulate → Validate) */}
              <ClosedLoopHUD />

              {/* Real Test Case Action Bar */}
              <div className="bg-white border border-[#EAE6DF] rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#FAF6F2] border border-[#EDE4D8] flex items-center justify-center text-[#DE5B49] shrink-0">
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-[#1C232B] uppercase tracking-wide">Test Case Evaluation</span>
                      <span className="bg-[#EBF7EE] border border-[#C3E8CA] text-[#1E7B3E] text-[10px] font-bold px-2 py-0.5 rounded-full">
                        REAL FLOW SAMPLES · OFFLINE
                      </span>
                      {store.activeTestCase && (
                        <span className="bg-[#EEF2FB] border border-[#C9D4EE] text-[#4B68B8] text-[10px] font-mono font-bold px-2 py-0.5 rounded-full">
                          Loaded: {store.testCases.find((t) => t.id === store.activeTestCase)?.name ?? store.activeTestCase}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#707C8C] mt-0.5">
                      Ingest provenance-recorded CSE-CIC-IDS2018 flow samples into the same temporal model path as uploaded captures.
                    </p>
                  </div>
                </div>

                <div className="flex min-w-0 items-center gap-2 flex-wrap">
                  <button
                    onClick={() => void store.loadTestCase("botnet_ares")}
                    disabled={store.busy.testCase}
                    className={`py-2 px-3.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-xs ${
                      store.activeTestCase === "botnet_ares"
                        ? "bg-[#DE5B49] text-white shadow-sm ring-2 ring-[#DE5B49]/30"
                        : "bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#333E4D]"
                    }`}
                  >
                    {store.busy.testCase && store.activeTestCase === "botnet_ares" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5 text-[#DE5B49]" />
                    )}
                    <span>Load Botnet Ares Sample</span>
                  </button>

                  <button
                    onClick={() => void store.loadTestCase("ssh_bruteforce")}
                    disabled={store.busy.testCase}
                    className={`py-2 px-3.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all shadow-xs ${
                      store.activeTestCase === "ssh_bruteforce"
                        ? "bg-[#DE5B49] text-white shadow-sm ring-2 ring-[#DE5B49]/30"
                        : "bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#333E4D]"
                    }`}
                  >
                    {store.busy.testCase && store.activeTestCase === "ssh_bruteforce" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5 text-[#E58B44]" />
                    )}
                    <span>Load SSH Brute Force Sample</span>
                  </button>

                  {store.activeTestCase && (
                    <button
                      onClick={() => void store.resetScenario()}
                      title="Reset test case and clear state"
                      className="p-2 bg-[#FAF8F5] hover:bg-[#FBEDEA] border border-[#DDD6CC] hover:border-[#DE5B49]/40 text-[#556171] hover:text-[#DE5B49] rounded-xl text-xs font-semibold transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Attack Labs & Strix Banner */}
              <div className="bg-white border border-[#EAE6DF] rounded-2xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#FAF0ED] border border-[#F4D0C9] flex items-center justify-center text-[#DE5B49] shrink-0">
                    <Zap className="w-5 h-5 text-[#DE5B49]" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-[#1C232B] uppercase tracking-wide">
                        Attack Labs &bull; Strix Adversarial Sandbox
                      </span>
                      <span className="bg-[#FAF0ED] border border-[#F4D0C9] text-[#C54737] text-[10px] font-bold px-2 py-0.5 rounded-full font-mono">
                        NON-EXPLOITING PROBES
                      </span>
                      <span className="bg-[#EBF7EE] border border-[#C3E8CA] text-[#1E7B3E] text-[10px] font-bold px-2 py-0.5 rounded-full font-mono">
                        OPTIONAL SCAN
                      </span>
                      <span className="bg-[#FAF8F5] border border-[#E8E2D7] text-[#707C8C] text-[10px] font-mono px-2 py-0.5 rounded-full">
                        Target: 127.0.0.1:8081
                      </span>
                    </div>
                    <p className="text-[11px] text-[#707C8C] mt-0.5">
                      Controlled Strix scans require a configured sandbox and local provider. The built-in offline check records sandbox responses beside the <code className="text-[#DE5B49] font-mono">best.pt</code> forecast.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setTab("attack-lab")}
                    className="py-2 px-4 rounded-xl bg-[#DE5B49] hover:bg-[#C54737] text-white font-bold text-xs tracking-wider uppercase transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
                  >
                    <Zap className="w-3.5 h-3.5 fill-white" />
                    <span>Open Attack Labs</span>
                  </button>
                </div>
              </div>

              {!modelAvailable && (
                <div className="bg-[#FDF3E4] border border-[#F2D9AF] text-[#8C5424] px-4 py-3 rounded-xl text-xs font-semibold flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Model not loaded — check <span className="font-mono">models/best.pt</span> and restart the backend to enable inference. The UI tracks live telemetry meanwhile.</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                <RiskCard forecast={store.forecast} ready={!!store.state?.ready} />
                <AttackStageCard forecast={store.forecast} dominantStage={store.state?.dominant_stage ?? 0} />
                <PredictedStageCard forecast={store.forecast} />
                <ProgressionCard forecast={store.forecast} />
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
                <div className="xl:col-span-8 min-w-0 space-y-5">
                  <NetworkGraph
                    nodes={store.nodes} links={store.links}
                    onSelectNode={setSelectedNode} selectedNodeId={selectedNode?.id}
                    windowLabel={store.state?.window_start ? `window @ ${new Date(store.state.window_start * 1000).toLocaleTimeString([], { hour12: false })}` : undefined}
                    onTakeToParallelFutures={handleTakeToParallelFutures}
                    onAttackWithStrix={handleAttackWithStrix}
                    onSuggestPatch={handleSuggestPatch}
                    defendedNodeIds={defendedNodeIds}
                  />
                  {milestones.length > 1 && <AttackTimeline milestones={milestones} onOpenFullTimeline={() => setTab("threat-forecast")} />}
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                    <div className="md:col-span-5 min-h-[270px]">
                      <RecentEventsTable events={store.events} onSelectEvent={setSelectedEvent} onViewAll={() => setTab("live-monitor")} />
                    </div>
                    <div className="md:col-span-4 min-h-[270px]">
                      <ScenarioLabCard
                        health={store.health} scenarios={store.scenarioList}
                        isRunning={scenarioRunning} currentId={currentScenarioId}
                        onToggleRunning={() => (scenarioRunning ? store.stopScenario() : currentScenarioId && store.startScenario(currentScenarioId))}
                        onReset={() => { void store.resetScenario(); }}
                        onPick={(id) => { void store.startScenario(id); }}
                      />
                    </div>
                    <div className="md:col-span-3 min-h-[270px]">
                      <SystemHealthCard health={store.health} wsUp={store.ws === "online"} />
                    </div>
                  </div>
                </div>

                <div className="xl:col-span-4 min-w-0 space-y-5">
                  <div className="h-[430px]">
                    <LiveEventFeed events={store.events} onSelectEvent={setSelectedEvent} onViewAll={() => setTab("live-monitor")} />
                  </div>
                  <DefenceCard
                    cf={store.counterfactual} gravity={store.gravity}
                    busyCf={store.busy.cf} busyGravity={store.busy.gravity}
                    onRunCf={() => { void store.runCounterfactual(); }}
                    onRunGravity={() => { void store.runGravity(); }}
                    modelAvailable={modelAvailable}
                  />
                  <div className="min-h-[300px]">
                    <ModelInsightsCard
                      attributions={store.attributions} attributionHost={store.attributionHost}
                      busy={store.busy.explain} hasState={!!store.state?.ready}
                      nodeCount={store.nodes.length}
                      onRunExplain={() => {
                        const host = store.nodes.find((n) => n.status !== "normal") ?? store.nodes[0];
                        if (host) void store.runExplain(host.index, host.id);
                      }}
                    />
                  </div>
                </div>
              </div>
              <ValidationPanel store={store} />
            </>
          )}

          {tab === "attack-lab" && <AttackLabView store={store} onBack={() => setTab("command-center")} />}
          {tab === "live-monitor" && <LiveMonitorView store={store} onBack={() => setTab("command-center")} />}
          {tab === "threat-forecast" && <ThreatForecastView store={store} onBack={() => setTab("command-center")} />}
          {tab === "parallel-forecast" && <ParallelForecastView store={store} onBack={() => setTab("command-center")} />}
          {tab === "attack-graph" && (
            <AttackGraphView
              store={store}
              onBack={() => setTab("command-center")}
              onSelectHost={(hostId) => {
                const n = store.nodes.find((x) => x.id === hostId);
                if (n) setSelectedNode(n);
              }}
              onTakeToParallelFutures={handleTakeToParallelFutures}
              onAttackWithStrix={handleAttackWithStrix}
              onSuggestPatch={handleSuggestPatch}
            />
          )}
          {tab === "scenario-lab" && <ScenarioLabView store={store} onBack={() => setTab("command-center")} />}
          {tab === "replay-analysis" && <ReplayView onBack={() => setTab("command-center")} />}
          {tab === "reports" && <ReportsView store={store} onBack={() => setTab("command-center")} />}
          {tab === "knowledge-base" && <KnowledgeBaseView onBack={() => setTab("command-center")} />}
          {tab === "settings" && <SettingsView store={store} onBack={() => setTab("command-center")} />}
          {tab === "flagged-flows" && <FlaggedFlowsView onBack={() => setTab("command-center")} />}
          {tab === "benchmark" && <BenchmarkModal isOpen={true} onClose={() => setTab("command-center")} />}
        </main>
      </div>

      <CommandPalette
        isOpen={paletteOpen} onClose={() => setPaletteOpen(false)}
        nodes={store.nodes} events={store.events}
        onSelectNode={setSelectedNode} onSelectEvent={setSelectedEvent}
      />
      <EventModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
      <NodeDetailDrawer
        node={selectedNode} onClose={() => setSelectedNode(null)}
        onIsolateNode={handleIsolate} gravity={store.gravity}
        eventsForHost={selectedNode ? store.events.filter((e) => e.source === selectedNode.id || e.destination === selectedNode.id).map((e) => ({ time: e.time, label: e.label, dst: e.destination, port: undefined })) : []}
        onRunExplain={(idx, id) => { void store.runExplain(idx, id); }}
        explainBusy={store.busy.explain}
        attributions={store.attributionHost === selectedNode?.id ? store.attributions : null}
        onTakeToParallelFutures={handleTakeToParallelFutures}
        onAttackWithStrix={handleAttackWithStrix}
        onDefendNode={handleDefendNode}
        isDefended={selectedNode ? defendedNodeIds.has(selectedNode.id) : false}
      />
      <ScenarioLabModal
        isOpen={scenarioModalOpen} onClose={() => setScenarioModalOpen(false)}
        scenarios={store.scenarioList} isRunning={scenarioRunning} currentId={currentScenarioId}
        onStart={(id, interval) => { void store.startScenario(id, interval); }}
        onStop={() => { void store.stopScenario(); }}
        onReset={() => { void store.resetScenario(); }}
      />
      <UploadModal isOpen={uploadModalOpen} onClose={() => { store.pausePolling(false); setUploadModalOpen(false); void store.refresh(true); }} onSuccess={() => {}} onViewFlaggedFlows={() => setTab("flagged-flows")} />
      <BenchmarkModal isOpen={benchmarkModalOpen} onClose={() => setBenchmarkModalOpen(false)} />
      <FloatingAnalystChat />
    </div>
  );
}

export default App;
