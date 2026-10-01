/**
 * Live store: one subscription powering the whole dashboard.
 * Sources: /api/health, /api/state/current, /api/forecast, /api/timeline + /ws/live.
 */
import { useEffect, useState, useCallback, useRef } from "react";
import {
  api, connectLive, forecastOf, type LiveMessage,
  type HealthResponse, type StateResponse, type Forecast,
  type ScenarioInfo, type AttackGravity, type Counterfactual, type Attribution,
  type StrixStatus, type StrixRun, type ValidationComparison, type DefenceRecommendation,
  type TestCaseInfo, type TestCaseLoadResult,
} from "./api";
import { toUINodes, toUILinks, toUIEvents, type UINode, type UILink, type UIEvent } from "./adapters";

export type WsStatus = "connecting" | "online" | "offline";
const OFFLINE_ERROR = "Local CYBERMIND service is unavailable. Relaunch the app and retry the connection.";

export interface LiveStore {
  health: HealthResponse | null;
  state: StateResponse | null;
  forecast: Forecast | null;
  events: UIEvent[];
  nodes: UINode[];
  links: UILink[];
  gravity: AttackGravity | null;
  counterfactual: Counterfactual | null;
  attributions: Attribution[] | null;
  attributionHost: string | null;
  scenarioList: ScenarioInfo[];
  testCases: TestCaseInfo[];
  activeTestCase: string | null;
  strixStatus: StrixStatus | null;
  strixRuns: StrixRun[];
  validations: ValidationComparison[];
  recommendation: DefenceRecommendation | null;
  lastValidation: ValidationComparison | null;
  provenance: string;
  ws: WsStatus;
  lastUpdate: number;
  busy: { gravity: boolean; cf: boolean; explain: boolean; validate: boolean; defence: boolean; testCase: boolean };
  error: string | null;
  refresh: (force?: boolean) => Promise<void>;
  pausePolling: (paused: boolean) => void;
  startScenario: (id: string, interval?: number) => Promise<void>;
  stopScenario: () => Promise<void>;
  resetScenario: () => Promise<void>;
  loadTestCase: (id: string, limit?: number) => Promise<TestCaseLoadResult | null>;
  runGravity: () => Promise<void>;
  runCounterfactual: () => Promise<void>;
  runExplain: (hostIndex: number, hostId: string) => Promise<void>;
  runValidation: (scenarioId: string, scanMode?: string) => Promise<ValidationComparison | null>;
  runDefence: () => Promise<void>;
  approveRecommendation: (id: string) => Promise<void>;
  rejectRecommendation: (id: string, reason?: string) => Promise<void>;
  dismissError: () => void;
}

