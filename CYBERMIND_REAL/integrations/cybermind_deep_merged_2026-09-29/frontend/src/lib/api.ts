/**
 * CYBERMIND API client.
 * Every live dashboard value comes from these endpoints:
 * telemetry → state → forecast → recommendation → experiments.
 */

export interface ModelStatus {
  available: boolean;
  status: string;
  device: string;
  version: string;
  checkpoint: string;
  checkpoint_present: boolean;
  load_error: string | null;
  expected_path: string;
  parameters?: number;
}

export interface HealthResponse {
  status: string;
  model: ModelStatus;
  telemetry_events: number;
  state_windows: number;
  scenario: { running: boolean; scenario_id?: string; run_id?: string; tick?: number; mode: string };
  time: number;
}

export interface ForecastStep {
  step: number;
  risk: number;
  risk_pct: number;
  variance?: number;
  std?: number;
  lower_bound?: number;
  upper_bound?: number;
  lower_pct?: number;
  upper_pct?: number;
  stage_id: number;
  stage: string;
  stage_short: string;
  technique: string;
  technique_id: string;
  stage_probs: number[];
  confidence: number;
}

export interface Forecast {
  model_available: boolean;
  reason?: string;
  run_id?: string | null;
  model_version?: string;
  k?: number;
  timestamp?: number;
  observation_windows?: number;
  current?: ForecastStep;
  horizon?: { risk: number | null; stage: string | null; stage_id: number | null };
  steps: ForecastStep[];
  confidence: number | null;
  ood_flag: boolean;
  latent_summary?: number[];
  latency_ms?: number;
  disclaimer?: string;
}

export interface GraphNode {
  id: string;
  index: number;
  anomaly: number;
  activity: number;
}

export interface GraphEdge {
  src: string;
  dst: string;
  src_index: number;
  dst_index: number;
  bytes: number;
  packets: number;
  protocol: number;
  port: number;
  duration: number;
}

export interface StateResponse {
  timestamp?: number;
  window_start?: number;
  window_end?: number;
  event_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  labels: Record<string, number>;
  dominant_stage: number;
  label_counts: Record<string, number>;
  ready: boolean;
}

export interface TelemetryEvent {
  timestamp: number;
  src: string;
  dst: string;
  src_port?: number | null;
  dst_port?: number | null;
  protocol?: number | string | null;
  bytes_fwd?: number;
  bytes_bwd?: number;
  packets_fwd?: number;
  packets_bwd?: number;
  duration?: number;
  label: string;
  attack_stage?: number | null;
  technique_id?: string | null;
  scenario_id?: string | null;
  source?: string;
  provenance?: string | null;
}

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  duration_ticks: number;
}

export interface Intervention {
  action: string;
  action_label: string;
  host?: string | null;
  port?: number | null;
  future_risk: number;
  risk_delta: number;
  risk_reduction: number;
  band: string;
  trajectory: number[];
  stage?: string;
  stage_short?: string;
  stage_ids?: number[];
}

export interface Counterfactual {
  baseline: { risk: number; band: string; trajectory: number[]; stage?: string; stage_short?: string; stage_ids?: number[] };
  interventions: Intervention[];
  recommended: Intervention | null;
  latency_ms: number;
  disclaimer: string;
}

export interface GravityRow {
  host: string;
  index: number;
  baseline_risk: number;
  counterfactual_risk: number;
  attack_gravity: number;
}

export interface AttackGravity {
  baseline_risk: number;
  baseline_trajectory: number[];
  gravity: GravityRow[];
  critical_asset: GravityRow | null;
  disclaimer: string;
}

export interface Attribution {
  feature: string;
  attribution: number;
  share?: number;
}

export interface ExperimentRun {
  run_id: string;
  scenario_id: string | null;
  model_version: string | null;
  start_time: number;
  end_time: number | null;
  prediction_count: number;
  intervention_count: number;
  metrics: Record<string, unknown>;
}

export interface RunDetail {
  run_id: string;
  scenario_id: string | null;
  model_version: string | null;
  source: string | null;
  start_time: number;
  end_time: number | null;
  predictions: Array<Record<string, unknown>>;
  interventions: Array<Record<string, unknown>>;
}

