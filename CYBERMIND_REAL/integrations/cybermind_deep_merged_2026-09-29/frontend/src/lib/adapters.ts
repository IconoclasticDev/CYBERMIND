/**
 * Adapters: backend responses → UI view models.
 * Provenance is preserved and displayed honestly (REPLAY / SYNTHETIC / LIVE).
 */
import type {
  StateResponse, ForecastStep, TelemetryEvent, AttackGravity,
  GraphNode, GraphEdge,
} from "./api";

export type Severity = "High" | "Medium" | "Low";
export type NodeStatus = "compromised" | "high-risk" | "medium-risk" | "normal";

export interface UINode {
  id: string;
  name: string;
  ip: string;
  status: NodeStatus;
  threatScore: number;
  x: number;
  y: number;
  role: string;
  type: string;
  index: number;
  activity: number;
  gravity?: number;
  lastActivity: string;
}

export interface UILink {
  id: string;
  source: string;
  target: string;
  type: "traffic" | "suspicious";
  protocol: string;
  port?: number;
  label?: string;
  animated?: boolean;
}

export interface UIEvent {
  id: string;
  time: string;
  source: string;
  destination?: string;
  event: string;
  severity: Severity;
  protocol?: string;
  label: string;
  stage?: number | null;
  technique_id?: string | null;
  scenario_id?: string | null;
  source_stream?: string | null;
}

export const STAGE_SHORT_NAMES = ["Benign", "Recon", "Lateral", "Impact"];
export const STAGE_COLORS: Record<number, string> = {
  0: "#2EAA58", 1: "#E58B44", 2: "#DE5B49", 3: "#B33A2B",
};

export function bandLabel(risk: number): { label: string; sev: Severity } {
  if (risk >= 0.75) return { label: "Critical", sev: "High" };
  if (risk >= 0.5) return { label: "High", sev: "High" };
  if (risk >= 0.25) return { label: "Medium", sev: "Medium" };
  return { label: "Low", sev: "Low" };
}

function nodeStatus(anomaly: number, gravity: number | undefined): NodeStatus {
  const score = Math.max(anomaly, gravity ?? 0);
  if (score >= 0.75) return "compromised";
  if (score >= 0.5) return "high-risk";
  if (score >= 0.25) return "medium-risk";
  return "normal";
}

/** Deterministic layout so the map is stable between polls. */
function layoutNodes(nodes: GraphNode[]): Map<string, { x: number; y: number }> {
  const pos = new Map<string, { x: number; y: number }>();
  const sorted = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
  const n = sorted.length || 1;
  if (n === 1) {
    pos.set(sorted[0].id, { x: 425, y: 235 });
    return pos;
  }
  if (n <= 3) {
    // Small graphs: horizontal spread across the middle band. The radial
    // layout degenerates to the top/bottom poles for n=2, pushing nodes and
    // labels out of the visible card area.
    const xs = n === 2 ? [215, 635] : [160, 425, 690];
    sorted.forEach((node, i) => pos.set(node.id, { x: xs[i], y: 235 }));
    return pos;
  }
  sorted.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    // viewBox is 850x480 like the reference design
    pos.set(node.id, { x: 425 + 300 * Math.cos(angle), y: 235 + 175 * Math.sin(angle) });
  });
  return pos;
}

export function toUINodes(state: StateResponse | null, gravity?: AttackGravity | null): UINode[] {
  if (!state?.nodes?.length) return [];
  const gmap = new Map((gravity?.gravity ?? []).map((g) => [g.host, g.attack_gravity]));
  const pos = layoutNodes(state.nodes);
  return state.nodes.map((n) => {
    const g = gmap.get(n.id);
    const anomaly = Math.min(1, Math.sqrt(Math.max(0, n.anomaly)));
    return {
      id: n.id,
      name: n.id,
      ip: n.id,
      status: nodeStatus(anomaly, g),
      threatScore: Math.round((g !== undefined ? Math.max(anomaly, g) : anomaly) * 100),
      x: pos.get(n.id)?.x ?? 425,
      y: pos.get(n.id)?.y ?? 235,
      role: `Observed endpoint · index ${n.index}`,
      type: "endpoint",
      index: n.index,
      activity: n.activity,
      gravity: g,
      lastActivity: "this window",
    };
  });
}

