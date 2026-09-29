const escapeHtml = value => String(value ?? '—').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const fmtRisk = value => typeof value === 'number' && Number.isFinite(value) ? (value * 100).toFixed(1) + '%' : '—';
const fmtTime = value => typeof value === 'number' && Number.isFinite(value) ? new Date(value * 1000).toLocaleString() : '—';
const fmtValue = value => value === null || value === undefined ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const row = (label, value) => `<tr><th scope="row">${escapeHtml(label)}</th><td>${escapeHtml(fmtValue(value))}</td></tr>`;
const table = (head, body) => `<div class="table-wrap"><table><thead><tr>${head.map(item => `<th scope="col">${escapeHtml(item)}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></div>`;

export function caseReportFilename(filename) {
  const stem = String(filename || 'cybermind_case').replace(/\.cmcase$/i, '').replace(/[^a-zA-Z0-9._-]+/g, '_').replace(/^\.+|\.+$/g, '').slice(0, 80) || 'cybermind_case';
  return `${stem}_readable_report.html`;
}

export function renderCaseReportHtml(report, filename, exportedAt = new Date()) {
  const forecast = Array.isArray(report.forecast) ? report.forecast : [];
  const evidence = Array.isArray(report.stage_evidence) ? report.stage_evidence : [];
  const flows = Array.isArray(report.observed_flows) ? report.observed_flows : [];
  const lineage = report.lineage && typeof report.lineage === 'object' ? report.lineage : {};
  const provenanceRows = Object.entries(lineage).map(([key, value]) => row(key.replaceAll('_', ' '), value)).join('');
  const forecastRows = forecast.map(item => `<tr><td>${escapeHtml(item.horizon || (item.step === 0 ? 'Now' : '+' + item.step))}</td><td>${escapeHtml(item.reported_stage || item.stage || 'Unknown')}</td><td>${escapeHtml(fmtRisk(item.risk))}</td><td>${escapeHtml(fmtTime(item.timestamp))}</td></tr>`).join('');
  const evidenceRows = evidence.map(item => `<tr><td>${escapeHtml(item.stage)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.basis)}</td><td>${escapeHtml(fmtValue(item.hosts))}</td><td>${escapeHtml(item.limitation)}</td></tr>`).join('');
  const flowRows = flows.map(item => `<tr><td>${escapeHtml(item.src)}:${escapeHtml(item.src_port)}</td><td>${escapeHtml(item.dst)}:${escapeHtml(item.dst_port)}</td><td>${escapeHtml(item.protocol)}</td><td>${escapeHtml(item.review_signal || '—')}</td></tr>`).join('');
  const optional = [['Input-range assessment', report.input_shift], ['Isolation comparisons', report.interventions], ['Model explanation', report.explanation]]
    .filter(([, value]) => value !== null && value !== undefined && !(Array.isArray(value) && value.length === 0))
    .map(([title, value]) => `<section><h2>${escapeHtml(title)}</h2><pre>${escapeHtml(JSON.stringify(value, null, 2))}</pre></section>`).join('');
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>CYBERMIND readable case report</title><style>
:root{font-family:Arial,Helvetica,sans-serif;color:#172435;background:#eef2f5}*{box-sizing:border-box}body{max-width:1050px;margin:0 auto;padding:32px}header,section,footer{background:#fff;border:1px solid #dce4e9;border-radius:10px;padding:24px;margin-bottom:18px}header{border-top:6px solid #0b8f8a}h1{margin:0 0 6px;font-size:26px}h2{font-size:17px;margin:0 0 14px;color:#126d70}p{line-height:1.5}.muted,small{color:#566b78}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}.summary div{background:#edf7f6;border:1px solid #cde4e1;border-radius:7px;padding:12px}.summary span,.summary strong{display:block}.summary span{font-size:11px;color:#4e6571}.summary strong{font-size:20px;margin-top:5px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #dce4e9;overflow-wrap:anywhere}thead th{background:#eef5f6;color:#345f68}tbody th{width:28%;color:#4e6571}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f8;padding:14px;border-radius:6px;font-size:11px}details{margin-top:18px}summary{cursor:pointer;font-weight:bold}.warning{color:#8b491e;background:#fff5e9;padding:10px;border-radius:6px}footer{font-size:11px;color:#566b78}@media print{:root{background:#fff}body{padding:0;max-width:none}header,section,footer{break-inside:avoid;box-shadow:none;border-color:#ccd6dc}pre,.table-wrap{overflow:visible}details:not([open]){display:none}}@media(max-width:700px){body{padding:12px}.summary{grid-template-columns:repeat(2,1fr)}}
</style></head><body><header><small>CYBERMIND · OFFLINE ANALYST CASE</small><h1>Decrypted case report</h1><p>${escapeHtml(filename || 'Saved CYBERMIND case')}</p><p class="muted">${escapeHtml(report.interpretation || 'Model forecast for analyst review.')}</p><p class="warning">This downloaded copy is readable and unencrypted. Handle it as sensitive case evidence. Predictions are decision support, not verified outcomes.</p><div class="summary"><div><span>Final-horizon risk</span><strong>${escapeHtml(fmtRisk(forecast.at(-1)?.risk))}</strong></div><div><span>Forecast windows</span><strong>${Math.max(0, forecast.length - 1)}</strong></div><div><span>Observed flow rows</span><strong>${flows.length}</strong></div><div><span>Evidence stages</span><strong>${evidence.length}</strong></div></div></header>
<section><h2>Forecast trajectory</h2>${forecast.length ? table(['Window','Stage','Risk','Time'], forecastRows) : '<p>No forecast rows were saved.</p>'}</section>
<section><h2>Stage evidence</h2>${evidence.length ? table(['Stage','Status','Basis','Hosts','Limitation'], evidenceRows) : '<p>No stage evidence was saved.</p>'}</section>
<section><h2>Observed flows (${flows.length})</h2>${flows.length ? table(['Source','Destination','Protocol','Signal'], flowRows) : '<p>No observed flow rows were saved.</p>'}</section>
<section><h2>Source and provenance</h2>${table(['Field','Value'], row('Report format', report.format) + provenanceRows + row('Rollout seed', report.seed) + row('Rollout draws', report.n_rollouts))}</section>${optional}
<section><details><summary>Complete decrypted source data</summary><pre>${escapeHtml(JSON.stringify(report, null, 2))}</pre></details></section><footer>Exported locally: ${escapeHtml(exportedAt.toLocaleString())}. This file has no network dependencies. Open it in a browser; use Print / Save as PDF for a PDF copy.</footer></body></html>`;
}

export function downloadReadableCaseReport(report, filename) {
  const html = renderCaseReportHtml(report, filename);
  const url = URL.createObjectURL(new Blob([html], {type:'text/html;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = caseReportFilename(filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
