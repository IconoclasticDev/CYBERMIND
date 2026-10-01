/* CYBERMIND war-room frontend. Vanilla JS, offline, no external deps. */
"use strict";

const $ = (id) => document.getElementById(id);
const pct = (x) => (x == null || isNaN(x) ? "—" : `${(Number(x) * 100).toFixed(1)}%`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const state = {
  screen: "warroom",
  paused: false,
  forecast: null,
  state: null,
  gravity: null,
  replay: { files: [], loaded: null, buffer: 0, index: 0 },
  ws: null,
};

async function getJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}
const postJSON = (url, body) =>
  getJSON(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

/* ------------------------------ navigation ------------------------------ */
document.querySelectorAll("#nav button").forEach((btn) => {
  btn.addEventListener("click", () => showScreen(btn.dataset.screen));
});
function showScreen(name) {
  state.screen = name;
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b.dataset.screen === name));
  ["warroom", "lab", "replay", "explain", "experiments", "system"].forEach((s) => {
    $(`screen-${s}`)?.classList.toggle("hidden", s !== name);
  });
  if (name === "lab") loadScenarios();
  if (name === "replay") loadReplayFiles();
  if (name === "experiments") loadRuns();
  if (name === "system") loadSystem();
  if (name === "explain") refreshExplainHosts();
}

/* ------------------------------ websocket ------------------------------- */
function connectWS() {
  try {
    const ws = new WebSocket(`ws://${location.host}/ws/live`);
    ws.onopen = () => setConn(true);
    ws.onmessage = (ev) => {
      let msg; try { msg = JSON.parse(ev.data); } catch { return; }
      handleLive(msg);
    };
    ws.onclose = () => { setConn(false); setTimeout(connectWS, 2000); };
    ws.onerror = () => setConn(false);
    state.ws = ws;
    setInterval(() => { if (ws.readyState === 1) ws.send("ping"); }, 15000);
  } catch { setConn(false); }
}
function setConn(up) {
  $("conn").textContent = up ? "● LIVE" : "● OFFLINE";
  $("conn").style.color = up ? "var(--ok)" : "var(--danger)";
}
function handleLive(msg) {
  if (msg.type === "forecast" && msg.steps) {
    state.forecast = msg;
    renderForecast(msg);
    if (state.screen === "lab") renderLabForecast(msg);
  } else if (msg.type === "scenario") {
    handleScenarioMsg(msg);
  } else if (msg.type === "intervention") {
    renderDefence(msg);
  } else if (msg.type === "state" && msg.forecast) {
    state.forecast = msg.forecast;
    renderForecast(msg.forecast);
  }
}

/* --------------------------- network graph ------------------------------ */
const STAGE_COLORS = { 0: "#6fb98f", 1: "#d6a04c", 2: "#e08a3c", 3: "#e66b5d" };
const STAGE_NAMES = { 0: "Benign", 1: "Recon", 2: "Lateral", 3: "Impact/Exfil" };