export function toUILinks(state: StateResponse | null): UILink[] {
  if (!state?.edges?.length) return [];
  return state.edges.map((e, i) => {
    const suspicious = e.port === 445 || e.port === 3389 || e.port === 22 || e.port === 8443 || e.port === 4444;
    return {
      id: `e${i}`,
      source: e.src,
      target: e.dst,
      type: suspicious ? "suspicious" : "traffic",
      protocol: e.protocol === 6 ? "TCP" : e.protocol === 17 ? "UDP" : `P${Math.round(e.protocol)}`,
      port: e.port ? Math.round(e.port) : undefined,
      label: e.port ? `Port ${Math.round(e.port)}` : undefined,
      animated: suspicious,
    };
  });
}

function fmtTime(ts: number | string | undefined): string {
  if (ts === undefined) return "—";
  const d = typeof ts === "number" ? new Date(ts < 1e12 ? ts * 1000 : ts) : new Date(ts);
  if (isNaN(d.getTime())) return String(ts);
  return d.toLocaleTimeString([], { hour12: false });
}

export function severityFromLabel(label: string, stage?: number | null): Severity {
  const l = (label || "").toUpperCase();
  if (l === "BENIGN") return "Low";
  if (stage === 3 || l.includes("EXFIL") || l.includes("IMPACT")) return "High";
  if (stage === 2 || l.includes("BOT") || l.includes("INFILTRATION")) return "High";
  return "Medium";
}

export function toUIEvents(events: TelemetryEvent[]): UIEvent[] {
  return events.map((e, i) => ({
    id: `ev${i}-${e.timestamp}`,
    time: fmtTime(e.timestamp),
    source: e.src,
    destination: e.dst,
    event: e.label || "flow",
    severity: severityFromLabel(e.label, e.attack_stage),
    protocol: e.protocol === 6 ? "TCP" : e.protocol === 17 ? "UDP" : e.protocol != null ? String(e.protocol) : undefined,
    label: e.label,
    stage: e.attack_stage,
    technique_id: e.technique_id,
    scenario_id: e.scenario_id,
    source_stream: e.source,
  }));
}

export interface UIMilestone {
  id: string;
  time: string;
  stage: string;
  detail: string;
  status: "completed" | "current" | "predicted";
  color: string;
  description: string;
  iocs: string[];
  mitreId: string;
}

/** Build the observed→predicted timeline from the last forecast. */
export function toMilestones(steps: ForecastStep[], currentStageId: number | undefined): UIMilestone[] {
  const out: UIMilestone[] = [];
  const cur = currentStageId ?? 0;
  out.push({
    id: "now",
    time: "now",
    stage: STAGE_SHORT_NAMES[cur] ?? "Unknown",
    detail: "(observed)",
    status: "current",
    color: STAGE_COLORS[cur] ?? "#2B3B4C",
    description: "Current observed network state, derived from the latest telemetry window.",
    iocs: ["observed window"],
    mitreId: "—",
  });
  steps.filter((s) => s.step > 0).forEach((s, i) => {
    out.push({
      id: `t${s.step}`,
      time: `t+${s.step}`,
      stage: s.stage_short ?? STAGE_SHORT_NAMES[s.stage_id] ?? "Unknown",
      detail: `(${Math.round(s.risk * 100)}% risk)`,
      status: "predicted",
      color: STAGE_COLORS[s.stage_id] ?? "#8A58D8",
      description:
        `Predicted state at step +${s.step}: risk ${Math.round(s.risk * 100)}%, ` +
        `stage ${s.stage ?? "unknown"}. Confidence ${Math.round((s.confidence ?? 0) * 100)}%. ` +
        (s.technique ? `Technique context: ${s.technique}.` : ""),
      iocs: [`step +${s.step}`, `stage_id ${s.stage_id}`],
      mitreId: s.technique_id || "—",
    });
    void i;
  });
  return out;
}

export function provenanceOf(source: string | undefined, scenario: string | null | undefined): string {
  if (scenario) return "SYNTHETIC";
  if (source?.startsWith("replay:") || source?.startsWith("file:") || source?.startsWith("upload:")) return "REPLAY";
  return "LIVE";
}
