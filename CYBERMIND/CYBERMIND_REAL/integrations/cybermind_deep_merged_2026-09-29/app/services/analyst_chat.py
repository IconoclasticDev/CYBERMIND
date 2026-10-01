"""Offline, read-only natural-language queries over the current app session.

The open-source scikit-learn model is fitted to CYBERMIND-specific utterances.
It only routes questions to bounded, deterministic data readers; it never
generates unsupported facts or turns a chat message into an action or SQL.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
import ipaddress
import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from cybermind.data.stages import STAGE_NAMES


TRAINING_UTTERANCES: dict[str, tuple[str, ...]] = {
    "summary": (
        "summarize the loaded data", "how many flows are loaded", "what is in this capture",
        "give me an overview of traffic", "how many attacks and benign events", "show dataset summary",
    ),
    "labels": (
        "which attack labels are present", "count events by attack type", "show stage distribution",
        "how many botnet flows", "what labels are in the data", "break down attack classes",
    ),
    "hosts": (
        "which hosts appear most often", "top source and destination IPs", "show busiest hosts",
        "what are the most active IP addresses", "rank hosts by flow count", "which machines are involved",
    ),
    "ports": (
        "which destination ports are most common", "top ports in the capture", "show port distribution",
        "what services are targeted", "count flows by destination port", "which port has most traffic",
    ),
    "protocols": (
        "which network protocols are present", "count flows by protocol", "show protocol distribution",
        "how many tcp flows", "how many udp flows", "what protocols are in this capture",
    ),
    "volume": (
        "how many bytes were transferred", "show total traffic volume", "what is the packet count",
        "how much network traffic is loaded", "count bytes and packets", "summarize transfer sizes",
    ),
    "recent": (
        "show recent events", "what happened most recently", "list latest flows",
        "show the last ten events", "what are the newest alerts", "display recent traffic",
    ),
    "forecast": (
        "what does the model forecast", "show predicted attack stage", "what is future risk",
        "summarize the next four windows", "what will happen next", "show rollout predictions",
    ),
    "provenance": (
        "where did this traffic come from", "show data provenance", "which source files were loaded",
        "is this synthetic or real data", "what dataset is currently loaded", "explain the data source",
    ),
    "model": (
        "which checkpoint is loaded", "is the model available", "show model status",
        "what device is inference using", "which model version is running", "tell me about best pt",
    ),
    "validation": (
        "what did validation find", "show local sandbox check", "is Strix available",
        "summarize the latest validation", "were the sandbox probes successful", "show validation evidence",
    ),
    "help": (
        "what can you do", "help me ask about data", "give me example questions",
        "what questions can I ask", "show chatbot capabilities", "how do I use this assistant",
    ),
}

EXAMPLES = [text for variants in TRAINING_UTTERANCES.values() for text in variants]
LABELS = [intent for intent, variants in TRAINING_UTTERANCES.items() for _ in variants]
INTENT_TERMS = {
    "summary": r"\b(summar|overview|loaded|capture|flow|traffic|dataset)\w*\b",
    "labels": r"\b(attack|label|stage|class|botnet|brute|benign|recon|exfil)\w*\b",
    "hosts": r"\b(host|ip|address|machine|endpoint)\w*\b",
    "ports": r"\b(port|service)\w*\b",
    "protocols": r"\b(protocol|tcp|udp|icmp)\w*\b",
    "volume": r"\b(byte|packet|volume|transfer)\w*\b",
    "recent": r"\b(recent|latest|last|newest|event|alert|flow)\w*\b",
    "forecast": r"\b(forecast|predict|future|risk|rollout|next)\w*\b",
    "provenance": r"\b(source|provenance|data|dataset|capture|synthetic|real)\w*\b",
    "model": r"\b(model|checkpoint|version|device|inference|best\.pt)\b",
    "validation": r"\b(validat|sandbox|strix|probe|evidence)\w*\b",
    "help": r"\b(help|question|assistant|chatbot|capabilit|use)\w*\b|what can you do",
}
HELP_TEXT = (
    "I can read the current local session: traffic totals, attack labels, hosts or a specific IP, "
    "destination ports, protocols, traffic volume, recent flows, the latest model forecast, provenance, model status, and "
    "sandbox validation. Try ‘How many attack flows?’, ‘Show traffic for 192.0.2.10’, "
    "or ‘What does the model forecast?’. I cannot run scans, modify data, or answer from files "
    "that have not been loaded into this app."
)


@lru_cache(maxsize=1)
def _intent_model():
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True)
    features = vectorizer.fit_transform(EXAMPLES)
    classifier = LogisticRegression(max_iter=500, random_state=0)
    classifier.fit(features, LABELS)
    return vectorizer, features, classifier


def _intent(question: str) -> str:
    vectorizer, examples, classifier = _intent_model()
    encoded = vectorizer.transform([question])
    similarity = float(cosine_similarity(encoded, examples).max())
    if similarity < 0.18:
        return "unknown"
    intent = str(classifier.predict(encoded)[0])
    return intent if re.search(INTENT_TERMS[intent], question.lower()) else "unknown"


def _host_in_question(question: str) -> str | None:
    for candidate in re.findall(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", question):
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None


def _timestamp(value: Any) -> str:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OverflowError, OSError, ValueError):
        pass
    return str(value or "unknown time")


def _rows(counter: Counter, limit: int = 6) -> str:
    return "\n".join(f"• {name}: {count:,}" for name, count in counter.most_common(limit)) or "No rows."


def answer_question(
    question: str,
    *,
    events: list[dict[str, Any]],
    state: Any | None,
    forecast: dict[str, Any] | None,
    model: dict[str, Any],
    validation: dict[str, Any] | None,
    strix_available: bool,
) -> dict[str, Any]:
    """Return a concise answer with an explicit evidence source and scope."""
    question = question.strip()
    host = _host_in_question(question)
    port_match = re.search(r"\b(?:destination\s+)?port\s*(\d{1,5})\b", question.lower())
    action = re.search(r"\b(delete|erase|remove|modify|write|scan|exploit|isolate|block)\b", question.lower())
    command = re.search(r"^\s*(please\s+)?(delete|erase|remove|modify|write|scan|exploit|isolate|block)\b", question.lower())
    unsupported_analysis = re.search(r"\b(trend|increasing|decreasing|over time|most dangerous|highest risk|riskiest)\b", question.lower())
    action_requested = bool(action and (command or re.search(
        r"\b(please|can you|could you|do it|run|start|make|perform)\b", question.lower()
    )))
    if unsupported_analysis or action_requested:
        intent = "unknown"
    else:
        intent = "host" if host else "ports" if port_match else _intent(question)
    source = "Current in-memory telemetry buffer"
    n = len(events)

    if action_requested:
        answer = "This assistant is read-only. It cannot run scans, change defenses, delete data, or export files. Use the app's dedicated controls for authorized actions."
        source = "Assistant read-only policy"
    elif unsupported_analysis:
        answer = ("I cannot establish that trend or rank hosts by danger from the available chat summaries. "
                  "I can report observed counts and the current model forecast separately; flow frequency is not a risk score.")
        source = "Unsupported analysis; no result fabricated"
    elif intent == "help":
        answer, source = HELP_TEXT, "Assistant capability list"
    elif intent == "model":
        if model.get("available"):
            answer = (f"Loaded checkpoint: {model.get('checkpoint_name') or 'unknown'}; "
                      f"device: {model.get('device') or 'unknown'}; "
                      f"parameters: {model.get('parameters', 0):,}; "
                      f"version: {model.get('version') or 'unknown'}.")
        else:
            answer = "No model checkpoint is loaded. The app cannot produce a model forecast right now."
        source = "Model runtime status"
    elif intent == "validation":
        if validation:
            statuses = ", ".join(
                f"{item.get('name', 'check')} HTTP {item.get('http_status', '?')}"
                for item in validation.get("checks", [])
            )
            answer = (f"Latest local sandbox check: {validation.get('verdict', 'unknown')}. "
                      f"{statuses}. This checks the bundled target's HTTP behavior, not model accuracy. "
                      f"Strix scanning is {'available' if strix_available else 'unavailable'}.")
        else:
            answer = ("No completed local sandbox check is available. "
                      f"Strix scanning is {'available' if strix_available else 'unavailable'}.")
        source = "Saved local validation result and Strix availability"
    elif intent == "forecast":
        if not forecast or not forecast.get("steps"):
            answer = "No model forecast is available in this session. Load a capture or demo sample first."
        else:
            steps = forecast["steps"][:4]
            detail_parts = []
            for index, step in enumerate(steps):
                risk_pct = step.get("risk_pct")
                if risk_pct is None and step.get("risk") is not None:
                    risk_pct = float(step["risk"]) * 100
                risk_text = f"{float(risk_pct):.1f}% risk" if risk_pct is not None else "risk unavailable"
                detail_parts.append(f"step {step.get('step', index + 1)}: {step.get('stage') or 'Unknown'} ({risk_text})")
            detail = "; ".join(detail_parts)
            answer = (f"Latest saved model forecast: {detail}. These are predictions, not observed attack stages.")
        source = "Latest model forecast in this session"
    elif not n:
        answer = "No traffic is loaded in this session. Import a PCAP/CSV or load a demo sample, then ask again."
    elif intent == "host" and host:
        matched = [e for e in events if host in (str(e.get("src")), str(e.get("dst")))]
        if not matched:
            answer = f"Host {host} does not occur in the {n:,} currently buffered flows."
        else:
            labels = Counter(str(e.get("label") or "UNKNOWN") for e in matched)
            answer = (f"Host {host} appears in {len(matched):,} of {n:,} buffered flows. "
                      f"Labels: {', '.join(f'{label} {count:,}' for label, count in labels.most_common(5))}. "
                      f"Latest: {_timestamp(matched[-1].get('timestamp'))}.")
    elif intent == "summary":
        attack = sum(str(e.get("label") or "BENIGN").upper() != "BENIGN" for e in events)
        hosts = {str(value) for e in events for value in (e.get("src"), e.get("dst")) if value}
        answer = (f"There are {n:,} buffered flows: {attack:,} attack-labeled and {n - attack:,} "
                  f"Benign, involving {len(hosts):,} distinct hosts. "
                  f"Latest flow: {_timestamp(events[-1].get('timestamp'))}. "
                  "These are observed labels in the loaded data, not model predictions.")
    elif intent == "labels":
        if "stage" in question.lower():
            stages = Counter(
                STAGE_NAMES[int(e["attack_stage"])] if e.get("attack_stage") is not None and 0 <= int(e["attack_stage"]) < len(STAGE_NAMES)
                else "Unspecified" for e in events
            )
            answer = f"Recorded stage fields in {n:,} buffered flows:\n{_rows(stages)}"
        else:
            labels = Counter(str(e.get("label") or "UNKNOWN") for e in events)
            requested = next((label for label in labels if len(label) >= 3 and label.lower() in question.lower()), None)
            if requested:
                answer = f"{requested}: {labels[requested]:,} of {n:,} buffered flows. These are observed labels, not model predictions."
            elif "how many" in question.lower() and "attack" in question.lower():
                attack = sum(count for label, count in labels.items() if label.upper() != "BENIGN")
                answer = f"{attack:,} of {n:,} buffered flows have a non-Benign observed label."
            else:
                answer = f"Observed flow labels in {n:,} buffered events:\n{_rows(labels)}"
    elif intent == "hosts":
        hosts = Counter(str(value) for e in events for value in (e.get("src"), e.get("dst")) if value)
        answer = f"Most frequent endpoint hosts across {n:,} buffered flows:\n{_rows(hosts)}\nThis ranks activity, not model risk."
    elif intent == "ports":
        ports = Counter(str(int(float(e["dst_port"]))) for e in events if e.get("dst_port") not in (None, ""))
        if port_match and 0 <= int(port_match.group(1)) <= 65535:
            port = port_match.group(1)
            answer = f"Destination port {port} occurs in {ports[port]:,} of {n:,} buffered flows."
        else:
            answer = f"Most frequent destination ports across {n:,} buffered flows:\n{_rows(ports)}"
    elif intent == "protocols":
        protocols = Counter(str(e.get("protocol") or "unknown") for e in events)
        known = {"tcp": "6", "udp": "17", "icmp": "1"}
        requested = next((name for name in known if re.search(rf"\b{name}\b", question.lower())), None)
        if requested:
            count = protocols[known[requested]] + protocols[requested.upper()] + protocols[requested.lower()]
            answer = f"{requested.upper()} occurs in {count:,} of {n:,} buffered flows."
        else:
            answer = f"Protocol values in {n:,} buffered flows:\n{_rows(protocols)}"
    elif intent == "volume":
        total_bytes = sum(float(e.get("bytes_fwd") or 0) + float(e.get("bytes_bwd") or 0) for e in events)
        total_packets = sum(float(e.get("packets_fwd") or 0) + float(e.get("packets_bwd") or 0) for e in events)
        answer = f"Across {n:,} buffered flows: {total_bytes:,.0f} bytes and {total_packets:,.0f} packets recorded in both directions."
    elif intent == "recent":
        match = re.search(r"\b(?:last|latest|recent)\s+(\d{1,2})\b", question.lower())
        limit = min(max(int(match.group(1)), 1), 10) if match else 5
        lines = [f"• {_timestamp(e.get('timestamp'))}: {e.get('src', '?')} → {e.get('dst', '?')} · {e.get('label', 'UNKNOWN')}"
                 for e in events[-limit:][::-1]]
        answer = f"Latest {len(lines)} buffered flows:\n" + "\n".join(lines)
    elif intent == "provenance":
        sources = Counter(str(e.get("source") or "unknown") for e in events)
        answer = f"Source labels on {n:,} buffered flows:\n{_rows(sources)}\nThese tags identify the app's ingestion path; they do not independently verify dataset authenticity."
    else:
        intent = "unknown"
        answer = ("I cannot answer that from the current local data. " + HELP_TEXT)
        source = "No matching supported data query"

    return {
        "answer": answer,
        "intent": intent,
        "source": source,
        "scope": f"Current local session; {n:,} buffered flows; {getattr(state, 'event_count', 0) if state else 0} flows in the latest graph window",
        "engine": "CYBERMIND domain-trained scikit-learn NLP router (offline, read-only)",
    }