function renderNetwork(canvas, nodes, edges, opts = {}) {
  canvas.innerHTML = "";
  if (!nodes || !nodes.length) {
    canvas.innerHTML = '<div class="empty">No telemetry yet — start a scenario in the Lab.</div>';
    return;
  }
  const W = canvas.clientWidth || 600, H = canvas.clientHeight || 420;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("class", "net-svg");
  const pos = layout(nodes, W, H);
  const gmax = opts.gravityMax ?? 0;
  const maxEdgeBytes = Math.max(1, ...edges.map((e) => e.bytes || 0));

  // edges first (under nodes)
  for (const e of edges) {
    const a = pos.get(e.src), b = pos.get(e.dst);
    if (!a || !b) continue;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
    line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
    const intensity = (e.bytes || 0) / maxEdgeBytes;
    const attack = (a.stage ?? 0) > 0 || (b.stage ?? 0) > 0;
    line.setAttribute("stroke", attack ? "var(--danger)" : "var(--line2)");
    line.setAttribute("stroke-width", attack ? 1.2 + intensity * 3 : 0.6 + intensity * 2);
    line.setAttribute("class", attack ? "edge attack-edge" : "edge");
    line.setAttribute("stroke-opacity", attack ? 0.85 : 0.55);
    svg.appendChild(line);
    if (e.port) {
      const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
      t.setAttribute("x", (a.x + b.x) / 2); t.setAttribute("y", (a.y + b.y) / 2 - 3);
      t.setAttribute("class", "edge-label"); t.textContent = Math.round(e.port);
      svg.appendChild(t);
    }
  }
  // nodes
  for (const n of nodes) {
    const p = pos.get(n.id);
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const grav = opts.gravity ? opts.gravity[n.id] ?? 0 : 0;
    const isHighGravity = gmax > 0 && grav >= gmax * 0.8 && grav > 0.02;
    const stage = n.stage ?? 0;
    const color = stage > 0 ? STAGE_COLORS[stage] : "var(--ok)";
    const r = 8 + Math.min(10, (n.anomaly || 0) * 12) + (isHighGravity ? 4 : 0);
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", p.x); c.setAttribute("cy", p.y); c.setAttribute("r", r);
    c.setAttribute("fill", color);
    c.setAttribute("class", "node" + (isHighGravity ? " gravity-node" : ""));
    if (isHighGravity) c.setAttribute("stroke", "var(--accent)"), c.setAttribute("stroke-width", 2.5);
    c.setAttribute("data-host", n.id);
    c.addEventListener("click", () => selectHost(n.id));
    const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.setAttribute("x", p.x); t.setAttribute("y", p.y - r - 6);
    t.setAttribute("text-anchor", "middle"); t.setAttribute("class", "node-label");
    t.textContent = n.id;
    g.appendChild(c); g.appendChild(t);
    svg.appendChild(g);
  }
  canvas.appendChild(svg);
}

function layout(nodes, W, H) {
  const pos = new Map();
  const n = nodes.length;
  // deterministic ring layout by host address (gateways/infra first via ip sort)
  const sorted = [...nodes].sort((a, b) => (a.id > b.id ? 1 : -1));
  const cx = W / 2, cy = H / 2;
  const R = Math.min(W, H) * 0.36;
  sorted.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
    pos.set(node.id, { x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) });
  });
  return pos;
}

function selectHost(hostId) {
  const sel = $("explain-host");
  if (sel && [...sel.options].some((o) => o.value === hostId)) sel.value = hostId;
  showScreen("explain");
}

/* ------------------------------ war room -------------------------------- */
function renderForecast(f) {
  if (!f) return;
  if (f.model_available === false) {
    $("risk").textContent = "—";
    $("risk-band").textContent = f.reason || "model unavailable";
    $("forecast-ribbon").innerHTML = "";
    $("stage-path").innerHTML = "";
    $("forecast-meta").textContent = "";
    return;
  }
  const cur = f.current || {};
  $("risk").textContent = cur.risk != null ? pct(cur.risk) : "—";
  const band = cur.risk != null ? bandFor(cur.risk) : "—";
  $("risk-band").textContent = band;
  $("risk-band").className = `band band-${band.toLowerCase()}`;
  $("conf-bar").style.width = `${Math.round((f.confidence ?? 0) * 100)}%`;
  $("conf-val").textContent = f.confidence != null ? `${Math.round(f.confidence * 100)}%` : "—";
  $("ood").textContent = f.ood_flag ? "HIGH" : "LOW";
  $("ood").className = `ood ${f.ood_flag ? "ood-high" : "ood-low"}`;
  $("forecast-meta").textContent = `k=${f.k} · ${f.latency_ms ?? "—"}ms · windows=${f.observation_windows ?? "—"}`;
  renderRibbon($("forecast-ribbon"), f.steps);
  renderStagePath(f.steps);
  renderLoop(f);
}

