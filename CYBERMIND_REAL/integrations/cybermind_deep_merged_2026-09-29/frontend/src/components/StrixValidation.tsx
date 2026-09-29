import React, { useState } from "react";
import {
  ShieldCheck, ShieldAlert, ShieldQuestion, FlaskConical, Loader2, Check, X,
  Clock, ExternalLink, ChevronDown, ChevronUp, Activity, FileSearch, Zap, Code,
  Upload,
} from "lucide-react";
import type { LiveStore } from "../lib/live";
import { api, type LocalValidationRun, type SandboxStageEvent, type StageEvidenceReport, type ValidationComparison, type StrixFinding } from "../lib/api";

const SEV_STYLE: Record<string, string> = {
  critical: "bg-[#FBEAE7] text-[#B33A2B] border-[#F2C9C3]",
  high: "bg-[#FDF1E3] text-[#B4611E] border-[#F4D6BC]",
  medium: "bg-[#FBF3DF] text-[#8C5424] border-[#EEDFC0]",
  low: "bg-[#E9F6EC] text-[#1E7A43] border-[#C8E6CF]",
  info: "bg-[#F4F1EB] text-[#586474] border-[#EAE2D8]",
};

const MATCH_STYLE: Record<string, { chip: string; label: string; icon: React.ReactNode }> = {
  MATCH: { chip: "bg-[#E9F6EC] text-[#1E7A43] border-[#C8E6CF]", label: "Legacy heuristic comparison only", icon: <ShieldCheck className="w-4 h-4" /> },
  PARTIAL: { chip: "bg-[#FBF3DF] text-[#8C5424] border-[#EEDFC0]", label: "Legacy heuristic comparison only", icon: <ShieldQuestion className="w-4 h-4" /> },
  MISMATCH: { chip: "bg-[#FBEAE7] text-[#B33A2B] border-[#F2C9C3]", label: "Legacy heuristic comparison only", icon: <ShieldAlert className="w-4 h-4" /> },
  INCONCLUSIVE: { chip: "bg-[#F4F1EB] text-[#586474] border-[#EAE2D8]", label: "Run produced no comparable evidence", icon: <ShieldQuestion className="w-4 h-4" /> },
};

const pct = (v: number | null | undefined) => (v == null ? "—" : `${Math.round(v * 100)}%`);

/* --------------------------- single comparison ---------------------------- */
export const ValidationCard: React.FC<{ c: ValidationComparison; onOpenRun?: (runId: string) => void }> = ({ c, onOpenRun }) => {
  const [open, setOpen] = useState(false);
  const ms = MATCH_STYLE[c.match || "INCONCLUSIVE"];
  return (
    <div className="border border-[#EAE6DF] rounded-xl overflow-hidden bg-white">
      <button onClick={() => setOpen((o) => !o)} className="w-full text-left p-3.5 hover:bg-[#FAF8F5] transition-colors">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className={`shrink-0`}>{ms.icon}</span>
            <div className="min-w-0">
              <div className="text-xs font-bold text-[#1C232B] truncate">
                {c.predicted_stage_label || "—"} → Strix hypothesis: {c.observed_stage_label || "no evidence"}
                {c.observed_stage_inferred && <span className="ml-1.5 text-[9px] font-mono text-[#98A2AF]">(inferred)</span>}
              </div>
              <div className="text-[10px] text-[#7A8696] font-mono truncate">
                run {c.strix_run_id} · {new Date(c.started_at * 1000).toLocaleTimeString()} · {c.finding_count} finding{c.finding_count === 1 ? "" : "s"}
              </div>
            </div>
          </div>
          <span className={`shrink-0 px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase ${ms.chip}`}>{c.match || "—"}</span>
        </div>
      </button>
      {open && (
        <div className="border-t border-[#F0ECE4] p-3.5 bg-[#FCFBF9] space-y-3">
          <div className="grid grid-cols-3 gap-3 text-[11px]">
            <div>
              <div className="text-[9px] uppercase font-bold text-[#8C96A3] mb-1">CYBERMIND predicted</div>
              <div className="font-semibold text-[#2B3542]">{c.predicted_stage_label || "—"}</div>
              <div className="font-mono text-[#54606E]">risk {pct(c.predicted_risk)}</div>
            </div>
            <div>
              <div className="text-[9px] uppercase font-bold text-[#8C96A3] mb-1">Strix stage hypothesis</div>
              <div className="font-semibold text-[#2B3542]">{c.observed_stage_label || "—"}</div>
              <div className="font-mono text-[#54606E]">risk est. {pct(c.observed_risk_estimate)}</div>
            </div>
            <div>
              <div className="text-[9px] uppercase font-bold text-[#8C96A3] mb-1">Delta</div>
              <div className="font-mono text-[#54606E]">err {c.prediction_error != null ? pct(c.prediction_error) : "—"}</div>
              <div className="font-mono text-[#54606E]">lead {c.lead_time != null ? `${Math.round(c.lead_time)}s` : "—"}</div>
            </div>
          </div>
          {c.observed_entities.length > 0 && (
            <div className="text-[10px] text-[#54606E]">
              <span className="font-semibold">Evidence assets:</span>{" "}
              {c.observed_entities.map((e) => <span key={e} className="inline-block font-mono bg-white border border-[#EAE6DF] rounded px-1.5 py-0.5 mr-1 mb-0.5">{e}</span>)}
            </div>
          )}
          {onOpenRun && (
            <button onClick={() => onOpenRun(c.strix_run_id)}
              className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#DE5B49] hover:underline">
              <FileSearch className="w-3 h-3" /> View scan findings
            </button>
          )}
          <p className="text-[9px] text-[#98A2AF] leading-relaxed">
            Strix stage is inferred from vulnerability keywords and uses a different stage scheme. It is not ground truth or a stage-accuracy result.
            {ms.label}
          </p>
        </div>
      )}
    </div>
  );
};