export interface AnalystChatReply {
  answer: string;
  intent: string;
  source: string;
  scope: string;
  engine: string;
}

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, opts);
  } catch {
    throw new Error("Local CYBERMIND service is unavailable. Relaunch the app and retry the connection.");
  }
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      detail = body.detail || JSON.stringify(body);
    } catch { /* keep statusText */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

const post = <T>(url: string, body?: unknown) =>
  req<T>(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });

export const api = {
  askAnalyst: (question: string) => post<AnalystChatReply>("/api/chat", { question }),
  health: () => req<HealthResponse>("/api/health"),
  modelStatus: () => req<ModelStatus & Record<string, unknown>>("/api/model"),
  state: () => req<StateResponse>("/api/state/current"),
  forecast: () => req<Forecast>("/api/forecast"),
  timeline: (limit = 60) => req<{ events: TelemetryEvent[] }>(`/api/timeline?limit=${limit}`),
  scenarios: () => req<{ scenarios: ScenarioInfo[]; status: Record<string, unknown> }>("/api/scenarios"),
  startScenario: (scenario_id: string, interval = 1.5, speed = 1) =>
    post<{ run_id: string; status: string }>("/api/scenarios/start", { scenario_id, interval, speed }),
  stopScenario: () => post<Record<string, unknown>>("/api/scenarios/stop", { scenario_id: "current" }),
  resetScenario: () => post<Record<string, unknown>>("/api/scenarios/reset"),
  counterfactual: (k = 6) => post<Counterfactual>("/api/counterfactual/simulate", { action: "auto", k }),
  counterfactualHost: (host: string, action: string, k = 6) =>
    post<Counterfactual>("/api/counterfactual/simulate", { action, host, k }),
  attackGravity: (k = 6) => post<AttackGravity>("/api/counterfactual/attack-gravity", { k }),
  explain: (hostIndex: number) => post<{ host: string; attributions: Attribution[]; disclaimer: string }>(`/api/explain/${hostIndex}`),
  replayFiles: () => req<{ files: string[]; loaded: string | null; buffer: number; index: number }>("/api/replay/files"),
  loadReplay: (filename: string) => post<{ file: string; events: number }>("/api/replay/load", { filename }),
  seekReplay: (index: number) =>
    post<{ index: number; total: number; ready: boolean; forecast: Forecast | null }>("/api/replay/seek", { index }),
  testCases: () => req<{ testcases: TestCaseInfo[] }>("/api/testcases"),
  loadTestCase: (testcase_id: string, limit = 1500) =>
    post<TestCaseLoadResult>("/api/testcases/load", { testcase_id, limit, clear_previous: true }),
  experiments: (limit = 50) => req<{ runs: ExperimentRun[] }>(`/api/experiments?limit=${limit}`),
  experiment: (runId: string) => req<RunDetail>(`/api/experiments/${runId}`),
  // --- Strix validation layer ------------------------------------------------
  strixStatus: () => req<StrixStatus>("/api/strix/status"),
  localValidationRuns: () => req<{ runs: LocalValidationRun[] }>("/api/validation/local"),
  runLocalValidation: () => post<LocalValidationRun>("/api/validation/local"),
  strixRuns: (limit = 50) => req<{ runs: StrixRun[]; availability: StrixAvailability }>(`/api/strix/runs?limit=${limit}`),
  strixRun: (runId: string) => req<StrixRun>(`/api/strix/runs/${runId}`),
  strixFindings: (runId: string) => req<{ run: StrixRun; parsed: StrixParsed | null; note?: string }>(`/api/strix/runs/${runId}/findings`),
  validateScenario: (scenarioId: string, scanMode = "quick", target?: string) =>
    post<ValidationResult>(`/api/scenarios/${scenarioId}/validate`, { scenario_id: scenarioId, scan_mode: scanMode, target }),
  validations: (limit = 50) => req<{ validations: ValidationComparison[] }>(`/api/validations?limit=${limit}`),
  validation: (id: string) => req<ValidationComparison>(`/api/validations/${id}`),
  compareStageEvidence: (id: string, events: SandboxStageEvent[]) =>
    post<StageEvidenceReport>(`/api/validations/${id}/stage-evidence`, { events }),
  defenceRecommendation: () => req<DefenceRecommendation>("/api/defence/recommendation"),
  defenceSimulate: (k = 6) => post<{ counterfactual: Counterfactual; recommendation: DefenceRecommendation }>("/api/defence/simulate", { action: "auto", k }),
  defenceApprove: (recommendationId: string, approver = "analyst") => post<DefenceDecision>("/api/defence/approve", { recommendation_id: recommendationId, approver }),
  defenceReject: (recommendationId: string, reason = "", approver = "analyst") => post<DefenceDecision>("/api/defence/reject", { recommendation_id: recommendationId, approver, reason }),
  defencePending: () => req<{ pending: DefenceRecommendation[] }>("/api/defence/pending"),
  registerTarget: (target: string, environment: string, label = "") => post<TargetRegistration>("/api/strix/targets", { target, environment, label }),
  // --- Attack Labs & Ollama 1-Click Patch -----------------------------------
  attackLabStatus: () => req<any>("/api/attack-lab/status"),
  attackLabVectors: () => req<{ vectors: any[] }>("/api/attack-lab/vectors"),
  startAttackLabProbe: (vectorId = "ssh_bruteforce", scanMode = "quick", intensity = 12, targetIp?: string, targetPort?: number) =>
    post<any>("/api/attack-lab/probe/start", { vector_id: vectorId, scan_mode: scanMode, intensity, target_ip: targetIp, target_port: targetPort }),
  stopAttackLabProbe: () => post<any>("/api/attack-lab/probe/stop"),
  suggestPatchForHost: (host: string, vectorId?: string, port?: number) =>
    post<{ host: string; vector_id: string; patch: any }>("/api/attack-lab/patch/suggest", { host, vector_id: vectorId, port }),
  applyOneClickPatch: (patchId: string, approver = "analyst") =>
    post<any>("/api/attack-lab/patch/apply", { patch_id: patchId, approver }),
  resetSandbox: () => post<any>("/api/attack-lab/sandbox/reset"),
  attackLabPatches: () => req<{ patches: any[] }>("/api/attack-lab/patches"),
  attackLabProbeRecords: () => req<any>("/api/attack-lab/probe/records"),
  attackLabRiskAssessment: () => req<any>("/api/attack-lab/risk-assessment"),
  // --- PS Element B.1, B.2 & Track A ---------------------------------------
  flaggedFlows: (limit = 60, min_risk = 0.0) => req<FlaggedFlowsResponse>(`/api/flows/flagged?limit=${limit}&min_risk=${min_risk}`),
  benchmarkComparison: () => req<BenchmarkComparison>("/api/benchmark/comparison"),
  uploadFlows: async (file: File, clearPrevious = false) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`/api/upload/flows?clear_previous=${clearPrevious}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },
};

export interface FlaggedFlow {
  flow_id: string;
  timestamp?: number;
  src: string;
  dst: string;
  src_port: number;
  dst_port: number;
  protocol: string;
  duration: number;
  bytes_fwd: number;
  bytes_bwd: number;
  tot_bytes: number;
  packets_fwd: number;
  packets_bwd: number;
  label: string;
  stage_id: number;
  predicted_stage: string;
  technique_id: string;
  risk_score: number;
  risk_pct: number;
  risk_band: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "BENIGN" | "UNASSESSED";
}

export interface FlaggedFlowsResponse {
  count: number;
  flows: FlaggedFlow[];
  summary: {
    critical_count: number;
    high_count: number;
    medium_count: number;
    unassessed_count?: number;
    low_or_benign_count: number;
  };
}

export interface BenchmarkComparison {
  title: string;
  problem_statement: string;
  evaluation_date: string;
  dataset: string;
  dataset_flows_evaluated: number;
  calibration_constraint: string;
  models: {
    cybermind_world_model: {
      name: string;
      parameters: number;
      metrics: {
        f1: number;
        precision: number;
        recall: number;
        fpr: number;
        ap: number;
        illegal_transition_rate: number;
      };
      confusion_matrix: { tp: number; fp: number; tn: number; fn: number };
    };
    logistic_baseline: {
      name: string;
      parameters: number;
      metrics: {
        f1: number;
        precision: number;
        recall: number;
        fpr: number;
        ap: number;
        illegal_transition_rate: number;
      };
      confusion_matrix: { tp: number; fp: number; tn: number; fn: number };
    };
    gnn_only_ablation?: {
      name: string;
      metrics: Record<string, number>;
    };
  };
  deltas_vs_logistic: Record<string, string>;
  verdict: string;
}

export interface TestCaseInfo {
  id: string;
  name: string;
  description: string;
  filename: string;
  replay_file?: string;
  attack_type: string;
  stage: string;
  attack_stage: number;
  events_count: number;
  size_mb: number;
  provenance: string;
  target: string;
}

export interface TestCaseLoadResult {
  status: string;
  testcase_id: string;
  name: string;
  accepted: number;
  rejected: number;
  event_count: number;
  state_windows: number;
  ready: boolean;
  forecast: Forecast | null;
  state: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    dominant_stage: number;
    labels: Record<string, number>;
  };
}

/* ------------------------------ Strix types ------------------------------ */
export interface StrixAvailability {
  available: boolean;
  binary: string;
  reason: string | null;
}
export interface StrixStatus extends StrixAvailability {
  ready?: boolean;
  checks?: { cli: boolean; docker: boolean; sandbox: boolean; llm: boolean };
  targets: TargetRegistration[];
}
export interface LocalValidationRun {
  run_id: string;
  created_at: number;
  mode: "BUNDLED_IN_PROCESS_SANDBOX";
  verdict: "SANDBOX_RESPONSES_OBSERVED" | "INCONCLUSIVE";
  forecast: { forecast_id: string | null; predicted_stage: string | null; predicted_risk: number | null };
  checks: Array<{ name: string; http_status: number | null; response_sha256: string | null; outcome: string; error?: string }>;
  limitation: string;
}
export interface TargetRegistration {
  target: string;
  environment: string;
  label: string;
  registered_at: number;
  notes: string;
}
export interface StrixRun {
  run_id: string;
  scenario_id: string;
  started_at: number;
  finished_at: number | null;
  status: string;
  target: string;
  mode: string;
  budget: number | null;
  artifacts_path: string | null;
  return_code: number | null;
  error: string | null;
}
export interface StrixFinding {
  finding_id: string;
  title: string;
  severity: string;
  cvss: number | null;
  affected_asset: string | null;
  evidence: string;
  reproduction_summary: string;
  remediation_guidance: string;
  confidence: number;
  timestamp: number | null;
  cve?: string | null;
  cwe?: string | null;
  attack_stage_hypothesis: number | null;
  attack_stage_inferred: boolean;
}
export interface StrixParsed {
  findings: StrixFinding[];
  finding_count: number;
  max_severity: string | null;
  max_cvss: number | null;
  observed_stage: number | null;
  observed_stage_inferred: boolean;
  scan_metadata?: Record<string, unknown>;
}
export interface ValidationComparison {
  validation_id: string;
  scenario_id: string;
  strix_run_id: string;
  forecast_id: string | null;
  predicted_stage: number | null;
  predicted_stage_label: string | null;
  predicted_risk: number | null;
  predicted_entities: string[];
  observed_stage: number | null;
  observed_stage_label: string | null;
  observed_stage_inferred: boolean;
  observed_risk_estimate: number | null;
  observed_entities: string[];
  finding_count: number;
  max_severity: string | null;
  prediction_error: number | null;
  match: "MATCH" | "PARTIAL" | "MISMATCH" | "INCONCLUSIVE" | null;
  lead_time: number | null;
  started_at: number;
  finished_at: number | null;
}
export interface ValidationResult {
  experiment_id?: string;
  run: StrixRun;
  comparison: ValidationComparison;
  parsed: StrixParsed | Record<string, never>;
}

export interface SandboxStageEvent {
  event_id: string;
  source: "sandbox_event_log";
  stage_id: 3 | 5;
  timestamp: number;
  evidence_ref: string;
  verified_by: string;
  strix_finding_ids?: string[];
}

export interface StageEvidenceReport {
  experiment_id: string;
  protocol: string;
  forecast_id: string | null;
  forecast_ts: number;
  model_version: string | null;
  strix_run_id: string;
  strix_status: string;
  step_seconds: number;
  future_step_count: number;
  metric_status: string;
  stages: {
    stage_id: 3 | 5;
    stage: string;
    verdict: "MATCH" | "MISMATCH" | "NO_VERIFIED_EVENT" | "EVENT_OUTSIDE_HORIZON";
    forecast_steps: { step: number; stage_id: number; stage: string; risk: number }[];
    model_prediction: { step: number; stage_id: number; stage: string; risk: number; source: string } | null;
    verified_observation: { event_id: string; timestamp: number; stage_id: number; stage: string; evidence_ref: string; verified_by: string } | null;
    strix_support: { finding_id: string; timestamp: number | null; role: string }[];
  }[];
  evidence_rule: string;
}
export interface DefenceCandidate {
  action: string;
  action_label: string;
  host?: string | null;
  port?: number | null;
  future_risk: number;
  risk_reduction: number;
  band: string;
  stage_short?: string;
  confidence: number;
  validated: boolean;
  reversibility: number;
  collateral_impact: number;
  score: number;
  validation?: ValidationComparison | null;
}
export interface DefenceRecommendation {
  recommendation_id: string;
  action: string | null;
  action_label: string | null;
  host: string | null;
  port: number | null;
  reason: string;
  baseline_risk: number;
  expected_risk: number | null;
  risk_delta: number | null;
  confidence: number | null;
  validated: boolean;
  validation_run_id: string | null;
  approval_required: boolean;
  mode: string;
  candidates: DefenceCandidate[];
  disclaimer: string;
  generated_at: number;
}
export interface DefenceDecision {
  recommendation_id: string;
  decision: "approved" | "rejected";
  approver: string;
  decided_at: number;
}

export type LiveMessage =
  | ({ type: "system"; status: string } & Partial<ModelStatus>)
  | ({ type: "forecast" } & Partial<Forecast>)
  | { type: "state"; accepted?: number; rejected?: number; event_count?: number; forecast?: Forecast | null; source?: string }
  | { type: "scenario"; event: string; scenario_id: string; run_id?: string; tick?: number; events?: number; forecast?: Forecast | null }
  | { type: "strix.run_started"; run_id: string; scenario_id: string; status: string }
  | { type: "strix.run_completed"; run_id: string; status: string; artifacts_path?: string | null }
  | { type: "validation.completed"; validation_id: string; scenario_id: string; match: string; predicted_stage_label?: string | null; observed_stage_label?: string | null; finding_count?: number; strix_run_id: string }
  | { type: "defence.recommendation"; recommendation_id: string; action: string | null; action_label?: string | null; risk_delta: number | null; approval_required: boolean }
  | { type: "approval.granted"; recommendation_id: string; decision: string }
  | { type: "approval.rejected"; recommendation_id: string; decision: string }
  | { type: "intervention"; recommended: Intervention | null; baseline: Counterfactual["baseline"] }
  | { type: "alert"; message: string }
  | { type: string };

/** Extract the forecast from any live message variant (flat or nested). */
export function forecastOf(msg: LiveMessage): Forecast | null {
  if (msg.type === "forecast") {
    const nested = (msg as { forecast?: Forecast }).forecast;
    return nested ?? (msg as unknown as Forecast);
  }
  if (msg.type === "scenario" || msg.type === "state") {
    return (msg as { forecast?: Forecast | null }).forecast ?? null;
  }
  return null;
}

/** Reconnecting WebSocket that broadcasts typed live messages to subscribers. */
export function connectLive(onMessage: (msg: LiveMessage) => void, onStatus: (up: boolean) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry: ReturnType<typeof setTimeout> | null = null;
  let ping: ReturnType<typeof setInterval> | null = null;

  const open = () => {
    if (closed) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/live`);
    ws.onopen = () => {
      onStatus(true);
      ping = setInterval(() => ws?.readyState === 1 && ws.send("ping"), 15000);
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as LiveMessage;
        if (msg && typeof msg === "object" && "type" in msg) onMessage(msg);
      } catch { /* ignore malformed */ }
    };
    ws.onclose = () => {
      onStatus(false);
      if (ping) clearInterval(ping);
      if (!closed) retry = setTimeout(open, 2000);
    };
    ws.onerror = () => ws?.close();
  };
  open();
  return () => {
    closed = true;
    if (retry) clearTimeout(retry);
    if (ping) clearInterval(ping);
    ws?.close();
  };
}