function bandFor(r) {
  if (r < 0.25) return "LOW";
  if (r < 0.5) return "MEDIUM";
  if (r < 0.75) return "HIGH";
  return "CRITICAL";
}

function renderRibbon(el, steps) {
  if (!steps || !steps.length) { el.innerHTML = ""; return; }
  el.innerHTML = steps.map((s) => `
    <div class="ribbon-step">
      <div class="ribbon-bar"><div class="ribbon-fill" style="width:${Math.round((s.risk || 0) * 100)}%"></div></div>
      <div class="ribbon-meta"><b>+${s.step}</b> ${pct(s.risk)}</div>
      <div class="ribbon-stage st${s.stage_id}">${esc(s.stage_short || STAGE_NAMES[s.stage_id] || "?")}</div>
    </div>`).join("");
}

function renderStagePath(steps) {
  const el = $("stage-path");
  if (!steps || !steps.length) { el.innerHTML = ""; return; }
  const path = steps.map((s) => `<span class="path-node st${s.stage_id}">${esc(s.stage_short || "?")}</span>`).join('<span class="path-arrow">→</span>');
  el.innerHTML = `<div class="stage-track">${path}</div>`;
}

function renderLoop(f) {
  const order = ["observe", "forecast", "simulate", "recommend", "replan"];
  const idx = f && f.steps && f.steps.length ? 1 : 0;
  document.querySelectorAll(".lp-step").forEach((el, i) => {
    el.classList.toggle("active", i <= idx);
  });
}

function renderState(st) {
  if (!st) return;
  state.state = st;
  const nodes = (st.nodes || []).map((n) => ({ ...n, stage: st.dominant_stage }));
  renderNetwork($("network"), nodes, st.edges || []);
  $("net-stats").textContent = `${nodes.length} nodes · ${(st.edges || []).length} edges`;
  $("event-count").textContent = `${st.event_count ?? 0} events`;
}

function renderDefence(cf) {
  if (!cf) return;
  const rec = cf.recommended, base = cf.baseline || {};
  $("d-gravity").textContent = state.gravity?.critical_asset
    ? `${state.gravity.critical_asset.host} (${state.gravity.critical_asset.attack_gravity})`
    : "run GRAVITY";
  $("d-asset").textContent = state.gravity?.critical_asset?.host || "—";
  if (rec) {
    $("d-action").textContent = `${rec.action_label}${rec.host ? ` · ${rec.host}` : rec.port ? ` · ${rec.port}` : ""}`;
    $("d-after").textContent = `${pct(rec.future_risk)} (${rec.band})`;
    $("d-reduction").textContent = `−${pct(rec.risk_reduction)}`;
  }
  $("d-disclaimer").textContent = cf.disclaimer || "";
  $("cf-results").innerHTML = (cf.interventions || []).slice(0, 8).map((r) => `
    <div class="cf-row">
      <span class="cf-name">${esc(r.action_label)}${r.host ? ` · ${esc(r.host)}` : ""}${r.port ? ` · ${esc(r.port)}` : ""}</span>
      <span class="cf-risk band-${r.band.toLowerCase()}">${pct(r.future_risk)}</span>
      <span class="cf-delta">${r.risk_reduction > 0 ? "−" : "+"}${pct(Math.abs(r.risk_reduction))}</span>
    </div>`).join("");
}

async function runCounterfactual() {
  try {
    setBusy($("btn-cf"), true);
    const cf = await postJSON("/api/counterfactual/simulate", { action: "auto", k: 6 });
    renderDefence(cf);
    pulseLoop("simulate"); pulseLoop("recommend");
  } catch (e) { flashError(e); }
  finally { setBusy($("btn-cf"), false); }
}