export function useLiveStore(): LiveStore {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [state, setState] = useState<StateResponse | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [events, setEvents] = useState<UIEvent[]>([]);
  const [gravity, setGravity] = useState<AttackGravity | null>(null);
  const [counterfactual, setCounterfactual] = useState<Counterfactual | null>(null);
  const [attributions, setAttributions] = useState<Attribution[] | null>(null);
  const [attributionHost, setAttributionHost] = useState<string | null>(null);
  const [scenarioList, setScenarioList] = useState<ScenarioInfo[]>([]);
  const [testCases, setTestCases] = useState<TestCaseInfo[]>([]);
  const [activeTestCase, setActiveTestCase] = useState<string | null>(null);
  const [strixStatus, setStrixStatus] = useState<StrixStatus | null>(null);
  const [strixRuns, setStrixRuns] = useState<StrixRun[]>([]);
  const [validations, setValidations] = useState<ValidationComparison[]>([]);
  const [recommendation, setRecommendation] = useState<DefenceRecommendation | null>(null);
  const [lastValidation, setLastValidation] = useState<ValidationComparison | null>(null);
  const [ws, setWs] = useState<WsStatus>("connecting");
  const [lastUpdate, setLastUpdate] = useState(0);
  const [busy, setBusy] = useState({ gravity: false, cf: false, explain: false, validate: false, defence: false, testCase: false });
  const [error, setError] = useState<string | null>(null);
  const pausedRef = useRef(false);
  const refreshInFlightRef = useRef(false);
  const nextRefreshAtRef = useRef(0);
  const pausePolling = useCallback((paused: boolean) => { pausedRef.current = paused; }, []);

  const refresh = useCallback(async (force = false) => {
    if (refreshInFlightRef.current || (!force && (pausedRef.current || Date.now() < nextRefreshAtRef.current))) return;
    refreshInFlightRef.current = true;
    try {
      const [h, st, fc, tl] = await Promise.all([
        api.health(), api.state(), api.forecast().catch(() => null), api.timeline(60),
      ]);
      if (pausedRef.current && !force) return;
      setHealth(h);
      setState(st);
      if (fc) setForecast(fc);
      setEvents(toUIEvents(tl.events ?? []));
      setLastUpdate(Date.now());
      nextRefreshAtRef.current = 0;
      setError((current) => current === OFFLINE_ERROR ? null : current);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      if (message === OFFLINE_ERROR) {
        nextRefreshAtRef.current = Date.now() + 10000;
        setHealth(null);
        setWs("offline");
      }
      setError(message);
    } finally {
      refreshInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    api.scenarios().then((s) => setScenarioList(s.scenarios)).catch(() => undefined);
    api.testCases().then((t) => setTestCases(t.testcases)).catch(() => undefined);
    api.strixStatus().then(setStrixStatus).catch(() => undefined);
    api.validations().then((v) => setValidations(v.validations)).catch(() => undefined);
    const t = setInterval(() => { void refresh(); }, 3000);
    const validatorStatusTimer = setInterval(() => {
      api.strixStatus().then(setStrixStatus).catch(() => undefined);
    }, 15000);
    return () => { clearInterval(t); clearInterval(validatorStatusTimer); };
  }, [refresh]);

  useEffect(() => {
    const handle = (msg: LiveMessage) => {
      const fc = forecastOf(msg);
      if (fc?.steps?.length) {
        setForecast(fc);
        return;
      }
      if (msg.type === "strix.run_started") {
        const started = msg as LiveMessage & { type: "strix.run_started"; run_id: string; scenario_id: string; status: string };
        setStrixRuns((prev) => [
          { run_id: started.run_id, scenario_id: started.scenario_id, started_at: Date.now() / 1000, finished_at: null, status: started.status, target: "", mode: "", budget: null, artifacts_path: null, return_code: null, error: null } as StrixRun,
          ...prev.filter((r) => r.run_id !== started.run_id),
        ].slice(0, 50));
        return;
      }
      if (msg.type === "strix.run_completed") {
        const done = msg as LiveMessage & { type: "strix.run_completed"; run_id: string; status: string };
        setStrixRuns((prev) => prev.map((r) => (r.run_id === done.run_id ? { ...r, status: done.status, finished_at: Date.now() / 1000 } : r)));
        return;
      }
      if (msg.type === "validation.completed") {
        // Refresh the validation list from source of truth shortly after.
        setTimeout(() => { api.validations().then((v) => setValidations(v.validations)).catch(() => undefined); }, 400);
        return;
      }
      if (msg.type === "defence.recommendation") {
        setTimeout(() => { api.defencePending().catch(() => undefined); }, 300);
        return;
      }
      if (msg.type === "intervention") {
        const iv = msg as { type: "intervention"; recommended: Counterfactual["recommended"]; baseline: Counterfactual["baseline"] };
        // Merge, don't clobber: a full parallel-futures simulation (with all
        // intervention branches) must survive routine recommendation ticks.
        setCounterfactual((prev) => {
          if (prev && prev.interventions.length) {
            return { ...prev, baseline: iv.baseline, recommended: iv.recommended };
          }
          return {
            baseline: iv.baseline,
            interventions: [],
            recommended: iv.recommended,
            latency_ms: 0,
            disclaimer: "Counterfactual Risk Simulation: model-based risk comparison of simulated futures, not a causal effect.",
          };
        });
      }
    };
    return connectLive(handle, (up) => setWs(up ? "online" : "offline"));
  }, []);

  const startScenario = useCallback(async (id: string, interval = 1.5) => {
    try {
      setError(null);
      await api.startScenario(id, interval);
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, [refresh]);

  const stopScenario = useCallback(async () => {
    try { await api.stopScenario(); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, [refresh]);

  const resetScenario = useCallback(async () => {
    try {
      await api.resetScenario();
      setActiveTestCase(null);
      setGravity(null);
      setCounterfactual(null);
      setAttributions(null);
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, [refresh]);

  const loadTestCase = useCallback(async (id: string, limit = 1500) => {
    setBusy((b) => ({ ...b, testCase: true }));
    try {
      setError(null);
      const res = await api.loadTestCase(id, limit);
      setActiveTestCase(id);
      if (res.forecast) setForecast(res.forecast);
      await refresh();
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setBusy((b) => ({ ...b, testCase: false }));
    }
  }, [refresh]);

  const runGravity = useCallback(async () => {
    setBusy((b) => ({ ...b, gravity: true }));
    try { setGravity(await api.attackGravity()); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy((b) => ({ ...b, gravity: false })); }
  }, []);

  const runCounterfactual = useCallback(async () => {
    setBusy((b) => ({ ...b, cf: true }));
    try {
      setCounterfactual(await api.counterfactual());
      setLastUpdate(Date.now());
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy((b) => ({ ...b, cf: false })); }
  }, []);

  const runExplain = useCallback(async (hostIndex: number, hostId: string) => {
    setBusy((b) => ({ ...b, explain: true }));
    try {
      const res = await api.explain(hostIndex);
      setAttributions(res.attributions);
      setAttributionHost(res.host || hostId);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy((b) => ({ ...b, explain: false })); }
  }, []);

  const runValidation = useCallback(async (scenarioId: string, scanMode = "quick") => {
    setBusy((b) => ({ ...b, validate: true }));
    try {
      const res = await api.validateScenario(scenarioId, scanMode);
      const comp = res.comparison;
      setLastValidation(comp);
      setValidations((prev) => [comp, ...prev.filter((v) => v.validation_id !== comp.validation_id)]);
      api.strixRuns().then((r) => setStrixRuns(r.runs)).catch(() => undefined);
      return comp;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally { setBusy((b) => ({ ...b, validate: false })); }
  }, []);

  const runDefence = useCallback(async () => {
    setBusy((b) => ({ ...b, defence: true }));
    try { setRecommendation(await api.defenceRecommendation()); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy((b) => ({ ...b, defence: false })); }
  }, []);

  const approveRecommendation = useCallback(async (id: string) => {
    try { await api.defenceApprove(id); setRecommendation((r) => (r && r.recommendation_id === id ? { ...r, approval_required: false } : r)); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, []);

  const rejectRecommendation = useCallback(async (id: string, reason = "") => {
    try { await api.defenceReject(id, reason); setRecommendation(null); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, []);

  const dismissError = useCallback(() => setError(null), []);

  const nodes = toUINodes(state, gravity);
  const links = toUILinks(state);
  const isReplay = events.some((e) => e.source?.includes("replay"));
  const provenance = health?.scenario?.running || events.some((e) => e.source?.startsWith("scenario:"))
    ? "SYNTHETIC LAB"
    : activeTestCase ? "REAL FLOW SAMPLE"
    : isReplay ? "REPLAY"
    : events.some((e) => e.source?.startsWith("upload:")) ? "LOCAL CAPTURE"
    : (events.length > 0 || state?.ready) ? "LIVE" : "—";

  return {
    health, state, forecast, events, nodes, links, gravity, counterfactual,
    attributions, attributionHost, scenarioList, testCases, activeTestCase,
    strixStatus, strixRuns, validations, recommendation, lastValidation,
    provenance, ws, lastUpdate, busy, error, refresh, pausePolling,
    startScenario, stopScenario, resetScenario, loadTestCase,
    runGravity, runCounterfactual, runExplain, runValidation, runDefence,
    approveRecommendation, rejectRecommendation, dismissError,
  };
}