/* ------------------------- findings detail modal -------------------------- */
export const FindingsModal: React.FC<{ runId: string; onClose: () => void }> = ({ runId, onClose }) => {
  const [data, setData] = useState<{ run: { status: string; target: string }; parsed: { findings: StrixFinding[]; finding_count: number; max_severity: string | null } | null; note?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    let alive = true;
    import("../lib/api").then(({ api }) =>
      api.strixFindings(runId).then((d) => { if (alive) { setData(d); setLoading(false); } }).catch(() => setLoading(false)),
    );
    return () => { alive = false; };
  }, [runId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-6" onClick={onClose}>
      <div className="bg-[#FBFAF7] border border-[#E5E0D8] rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-[#EAE6DF]">
          <div>
            <h3 className="font-bold text-sm text-[#1C232B]">Scan Findings · run {runId}</h3>
            <p className="text-[10px] text-[#7A8696] font-mono">{data?.run?.target || ""}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#F0ECE4]"><X className="w-4 h-4 text-[#54606E]" /></button>
        </div>
        <div className="p-4 overflow-y-auto space-y-2.5">
          {loading && <div className="flex items-center gap-2 text-xs text-[#7A8696]"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading artifacts…</div>}
          {!loading && !data?.parsed?.findings?.length && (
            <p className="text-xs text-[#7A8696]">{data?.note || "No findings parsed from this run's artifacts."}</p>
          )}
          {data?.parsed?.findings?.map((f) => (
            <div key={f.finding_id} className="bg-white border border-[#EAE6DF] rounded-xl p-3.5">
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <div className="text-xs font-bold text-[#1C232B]">{f.title}</div>
                <span className={`shrink-0 px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase ${SEV_STYLE[f.severity] || SEV_STYLE.info}`}>{f.severity}{f.cvss != null ? ` · CVSS ${f.cvss}` : ""}</span>
              </div>
              {f.affected_asset && <div className="text-[10px] font-mono text-[#7A8696] mb-1">{f.affected_asset}</div>}
              {f.evidence && <p className="text-[11px] text-[#54606E] leading-relaxed line-clamp-3">{f.evidence}</p>}
              {f.remediation_guidance && (
                <div className="mt-2 text-[10px] text-[#1E7A43] bg-[#F2FAF4] border border-[#C8E6CF] rounded-lg p-2">
                  <span className="font-bold">Remediation:</span> {f.remediation_guidance.slice(0, 220)}
                </div>
              )}
              <div className="mt-1.5 text-[9px] text-[#98A2AF] flex items-center gap-2">
                {f.cwe && <span className="font-mono">{f.cwe}</span>}
                {f.cve && <span className="font-mono">{f.cve}</span>}
                {f.attack_stage_inferred && <span>stage hypothesis: {f.attack_stage_hypothesis} (inferred)</span>}
                <span>confidence {pct(f.confidence)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* -------------- stage forecast vs reviewer-attested sandbox event --------- */
const StageEvidencePanel: React.FC<{ validations: ValidationComparison[] }> = ({ validations }) => {
  const [selection, setSelection] = useState("");
  const [events, setEvents] = useState<SandboxStageEvent[]>([]);
  const [fileName, setFileName] = useState("");
  const [report, setReport] = useState<StageEvidenceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const selectedId = validations.some((v) => v.validation_id === selection)
    ? selection : validations[0]?.validation_id || "";
  const chip = (verdict: string) => verdict === "MATCH"
    ? "bg-[#E9F6EC] text-[#1E7A43] border-[#C8E6CF]"
    : verdict === "MISMATCH" ? "bg-[#FBEAE7] text-[#B33A2B] border-[#F2C9C3]"
    : "bg-[#F4F1EB] text-[#586474] border-[#EAE2D8]";

  const loadEvents = async (file?: File) => {
    setReport(null);
    setError(null);
    if (!file) { setEvents([]); setFileName(""); return; }
    if (file.size > 1024 * 1024) { setError("Event log must be under 1 MB."); return; }
    try {
      const payload: unknown = JSON.parse(await file.text());
      const records = Array.isArray(payload) ? payload
        : payload && typeof payload === "object" && "events" in payload
          ? (payload as { events: unknown }).events : null;
      if (!Array.isArray(records) || records.length > 100) throw new Error("Expected a JSON array or {\"events\": [...]} with at most 100 events.");
      setEvents(records as SandboxStageEvent[]);
      setFileName(file.name);
    } catch (e) {
      setEvents([]);
      setFileName("");
      setError(e instanceof Error ? e.message : "Could not read the event log.");
    }
  };

  const compare = async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try { setReport(await api.compareStageEvidence(selectedId, events)); }
    catch (e) { setReport(null); setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  };

  return (
    <div className="bg-[#FCFBF9] border border-[#EAE6DF] rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-[#DE5B49]" />
            <h4 className="text-xs font-bold text-[#1C232B]">Lateral &amp; Exfiltration evidence</h4></div>
          <p className="mt-1 text-[10px] text-[#7A8696] leading-relaxed">Frozen model forecast → reviewer-attested sandbox event. Strix findings support the case; they do not establish an attack stage.</p>
        </div>
        <span className="shrink-0 px-2 py-0.5 rounded-md border bg-[#F4F1EB] text-[#586474] border-[#EAE2D8] text-[9px] font-bold uppercase">Case evidence</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select aria-label="Validation run" value={selectedId} onChange={(e) => { setSelection(e.target.value); setReport(null); }}
          className="min-w-0 flex-1 bg-white border border-[#EAE6DF] rounded-lg px-2.5 py-2 text-[11px] text-[#2B3542] focus:outline-none focus:border-[#DE5B49]">
          {!validations.length && <option value="">No completed validation</option>}
          {validations.map((v) => <option key={v.validation_id} value={v.validation_id}>run {v.strix_run_id} · forecast {v.forecast_id || "unavailable"}</option>)}
        </select>
        <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-[#EAE6DF] bg-white px-3 py-2 text-[11px] font-semibold text-[#54606E] hover:bg-[#F4F1EB]">
          <Upload className="w-3.5 h-3.5" /> Event log JSON
          <input className="sr-only" type="file" accept=".json,application/json" onChange={(e) => void loadEvents(e.target.files?.[0])} />
        </label>
        <button onClick={() => void compare()} disabled={!selectedId || loading}
          className="inline-flex items-center gap-1.5 rounded-lg bg-[#2B3542] px-3 py-2 text-[11px] font-bold text-white hover:bg-[#1C232B] disabled:opacity-40">
          {loading && <Loader2 className="w-3 h-3 animate-spin" />} Compare
        </button>
      </div>
      <p className="text-[10px] text-[#8C96A3]">{fileName ? `${fileName} · ${events.length} event(s)` : "No event log supplied: comparison will remain unverified."} Each event needs its stage (3 or 5), timestamp, evidence reference and reviewer.</p>
      <details className="text-[10px] text-[#7A8696]">
        <summary className="cursor-pointer font-semibold text-[#54606E]">Event log format</summary>
        <pre className="mt-2 overflow-x-auto rounded-lg border border-[#EAE6DF] bg-white p-2.5 font-mono text-[9px] leading-relaxed">{`{"events":[{"event_id":"replace-me","source":"sandbox_event_log","stage_id":3,"timestamp":0,"evidence_ref":"sha256:replace-me","verified_by":"reviewer-name"}]}`}</pre>
        <p className="mt-1">Example schema only. Use the actual UTC epoch-second timestamp and independently reviewed evidence; stage 5 is Exfiltration.</p>
      </details>
      {error && <p role="alert" className="rounded-lg border border-[#F2C9C3] bg-[#FBEAE7] px-3 py-2 text-[11px] text-[#B33A2B]">{error}</p>}

      {report && <div className="space-y-2">
        <p className="text-[10px] font-mono text-[#7A8696]">forecast {report.forecast_id} · Strix run {report.strix_run_id} · saved experiment {report.experiment_id}</p>
        {report.stages.map((stage) => <div key={stage.stage_id} className="rounded-xl border border-[#EAE6DF] bg-white p-3 space-y-2">
          <div className="flex items-center justify-between gap-2"><span className="text-[11px] font-bold text-[#1C232B]">{stage.stage}</span>
            <span className={`rounded-md border px-2 py-0.5 text-[9px] font-bold uppercase ${chip(stage.verdict)}`}>{stage.verdict.replaceAll("_", " ")}</span></div>
          <div className="flex flex-wrap gap-1.5">{stage.forecast_steps.map((s) => <span key={s.step} className="rounded-md border border-[#EAE6DF] bg-[#FCFBF9] px-2 py-1 text-[10px] text-[#54606E]">+{s.step - 1} · {s.stage || "Unknown"} · {pct(s.risk)}</span>)}</div>
          <div className="grid gap-2 text-[10px] text-[#54606E] sm:grid-cols-2">
            <div><span className="font-bold text-[#2B3542]">Model at event window:</span> {stage.model_prediction ? `+${stage.model_prediction.step - 1} ${stage.model_prediction.stage} (${pct(stage.model_prediction.risk)})` : "No comparable event"}</div>
            <div><span className="font-bold text-[#2B3542]">Sandbox observation:</span> {stage.verified_observation ? `${new Date(stage.verified_observation.timestamp * 1000).toLocaleTimeString()} · ${stage.verified_observation.event_id} · reviewer ${stage.verified_observation.verified_by}` : "No reviewer-attested event in horizon"}</div>
          </div>
          {stage.verified_observation && <div className="text-[9px] font-mono text-[#8C96A3] break-all">evidence {stage.verified_observation.evidence_ref} · {stage.strix_support.length} linked Strix finding(s)</div>}
        </div>)}
        <p className="text-[9px] text-[#98A2AF] leading-relaxed">Case-level timing evidence only; this is not held-out stage accuracy. An uploaded reviewer name and evidence reference are attestations, not cryptographic verification.</p>
      </div>}
    </div>
  );
};

/* ----------------------------- main panel --------------------------------- */
export const ValidationPanel: React.FC<{ store: LiveStore }> = ({ store }) => {
  const [showFindings, setShowFindings] = useState<string | null>(null);
  const [localRun, setLocalRun] = useState<LocalValidationRun | null>(null);
  const [localBusy, setLocalBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  React.useEffect(() => {
    api.localValidationRuns().then((r) => setLocalRun(r.runs[0] ?? null)).catch(() => undefined);
  }, []);
  const runLocal = async () => {
    setLocalBusy(true);
    setLocalError(null);
    try { setLocalRun(await api.runLocalValidation()); }
    catch (error) { setLocalError(error instanceof Error ? error.message : String(error)); }
    finally { setLocalBusy(false); }
  };
  const strixOk = store.strixStatus?.ready ?? store.strixStatus?.available;
  const activeScenario = store.scenarioList.length ? "lateral_movement" : null;
  const recent = store.validations.slice(0, 6);

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-[#DE5B49]" />
          <h3 className="font-bold text-sm text-[#1C232B]">Validation Engine</h3>
          <span className="text-[9px] font-mono text-[#98A2AF] uppercase">local checks and controlled adversarial evidence</span>
        </div>
        <span className={`px-2 py-0.5 rounded-md border text-[9px] font-bold uppercase ${
          strixOk ? "bg-[#E9F6EC] text-[#1E7A43] border-[#C8E6CF]" : "bg-[#F4F1EB] text-[#8C96A3] border-[#EAE2D8]"}`}>
          {strixOk ? "Strix ready" : "Strix unavailable"}
        </span>
      </div>

      <div className="rounded-xl border border-[#D9E7DD] bg-[#F6FAF7] p-3.5 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="text-[11px] font-bold text-[#1E6F40]">Built-in sandbox check <span className="font-mono text-[9px]">· OFFLINE</span></div>
            <p className="text-[10px] text-[#586474]">Record bundled target responses alongside the latest frozen forecast. This checks sandbox behavior, not model accuracy.</p>
          </div>
          <button onClick={() => void runLocal()} disabled={localBusy}
            className="shrink-0 rounded-lg bg-[#2B3542] px-3 py-2 text-[11px] font-bold text-white hover:bg-[#1C232B] disabled:opacity-40">
            {localBusy ? "Checking…" : "Run local check"}
          </button>
        </div>
        {!store.state?.ready && <p className="text-[10px] text-[#8C5424]">Load a PCAP, CSV, or real-flow sample first. The check will explain if the case has too few observation windows.</p>}
        {localError && <p role="alert" className="text-[10px] text-[#B33A2B] break-words">{localError}</p>}
        {localRun && <div className="rounded-lg border border-[#D9E7DD] bg-white p-3 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px]">
            <span className="font-bold text-[#1C232B]">{localRun.verdict.replaceAll("_", " ")}</span>
            <span className="font-mono text-[#7A8696] break-all">{localRun.run_id} · forecast {localRun.forecast.forecast_id ?? "—"}</span>
          </div>
          <div className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-4">
            {localRun.checks.map((check) => <div key={check.name} className="min-w-0 rounded-md bg-[#F7F5F0] px-2 py-1.5 text-[10px] text-[#54606E]">
              <span className="font-semibold">{check.name}</span><span className="ml-1 font-mono">HTTP {check.http_status ?? "error"}</span>
              <div className="font-mono text-[9px] truncate" title={check.response_sha256 ?? check.error ?? ""}>SHA-256 {check.response_sha256?.slice(0, 16) ?? "—"}…</div>
            </div>)}
          </div>
          <p className="text-[9px] leading-relaxed text-[#7A8696]">{localRun.limitation}</p>
        </div>}
      </div>

      {!strixOk && (
        <div className="bg-[#FCFBF7] border border-[#EEDFC0] rounded-xl p-3 text-[11px] text-[#8C5424] leading-relaxed">
          <strong>Controlled validation unavailable.</strong>{" "}
          {store.strixStatus?.reason ?? "Checking the validator setup…"}.
          {store.strixStatus?.targets?.length
            ? " A sandbox target is registered; the validator CLI, its Docker runtime, and an LLM provider must be available before a scan can run."
            : " Register an authorized sandbox target after configuring the validator CLI, Docker, and an LLM provider."}
          {" "}Forecasting remains available. No Strix scan evidence is generated while this control is disabled.
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={() => activeScenario && store.runValidation(activeScenario)}
          disabled={!strixOk || store.busy.validate || !activeScenario}
          className="px-3.5 py-2 bg-[#2B3542] hover:bg-[#1C232B] disabled:opacity-40 text-white text-xs font-bold rounded-xl flex items-center gap-2">
          {store.busy.validate ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}
          {store.busy.validate ? "Validating…" : "Run controlled validation"}
        </button>
        {store.lastValidation && (
          <span className="text-[10px] text-[#7A8696] font-mono">last: {store.lastValidation.match} · run {store.lastValidation.strix_run_id}</span>
        )}
      </div>

      {store.busy.validate && (
        <div className="bg-[#FCFBF9] border border-[#EAE6DF] rounded-xl p-3 text-[11px] text-[#54606E] space-y-1">
          <div className="flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> Validation agent scanning registered sandbox target…</div>
          <div className="text-[9px] text-[#98A2AF] font-mono pl-5">HEADLESS · SANDBOX · QUICK SCAN · artifacts parsed on completion</div>
        </div>
      )}

      <div className="space-y-2">
        <div className="text-[10px] font-bold uppercase tracking-wide text-[#8C96A3]">Recent forecast and scan cases</div>
        {!recent.length && <p className="text-[11px] text-[#98A2AF]">No validations yet. Run a controlled sandbox scan, then attach a reviewer-attested event log to compare stage timing.</p>}
        {recent.map((c) => <ValidationCard key={c.validation_id} c={c} onOpenRun={setShowFindings} />)}
      </div>

      <StageEvidencePanel validations={recent} />

      {showFindings && <FindingsModal runId={showFindings} onClose={() => setShowFindings(null)} />}
    </div>
  );
};

/* ---------------------- defence recommendation panel ---------------------- */
export const DefencePanel: React.FC<{ store: LiveStore }> = ({ store }) => {
  const [expanded, setExpanded] = useState(false);
  const rec = store.recommendation;

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#DE5B49]" />
          <h3 className="font-bold text-sm text-[#1C232B]">Defence Recommendation</h3>
        </div>
        <button onClick={() => store.runDefence()} disabled={store.busy.defence}
          className="px-3 py-1.5 bg-[#DE5B49] hover:bg-[#C94838] disabled:opacity-50 text-white text-[11px] font-bold rounded-lg flex items-center gap-1.5">
          {store.busy.defence ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
          {store.busy.defence ? "Ranking…" : "Generate"}
        </button>
      </div>

      {!rec && <p className="text-[11px] text-[#98A2AF]">Generate a ranked recommendation from the latest counterfactual futures and validation evidence.</p>}

      {rec && (
        <div className="space-y-3">
          <div className={`rounded-xl border p-3.5 ${rec.approval_required ? "bg-[#FDF6EC] border-[#EEDFC0]" : "bg-[#F2FAF4] border-[#C8E6CF]"}`}>
            {rec.approval_required && (
              <div className="text-[10px] font-black uppercase tracking-wider text-[#8C5424] mb-1.5">Human approval required</div>
            )}
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-black text-[#1C232B]">{rec.action_label || rec.action || "—"}</div>
                <div className="text-[10px] text-[#7A8696]">{rec.host ? `target ${rec.host}` : ""} · confidence {pct(rec.confidence)}</div>
              </div>
              {rec.risk_delta != null && (
                <div className="text-right">
                  <div className={`text-lg font-black font-mono ${rec.risk_delta < 0 ? "text-[#1E7A43]" : "text-[#B33A2B]"}`}>{rec.risk_delta > 0 ? "+" : ""}{rec.risk_delta}</div>
                  <div className="text-[9px] uppercase font-bold text-[#8C96A3]">risk Δ</div>
                </div>
              )}
            </div>
            <div className="mt-2 flex items-center gap-3 text-[10px] font-mono text-[#54606E]">
              <span>baseline {rec.baseline_risk}</span>
              <span>→ expected {rec.expected_risk ?? "—"}</span>
              <span className={rec.validated ? "text-[#1E7A43] font-bold" : "text-[#8C96A3]"}>
                {rec.validated ? `validated (run ${rec.validation_run_id})` : "not yet validated"}
              </span>
            </div>
            <p className="mt-2 text-[10px] text-[#7A8696] leading-relaxed">{rec.reason}</p>
          </div>

          {rec.approval_required ? (
            <div className="flex items-center gap-2">
              <button onClick={() => store.approveRecommendation(rec.recommendation_id)}
                className="flex-1 px-3 py-2 bg-[#1E7A43] hover:bg-[#186635] text-white text-xs font-bold rounded-xl flex items-center justify-center gap-1.5">
                <Check className="w-3.5 h-3.5" /> Approve
              </button>
              <button onClick={() => store.rejectRecommendation(rec.recommendation_id, "analyst rejected")}
                className="flex-1 px-3 py-2 bg-white border border-[#EAE2D8] hover:bg-[#FAF8F5] text-[#54606E] text-xs font-bold rounded-xl flex items-center justify-center gap-1.5">
                <X className="w-3.5 h-3.5" /> Reject
              </button>
            </div>
          ) : (
            <div className="text-[10px] text-[#1E7A43] font-bold uppercase tracking-wide flex items-center gap-1.5">
              <Clock className="w-3 h-3" /> Autonomous sandbox mode — no approval gate required
            </div>
          )}

          {rec.candidates.length > 0 && (
            <div>
              <button onClick={() => setExpanded((e) => !e)} className="flex items-center gap-1 text-[10px] font-bold text-[#54606E] uppercase tracking-wide">
                {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                All {rec.candidates.length} ranked candidates
              </button>
              {expanded && (
                <table className="w-full text-left mt-2 border-collapse text-[10px]">
                  <thead>
                    <tr className="border-b border-[#F0ECE4] text-[9px] font-semibold text-[#8C96A3]">
                      <th className="py-1.5 px-1.5">Action</th><th className="py-1.5 px-1.5">Future risk</th>
                      <th className="py-1.5 px-1.5">Reduction</th><th className="py-1.5 px-1.5">Score</th><th className="py-1.5 px-1.5">Validated</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F4F1EA]">
                    {rec.candidates.map((c, i) => (
                      <tr key={`${c.action}-${c.host ?? i}`} className="hover:bg-[#FAF8F5]">
                        <td className="py-1.5 px-1.5 font-semibold text-[#2B3542]">{c.action_label}{c.host ? ` · ${c.host}` : ""}</td>
                        <td className="py-1.5 px-1.5 font-mono">{Math.round(c.future_risk * 100)}</td>
                        <td className="py-1.5 px-1.5 font-mono text-[#1E7A43]">-{Math.round(c.risk_reduction * 100)}</td>
                        <td className="py-1.5 px-1.5 font-mono font-bold">{c.score.toFixed(2)}</td>
                        <td className="py-1.5 px-1.5">{c.validated ? <Check className="w-3 h-3 text-[#1E7A43]" /> : <span className="text-[#98A2AF]">—</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          <p className="text-[9px] text-[#98A2AF] leading-relaxed">{rec.disclaimer}</p>
        </div>
      )}
    </div>
  );
};

/* ------------------------- forecast evidence panel ------------------------ */
export const ForecastEvidencePanel: React.FC<{ store: LiveStore }> = ({ store }) => {
  void store;
  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-2">
        <ExternalLink className="w-4 h-4 text-[#DE5B49]" />
        <h3 className="font-bold text-sm text-[#1C232B]">Forecast Evidence</h3>
      </div>
      <p className="text-[11px] text-[#7A8696] leading-relaxed">
        Every forecast references its source windows, model version and forecast_id. Validations link a forecast_id
        to a validation run and store the comparison as a queryable experiment — the full
        prediction → intervention → validation → outcome chain is auditable.
      </p>
    </div>
  );
};

/* ------------------------ Attack Labs & Strix Panel ------------------------ */
export const AttackLabPanel: React.FC<{ store?: LiveStore }> = () => {
  const [vector, setVector] = useState("ssh_bruteforce");
  const [loading, setLoading] = useState(false);
  const [applyingPatch, setApplyingPatch] = useState(false);
  const [status, setStatus] = useState<any>(null);
  const [patchSuccess, setPatchSuccess] = useState<string | null>(null);

  const fetchStatus = React.useCallback(async () => {
    try {
      const { api } = await import("../lib/api");
      const data = await api.attackLabStatus();
      setStatus(data);
    } catch {}
  }, []);

  React.useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleLaunchProbe = async () => {
    setLoading(true);
    setPatchSuccess(null);
    try {
      const { api } = await import("../lib/api");
      await api.startAttackLabProbe(vector, "quick", 10);
      let count = 0;
      const poll = setInterval(async () => {
        count++;
        const s = await api.attackLabStatus();
        setStatus(s);
        if (!s.active_session || s.active_session.status !== "RUNNING" || count > 20) {
          clearInterval(poll);
          setLoading(false);
        }
      }, 500);
    } catch (e) {
      setLoading(false);
    }
  };

  const handleApplyPatch = async () => {
    const patchId = status?.active_session?.generated_patch?.patch_id;
    if (!patchId) return;
    setApplyingPatch(true);
    try {
      const { api } = await import("../lib/api");
      const res = await api.applyOneClickPatch(patchId);
      setPatchSuccess(res.mitigation_summary || "Patch deployed & verified!");
      await fetchStatus();
    } catch {}
    setApplyingPatch(false);
  };

  const activeSession = status?.active_session;
  const currentRisk = (activeSession?.final_risk || activeSession?.peak_risk || 0.018) * 100;
  const generatedPatch = activeSession?.generated_patch;

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-[#DE5B49]" />
          <div>
            <h3 className="font-bold text-sm text-[#1C232B]">Attack Labs &amp; Strix (Isolated Sandbox)</h3>
            <span className="text-[10px] text-[#7A8696] font-mono">
              Target: 127.0.0.1:8081 &bull; Safety Gate: Non-Exploiting &bull; PT Model Risk Feed
            </span>
          </div>
        </div>
        <a href="/ui-copy/attack_labs.html" target="_blank" rel="noreferrer"
          className="px-2.5 py-1 text-[10px] font-bold text-[#DE5B49] bg-[#FBEAE7] hover:bg-[#F8D7D2] rounded-lg border border-[#F2C9C3] flex items-center gap-1 transition-colors">
          <ExternalLink className="w-3 h-3" /> Full HUD Mode
        </a>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-bold uppercase text-[#8C96A3] mb-1 block">Probe Vector</label>
          <select
            value={vector}
            onChange={(e) => setVector(e.target.value)}
            disabled={loading}
            className="w-full text-xs bg-[#FAF8F5] border border-[#EAE6DF] rounded-xl px-3 py-2 text-[#1C232B] font-medium focus:outline-none focus:border-[#DE5B49]">
            <option value="ssh_bruteforce">SSH Credential Brute Force (CWE-307 / Port 22)</option>
            <option value="sqli_probe">SQL Injection Parameter Probe (CWE-89 / Port 8081)</option>
            <option value="smb_lateral">SMB Lateral Share Enumeration (CWE-285 / Port 445)</option>
            <option value="c2_beacon">Egress C2 Beaconing Channel (CWE-200 / Port 8080)</option>
          </select>
        </div>

        <div>
          <label className="text-[10px] font-bold uppercase text-[#8C96A3] mb-1 block">Adversarial Action</label>
          <button
            onClick={handleLaunchProbe}
            disabled={loading}
            className="w-full py-2 bg-[#DE5B49] hover:bg-[#C94838] disabled:opacity-50 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 shadow-sm transition-all">
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            {loading ? "Probing Sandbox..." : "Launch Strix Penetration Probe"}
          </button>
        </div>
      </div>

      {activeSession && (
        <div className="bg-[#FAF8F5] border border-[#EAE6DF] rounded-xl p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#1C232B]">{activeSession.vector?.name}</span>
            <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded ${currentRisk > 50 ? "bg-[#FBEAE7] text-[#B33A2B]" : "bg-[#E9F6EC] text-[#1E7A43]"}`}>
              MODEL RISK: {currentRisk.toFixed(1)}%
            </span>
          </div>

          <div className="text-[10px] text-[#7A8696] font-mono">
            Status: {activeSession.status} &bull; Flows Ingested to PT Model: {activeSession.flows_generated}
          </div>

          {activeSession.outcome_message && (
            <p className="text-[11px] text-[#54606E] leading-relaxed border-t border-[#EAE6DF] pt-2">
              {activeSession.outcome_message}
            </p>
          )}

          {generatedPatch && (
            <div className="mt-2 bg-white border border-[#EAE6DF] rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#1C232B] flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5 text-[#1E7A43]" />
                  AI Defensive Patch ({generatedPatch.engine})
                </span>
                <span className="text-[9px] font-mono text-[#7A8696]">{generatedPatch.target_file}</span>
              </div>

              <div className="bg-[#1C232B] text-emerald-400 p-2.5 rounded-lg text-[10px] font-mono overflow-x-auto max-h-[140px]">
                <pre>{generatedPatch.patch_diff}</pre>
              </div>

              <button
                onClick={handleApplyPatch}
                disabled={applyingPatch || generatedPatch.applied}
                className="w-full py-2 bg-[#1E7A43] hover:bg-[#186635] disabled:opacity-50 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-all">
                {applyingPatch ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                {generatedPatch.applied ? "Patch Applied &amp; Target Secured" : "Apply 1-Click AI Patch"}
              </button>
            </div>
          )}

          {patchSuccess && (
            <div className="bg-[#E9F6EC] border border-[#C8E6CF] text-[#1E7A43] p-2.5 rounded-xl text-xs font-medium">
              {patchSuccess}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