async function runGravity() {
  try {
    setBusy($("btn-gravity"), true);
    const g = await postJSON("/api/counterfactual/attack-gravity", { k: 6 });
    state.gravity = g;
    const max = Math.max(...g.gravity.map((x) => x.attack_gravity), 0);
    renderNetwork($("network"), (state.state?.nodes || []).map((n) => ({
      ...n, gravity: g.gravity.find((x) => x.host === n.id)?.attack_gravity ?? 0,
    })), state.state?.edges || [], { gravity: true, gravityMax: max });
    renderDefence({ recommended: null, baseline: {}, interventions: [], disclaimer: g.disclaimer });
    $("d-gravity").textContent = g.critical_asset ? `${g.critical_asset.host} (${g.critical_asset.attack_gravity})` : "—";
    $("d-asset").textContent = g.critical_asset?.host || "—";
  } catch (e) { flashError(e); }
  finally { setBusy($("btn-gravity"), false); }
}

/* ------------------------------ timeline -------------------------------- */
let timelineItems = [];
function pushTimeline(events) {
  if (state.paused || !events?.length) return;
  timelineItems = [...events.slice(-40), ...timelineItems].slice(0, 60);
  $("timeline").innerHTML = timelineItems.map((e) => `
    <div class="tl-row">
      <span class="tl-ts">${esc(new Date(e.timestamp).toLocaleTimeString())}</span>
      <span class="tl-flow">${esc(e.src)} → ${esc(e.dst)}${e.dst_port ? `:${esc(e.dst_port)}` : ""}</span>
      <span class="tl-label ${String(e.label).toUpperCase() !== "BENIGN" ? "tl-attack" : ""}">${esc(e.label)}</span>
    </div>`).join("");
}

/* ---------------------------- scenario lab ------------------------------ */
async function loadScenarios() {
  try {
    const data = await getJSON("/api/scenarios");
    $("scenario-list").innerHTML = data.scenarios.map((s) => `
      <div class="scenario-card">
        <div><b>${esc(s.name)}</b><div class="mini">${esc(s.description)}</div></div>
        <button class="btn primary" data-scenario="${esc(s.id)}">START</button>
      </div>`).join("");
    document.querySelectorAll("[data-scenario]").forEach((b) =>
      b.addEventListener("click", () => startScenario(b.dataset.scenario)));
    $("lab-status").textContent = data.status?.running ? `running ${data.status.scenario_id}` : "idle";
  } catch (e) { flashError(e); }
}

async function startScenario(id) {
  try {
    const interval = parseFloat($("lab-interval").value) || 1.5;
    const res = await postJSON("/api/scenarios/start", { scenario_id: id, interval });
    $("lab-current").textContent = id;
    $("lab-run").textContent = res.run_id || "—";
    $("lab-status").textContent = "running";
    $("lab-log").innerHTML = "";
    pulseLoop("observe");
  } catch (e) { flashError(e); }
}

function handleScenarioMsg(msg) {
  if (msg.event === "started") {
    $("lab-current").textContent = msg.scenario_id;
    $("lab-run").textContent = msg.run_id;
    $("lab-status").textContent = "running";
    labLog(`▶ scenario started: ${msg.scenario_id}`);
  } else if (msg.event === "tick") {
    $("lab-tick").textContent = msg.tick;
    if (msg.forecast) { state.forecast = msg.forecast; renderLabForecast(msg.forecast); renderForecast(msg.forecast); }
    labLog(`tick ${msg.tick} · ${msg.events} events`);
    pulseLoop("observe");
    if (msg.forecast) pulseLoop("forecast");
  } else if (msg.event === "finished") {
    $("lab-status").textContent = "finished";
    labLog("■ scenario finished");
    pulseLoop("replan");
  }
}

function renderLabForecast(f) {
  $("lab-risk").textContent = f.horizon?.risk != null ? pct(f.horizon.risk) : "—";
  renderRibbon($("lab-steps"), f.steps || []);
}

