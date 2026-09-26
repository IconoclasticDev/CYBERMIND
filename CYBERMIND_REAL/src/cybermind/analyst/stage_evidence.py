"""Conservative, label-free stage evidence for analyst review.

These rules do not change model probabilities and are not trained-stage claims.
They expose observable indicators and abstain when evidence is insufficient.
"""
from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_address, ip_network
from statistics import median

import torch

from cybermind.data.graph_builder import EDGE_FEATURE_NAMES, NODE_FEATURE_NAMES
from cybermind.data.normalization import FeatureNormalizer
from cybermind.data.stages import STAGE_NAMES


_INTERNAL = tuple(ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
_PROTECTED_STAGES = {3, 4, 5}


def _internal(host):
    try:
        value = ip_address(str(host))
    except ValueError:
        return None
    return value.version == 4 and any(value in network for network in _INTERNAL)


def _raw(state, normalizer):
    if normalizer is None:
        return state.x.float(), state.edge_attr.float()
    return (normalizer.inverse_transform(state.x, "node"),
            normalizer.inverse_transform(state.edge_attr, "edge"))


def _blank(stage_id, limitation):
    return {
        "stage_id": stage_id,
        "stage": STAGE_NAMES[stage_id],
        "status": "unsupported / insufficient evidence",
        "basis": "abstention",
        "hosts": [],
        "indicators": [],
        "limitation": limitation,
    }


def analyze_stage_evidence(states, normalization, model_risk, risk_threshold=0.5):
    """Return transparent stage 3–5 indicators from observed states only.

    Rules are gated by the learned infiltration risk but never alter that risk.
    Host identifiers and supporting measurements are returned for auditability.
    """
    if not states:
        raise ValueError("At least one observed graph state is required")
    if not 0 <= float(model_risk) <= 1:
        raise ValueError("model_risk must be a probability")
    normalizer = FeatureNormalizer(normalization) if normalization is not None else None
    node_index = {name: index for index, name in enumerate(NODE_FEATURE_NAMES)}
    edge_index = {name: index for index, name in enumerate(EDGE_FEATURE_NAMES)}
    history = []
    peer_history = defaultdict(set)
    external_windows = defaultdict(lambda: defaultdict(int))
    outbound_history = defaultdict(list)

    for state in states:
        raw_nodes, raw_edges = _raw(state, normalizer)
        outgoing = defaultdict(list)
        incoming_bytes = defaultdict(float)
        for position, (source, destination) in enumerate(state.edge_index.detach().cpu().t().tolist()):
            if source >= len(state.node_ids) or destination >= len(state.node_ids):
                continue
            src, dst = str(state.node_ids[source]), str(state.node_ids[destination])
            values = raw_edges[position]
            item = {
                "peer": dst,
                "bytes": max(0.0, float(values[edge_index["bytes"]])),
                "packets": max(0.0, float(values[edge_index["packets"]])),
                "port": max(0.0, float(values[edge_index["port"]])),
            }
            outgoing[src].append(item)
            incoming_bytes[dst] += item["bytes"]
            if _internal(dst) is False:
                external_windows[src][dst] += 1
        history.append((state, raw_nodes, outgoing, incoming_bytes))

    latest_state, latest_nodes, latest_outgoing, latest_incoming = history[-1]
    previous_peers = defaultdict(set)
    for state, _, outgoing, _ in history[:-1]:
        for host, edges in outgoing.items():
            previous_peers[host].update(edge["peer"] for edge in edges)
            outbound_history[host].append(sum(edge["bytes"] for edge in edges))

    evidence = {
        3: _blank(3, "No verified new internal movement pattern passed the conservative rule."),
        4: _blank(4, "The stage-4 head had no training support; no repeated external peer passed the evidence rule."),
        5: _blank(5, "No externally directed volume surge passed the conservative rule."),
    }
    if float(model_risk) < risk_threshold:
        for record in evidence.values():
            record["limitation"] = f"Learned risk {model_risk:.3f} is below the {risk_threshold:.3f} evidence gate."
        return [evidence[key] for key in sorted(evidence)]

    lateral, c2, exfil = [], [], []
    total_windows = len(history)
    for position, host in enumerate(map(str, latest_state.node_ids)):
        outgoing = latest_outgoing.get(host, [])
        peers = {edge["peer"] for edge in outgoing}
        new_internal = sorted(peer for peer in peers - previous_peers[host] if _internal(peer) is True)
        unique_peers = max(0.0, float(latest_nodes[position, node_index["unique_peer_count"]]))
        anomaly = float(latest_nodes[position, node_index["anomaly_proxy"]])
        if _internal(host) is True and len(new_internal) >= 2 and unique_peers >= 3 and anomaly >= 0.5:
            lateral.append({"host": host, "new_internal_peers": new_internal,
                            "unique_peers": round(unique_peers, 3), "anomaly_proxy": round(anomaly, 3)})

        repeated = sorted(peer for peer, count in external_windows[host].items()
                          if count >= max(2, (total_windows + 1) // 2))
        if repeated:
            c2.append({"host": host, "repeated_external_peers": repeated,
                       "observed_windows": total_windows})

        external_bytes = sum(edge["bytes"] for edge in outgoing if _internal(edge["peer"]) is False)
        inbound = latest_incoming.get(host, 0.0)
        prior = outbound_history.get(host, [])
        baseline = median(prior) if prior else 0.0
        external_peers = sorted(edge["peer"] for edge in outgoing if _internal(edge["peer"]) is False)
        if (external_peers and external_bytes >= 1_000_000 and
                external_bytes >= 3 * max(baseline, 1.0) and external_bytes >= 3 * max(inbound, 1.0)):
            exfil.append({"host": host, "external_peers": external_peers,
                          "outbound_external_bytes": round(external_bytes, 3),
                          "prior_median_outbound_bytes": round(baseline, 3),
                          "outbound_inbound_ratio": round(external_bytes / max(inbound, 1.0), 3)})

    for stage_id, matches, indicators in (
        (3, lateral, ["new internal peers", "peer fan-out", "node anomaly proxy"]),
        (4, c2, ["repeated external peer", "learned infiltration-risk gate"]),
        (5, exfil, ["external outbound volume surge", "outbound/inbound ratio", "learned infiltration-risk gate"]),
    ):
        if matches:
            evidence[stage_id] = {
                "stage_id": stage_id,
                "stage": STAGE_NAMES[stage_id],
                "status": "rule-supported evidence",
                "basis": "observed telemetry rule + learned risk gate",
                "hosts": matches,
                "indicators": indicators,
                "limitation": "Analyst evidence only; not a trained stage prediction or causal conclusion.",
            }
    return [evidence[key] for key in sorted(evidence)]


def annotate_forecast_stage_coverage(rows, evidence):
    """Preserve raw model output and add a coverage-aware reported stage."""
    support = {int(record["stage_id"]): record["status"] == "rule-supported evidence"
               for record in evidence}
    annotated = []
    for source in rows:
        row = dict(source)
        stage_id = int(row["stage_id"])
        row["model_stage"] = row["stage"]
        if stage_id in _PROTECTED_STAGES:
            if support.get(stage_id, False):
                row["reported_stage"] = row["stage"]
                row["evidence_basis"] = "rule-supported; learned stage class unsupported"
            else:
                row["reported_stage"] = STAGE_NAMES[6]
                row["evidence_basis"] = "abstained: insufficient supported evidence"
        elif stage_id == 6:
            row["reported_stage"] = row["stage"]
            row["evidence_basis"] = "model abstention"
        else:
            row["reported_stage"] = row["stage"]
            row["evidence_basis"] = "learned stage with training support"
        annotated.append(row)
    return annotated
