"""Grounded offline case questions; no external API or generated claims."""
from __future__ import annotations

import re


def _flow_cues(report):
    flows = report.get("observed_flows") or []
    return [row for row in flows if row.get("review_flag")]


def answer_case_question(question: str, report: dict, observed=None) -> dict:
    """Answer common analyst questions using only cited case fields."""
    query = question.strip().lower()
    if not query:
        return {"answer": "Enter a question about risk, stages, flows, hosts, or provenance.",
                "evidence": []}
    forecast = report.get("forecast") or []
    lineage = report.get("lineage") or {}
    flagged = _flow_cues(report)
    terms = set(re.findall(r"[a-z0-9]+", query))

    if terms & {'host', 'hosts'} and terms & {'flow', 'flows'}:
        hosts = answer_case_question('hosts changed', report, observed)
        flows = answer_case_question('flagged flows', report, observed)
        return {'answer': hosts['answer'] + ' ' + flows['answer'],
                'evidence': hosts['evidence'] + flows['evidence']}

    if terms & {"risk", "probability", "forecast", "next", "infiltration"}:
        future = [row for row in forecast if int(row.get("step", 0)) > 0]
        if not future:
            return {"answer": "This case has no future-risk rows.", "evidence": ["forecast"]}
        points = ", ".join(f"+{row['step']}: {float(row['risk']):.1%}" for row in future)
        return {"answer": f"Forecast network infiltration risk: {points}. These are model outputs, not observed outcomes.",
                "evidence": [f"forecast[{i}].risk" for i, row in enumerate(forecast) if row in future]}

    if terms & {"stage", "stages", "attack", "mitre", "chain"}:
        future = [row for row in forecast if int(row.get("step", 0)) > 0]
        if not future:
            return {"answer": "This case has no future-stage rows.", "evidence": ["forecast"]}
        points = ", ".join(f"+{row['step']}: {row.get('reported_stage', row.get('stage', 'Unknown'))}"
                           for row in future)
        return {"answer": f"Displayed stage annotations: {points}. Reported stages may include telemetry rules or abstention; they are not verified attack ground truth.",
                "evidence": [f"forecast[{i}].reported_stage" for i, row in enumerate(forecast) if row in future]}

    if terms & {"flow", "flows", "flag", "flagged", "port", "packet", "scan", "why"}:
        if not flagged:
            return {"answer": "No displayed flow has a telemetry review flag. This does not establish benign traffic; network-level risk is separate.",
                    "evidence": ["observed_flows"]}
        shown = flagged[:5]
        parts = [f"{row.get('src', '?')}:{row.get('src_port', '?')} → {row.get('dst', '?')}:{row.get('dst_port', '?')} ({row.get('review_signal', 'review')})"
                 for row in shown]
        return {"answer": "Flows for analyst review: " + "; ".join(parts) +
                ". These flags are observed telemetry cues, not per-flow model probabilities or causal attributions.",
                "evidence": [f"observed_flows[{(report.get('observed_flows') or []).index(row)}]" for row in shown]}

    if terms & {"host", "hosts", "changed", "change", "new", "network"}:
        if observed and len(observed) >= 2:
            prior, latest = observed[-2], observed[-1]
            added = sorted(set(latest.node_ids) - set(prior.node_ids))
            removed = sorted(set(prior.node_ids) - set(latest.node_ids))
            return {"answer": f"From the prior observed window: {len(added)} new host(s) {added[:10]}; {len(removed)} no-longer-observed host(s) {removed[:10]}. This compares capture windows, not attack attribution.",
                    "evidence": ["observed_states[-2].node_ids", "observed_states[-1].node_ids"]}
        return {"answer": "Host changes require at least two observed graph windows in the active session.",
                "evidence": []}

    if terms & {"source", "checkpoint", "file", "provenance", "hash", "where"}:
        return {"answer": f"Source: {lineage.get('dataset', 'unavailable')}. Checkpoint SHA-256: {lineage.get('checkpoint_sha256', 'unavailable')}. Input SHA-256: {lineage.get('dataset_sha256', 'unavailable')}.",
                "evidence": ["lineage.dataset", "lineage.checkpoint_sha256", "lineage.dataset_sha256"]}

    return {"answer": "I can answer questions about future risk, displayed stages, flagged flows, host changes, and file provenance. Each answer is tied to this case's evidence; no cloud model is used.",
            "evidence": []}



def compare_case_reports(first: dict, second: dict) -> list[dict]:
    """Compare saved evidence without re-scoring or changing either case."""
    def read(report):
        future = [row for row in report.get('forecast', []) if int(row.get('step', 0)) > 0]
        final = future[-1] if future else {}
        return {
            'input_sha256': (report.get('lineage') or {}).get('dataset_sha256', 'unavailable'),
            'final_risk': final.get('risk'),
            'reported_stage': final.get('reported_stage', final.get('stage', 'unavailable')),
            'review_flagged_flows': sum(bool(row.get('review_flag'))
                                        for row in report.get('observed_flows', [])),
            'replay_position': (report.get('lineage') or {}).get('sequence_index', 'unavailable'),
        }
    left, right = read(first), read(second)
    return [{'measure': label, 'first_case': left[label], 'second_case': right[label]}
            for label in left]