function labLog(line) {
  const el = $("lab-log");
  el.innerHTML = `<div class="tl-row"><span class="tl-ts">${new Date().toLocaleTimeString()}</span><span>${esc(line)}</span></div>` + el.innerHTML.slice(0, 4000);
}

/* -------------------------------- replay -------------------------------- */
async function loadReplayFiles() {
  try {
    const data = await getJSON("/api/replay/files");
    state.replay = data;
    $("replay-files").innerHTML = data.files.length
      ? data.files.map((f) => `<div class="file-row"><span>${esc(f)}</span><button class="btn tiny" data-file="${esc(f)}">LOAD</button></div>`).join("")
      : '<div class="empty">No replay files found in data/replay/.</div>';
    document.querySelectorAll("[data-file]").forEach((b) =>
      b.addEventListener("click", () => loadReplay(b.dataset.file)));
  } catch (e) { flashError(e); }
}

async function loadReplay(filename) {
  try {
    const res = await postJSON("/api/replay/load", { filename });
    state.replay.loaded = filename;
    state.replay.buffer = res.events;
    const scrub = $("scrub");
    scrub.max = res.events; scrub.value = 0;
    $("scrub-pos").textContent = `0 / ${res.events}`;
    $("replay-note").textContent = `Loaded ${filename} (${res.events} events). Scrub the timeline.`;
  } catch (e) { flashError(e); }
}

async function seekReplay() {
  const idx = parseInt($("scrub").value, 10);
  try {
    const res = await postJSON("/api/replay/seek", { index: idx });
    $("scrub-pos").textContent = `${res.index} / ${res.total}`;
    const nodes = (res.state?.nodes || []).map((n) => ({ ...n, stage: res.state?.dominant_stage }));
    renderNetwork($("replay-network"), nodes, res.state?.edges || []);
    if (res.forecast?.steps) {
      $("replay-risk").textContent = res.forecast.horizon?.risk != null ? pct(res.forecast.horizon.risk) : "—";
      renderRibbon($("replay-compare"), res.forecast.steps);
    } else {
      $("replay-risk").textContent = "—";
      $("replay-compare").innerHTML = res.forecast?.reason === "model_checkpoint_missing"
        ? '<div class="empty">Model checkpoint missing — load models/cybermind_final.pt</div>' : "";
    }
  } catch (e) { flashError(e); }
}

$("scrub").addEventListener("input", () => { $("scrub-pos").textContent = `${$("scrub").value} / ${state.replay.buffer}`; });
$("scrub").addEventListener("change", seekReplay);

$("replay-upload").addEventListener("change", async (ev) => {
  const file = ev.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const r = await fetch("/api/telemetry/upload", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    await loadReplayFiles();
  } catch (e) { flashError(e); }
});

/* -------------------------------- explain ------------------------------- */
async function refreshExplainHosts() {
  const st = state.state;
  const sel = $("explain-host");
  if (!st?.nodes?.length) { sel.innerHTML = '<option value="">— no state yet —</option>'; return; }
  sel.innerHTML = st.nodes.map((n) => `<option value="${esc(n.id)}">${esc(n.id)}</option>`).join("");
}

async function runExplain() {
  const st = state.state;
  if (!st?.nodes?.length) { $("explain-out").innerHTML = '<div class="empty">No graph state — run a scenario first.</div>'; return; }
  const hostId = $("explain-host").value;
  const idx = st.nodes.findIndex((n) => n.id === hostId);
  if (idx < 0) return;
  try {
    setBusy($("btn-explain"), true);
    const res = await postJSON(`/api/explain/${idx}`, {});
    $("explain-out").innerHTML = res.attributions.map((a) => `
      <div class="attr-row">
        <span class="attr-name">${esc(a.feature)}</span>
        <div class="attr-bar"><div style="width:${attrWidth(a.attribution, res.attributions)}%"></div></div>
        <span class="attr-val">${a.attribution.toFixed(4)}</span>
      </div>`).join("");
    const top = res.attributions.slice(0, 3).map((a) => featureNarrative(a.feature)).join("; ");
    $("explain-narrative").innerHTML =
      `<b>${esc(hostId)}</b>: strongest model-attributed evidence — ${top}. ` +
      `These features drove the predicted transition; simulate an intervention in the War Room to see which future branch collapses.`;
    $("top-evidence").innerHTML = res.attributions.slice(0, 3).map((a) => `
      <div class="cf-row"><span class="cf-name">${esc(a.feature)}</span><span class="cf-risk">${a.attribution.toFixed(3)}</span></div>`).join("");
  } catch (e) { flashError(e); }
  finally { setBusy($("btn-explain"), false); }
}

function attrWidth(v, all) {
  const max = Math.max(...all.map((a) => a.attribution), 1e-9);
  return Math.max(4, Math.round((v / max) * 100));
}
function featureNarrative(f) {
  const map = {
    flow_count: "unusual number of flows",
    unique_peer_count: "spike in distinct peers contacted",
    unique_dst_port_count: "wide port sweep",
    bytes_total: "abnormal byte volume",
    anomaly_proxy: "combined volume+peer pressure",
    packets_total: "abnormal packet volume",
    mean_iat: "irregular inter-arrival timing",
    activity_rate: "burst of activity in the window",
    tcp_ratio: "TCP-heavy traffic mix",
    udp_ratio: "UDP-heavy traffic mix",
  };
  return map[f] || f.replace(/_/g, " ");
}
$("btn-explain").addEventListener("click", runExplain);

/* ------------------------------ experiments ----------------------------- */
async function loadRuns() {
  try {
    const data = await getJSON("/api/experiments");
    $("runs-list").innerHTML = data.runs.length
      ? `<table class="runs-table"><tr><th>RUN</th><th>SCENARIO</th><th>MODEL</th><th>STARTED</th><th>PREDICTIONS</th></tr>` +
        data.runs.map((r) => `
          <tr class="run-row" data-run="${esc(r.run_id)}">
            <td>${esc(r.run_id)}</td><td>${esc(r.scenario_id || "—")}</td>
            <td>${esc(r.model_version || "—")}</td>
            <td>${r.start_time ? new Date(r.start_time * 1000).toLocaleString() : "—"}</td>
            <td>${r.prediction_count}</td>
          </tr>`).join("") + "</table>"
      : '<div class="empty">No runs yet — start a scenario.</div>';
    document.querySelectorAll(".run-row").forEach((row) =>
      row.addEventListener("click", () => loadRun(row.dataset.run)));
  } catch (e) { flashError(e); }
}

async function loadRun(runId) {
  try {
    const r = await getJSON(`/api/experiments/${runId}`);
    const preds = (r.predictions || []).slice(-20);
    $("run-detail").innerHTML = `
      <div class="kv"><span>RUN</span><span>${esc(r.run_id)}</span></div>
      <div class="kv"><span>SCENARIO</span><span>${esc(r.scenario_id || "—")}</span></div>
      <div class="kv"><span>MODEL VERSION</span><span>${esc(r.model_version || "—")}</span></div>
      <div class="kv"><span>SOURCE</span><span>${esc(r.source || "—")}</span></div>
      <div class="kv"><span>INTERVENTIONS</span><span>${(r.interventions || []).length}</span></div>
      <div class="mini" style="margin-top:10px">last predictions:</div>
      ${preds.map((p) => `<div class="cf-row"><span class="cf-name">${p.tick != null ? `tick ${p.tick}` : new Date(p.timestamp * 1000).toLocaleTimeString()}</span>
        <span class="cf-risk">${p.risk != null ? pct(p.risk) : `· ${p.events ?? ""} events`}</span></div>`).join("")}`;
  } catch (e) { flashError(e); }
}

/* -------------------------------- system -------------------------------- */
async function loadSystem() {
  try {
    const [h, files] = await Promise.all([getJSON("/api/health"), getJSON("/api/replay/files")]);
    const m = h.model;
    $("sys-model").innerHTML = `
      <div class="kv"><span>STATUS</span><span class="${m.available ? "ok" : "warn"}">${esc(m.status)}</span></div>
      <div class="kv"><span>VERSION</span><span>${esc(m.version)}</span></div>
      <div class="kv"><span>DEVICE</span><span>${esc(m.device)}</span></div>
      <div class="kv"><span>CHECKPOINT</span><span class="mono">${esc(m.checkpoint)}</span></div>
      ${m.load_error ? `<div class="kv"><span>LOAD ERROR</span><span class="warn mono">${esc(m.load_error)}</span></div>` : ""}`;
    $("sys-pipeline").innerHTML = `
      <div class="kv"><span>TELEMETRY EVENTS</span><span>${h.telemetry_events}</span></div>
      <div class="kv"><span>STATE WINDOWS</span><span>${h.state_windows}</span></div>
      <div class="kv"><span>SCENARIO</span><span>${esc(h.scenario?.running ? h.scenario.scenario_id : "idle")}</span></div>`;
    $("sys-replay").innerHTML = files.files.map((f) => `<div class="file-row mini"><span>${esc(f)}</span></div>`).join("") || '<div class="empty">empty</div>';
  } catch (e) { flashError(e); }
}

/* ------------------------------- helpers -------------------------------- */
function setBusy(btn, busy) { if (btn) { btn.disabled = busy; btn.classList.toggle("busy", busy); } }
function flashError(e) { console.error(e); labLog(`⚠ ${String(e.message || e).slice(0, 140)}`); }
function pulseLoop(step) {
  const el = document.querySelector(`.lp-step[data-step="${step}"]`);
  if (el) { el.classList.add("pulse"); setTimeout(() => el.classList.remove("pulse"), 700); }
}

/* ------------------------------- polling -------------------------------- */
async function poll() {
  if (state.paused) return;
  try {
    const [h, st, tl] = await Promise.all([
      getJSON("/api/health"), getJSON("/api/state/current"), getJSON("/api/timeline?limit=40"),
    ]);
    setConn(true);
    $("model-badge").textContent = `MODEL ${h.model.available ? h.model.version : "UNAVAILABLE"}`;
    $("model-badge").className = `model-badge ${h.model.available ? "ok" : "warn"}`;
    renderState(st);
    if (state.screen === "warroom" && !state.forecast && h.state_windows > 0) {
      const f = await getJSON("/api/forecast");
      state.forecast = f; renderForecast(f);
    }
    if (!state.paused) pushTimeline(tl.events || []);
  } catch { setConn(false); }
}

/* --------------------------------- wire --------------------------------- */
$("btn-cf").addEventListener("click", runCounterfactual);
$("btn-gravity").addEventListener("click", runGravity);
$("pause-feed").addEventListener("change", (e) => { state.paused = e.target.checked; });
$("lab-interval").addEventListener("input", (e) => { $("lab-interval-val").textContent = `${e.target.value}s`; });
$("lab-stop").addEventListener("click", () => postJSON("/api/scenarios/stop", { scenario_id: "current" }).then(loadScenarios).catch(flashError));
$("lab-reset").addEventListener("click", async () => {
  try {
    await postJSON("/api/scenarios/reset", {});
    state.forecast = null; state.gravity = null;
    ["risk", "d-gravity", "d-asset", "d-action", "d-after", "d-reduction"].forEach((id) => { $(id).textContent = "—"; });
    ["cf-results", "forecast-ribbon", "stage-path", "lab-steps"].forEach((id) => { $(id).innerHTML = ""; });
    renderNetwork($("network"), [], []);
    labLog("state reset");
  } catch (e) { flashError(e); }
});

connectWS();
poll();
setInterval(poll, 2500);
