from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "pdf" / "SIH26153_CYBERMIND_Separate_Files"
ARCH = ROOT / "architecture_diagram.jpeg"


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleBlack", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=21, leading=23, textColor=colors.black,
            alignment=TA_LEFT, spaceAfter=5,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.5, leading=10.5, textColor=colors.HexColor("#2D3E50"),
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=12, leading=14, textColor=colors.black,
            spaceBefore=6, spaceAfter=3, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.2, leading=12, alignment=TA_JUSTIFY,
            textColor=colors.black, spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9, leading=11.2, leftIndent=12, firstLineIndent=-8,
            bulletIndent=2, alignment=TA_LEFT, spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.6, leading=9.2, alignment=TA_LEFT, spaceAfter=0,
        ),
        "small_center": ParagraphStyle(
            "SmallCenter", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.6, leading=9.2, alignment=TA_CENTER, spaceAfter=0,
        ),
        "header": ParagraphStyle(
            "Header", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.8, leading=9.4, alignment=TA_CENTER,
            textColor=colors.white, spaceAfter=0,
        ),
    }


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(A4[0] / 2, 8 * mm, f"SIH26153  |  CYBERMIND  |  Page {doc.page}")
    canvas.restoreState()


def make_doc(path, title_text, subject):
    doc = BaseDocTemplate(
        str(path), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=15 * mm, title=title_text,
        author="CYBERMIND Team", subject=subject,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="standard", frames=[frame], onPage=footer)])
    return doc


def p(text, style, **kwargs):
    return Paragraph(text, style, **kwargs)


def common_header(title_text, s):
    return [
        p(title_text, s["title"]),
        p("Smart India Hackathon 2026  |  Problem Statement SIH26153  |  CYBERMIND", s["meta"]),
    ]


def build_idea(s):
    path = OUT_DIR / "01_CYBERMIND_Idea_Description.pdf"
    doc = make_doc(path, "CYBERMIND Idea Description", "SIH26153 CYBERMIND idea description")
    story = common_header("CYBERMIND Idea Description", s)
    story += [
        p("Proposed Solution", s["h1"]),
        p("CYBERMIND is an offline, analyst-centred predictive cyber-defence platform that moves beyond the conventional detect-and-alert model. It represents an enterprise network as a time-ordered sequence of host communication graphs, learns how that state evolves, and forecasts the risk and coarse attack stage of upcoming graph windows. This gives defenders an evidence-linked view of what may happen next while an intrusion is still developing.", s["body"]),
        p("An analyst imports a PCAP, PCAPNG, CAP, or network-flow CSV. CYBERMIND parses the input locally, preserves file provenance, converts records into a canonical flow schema, and builds overlapping temporal graph windows in which hosts are nodes and communications are edges. A pinned graph-temporal model combines a GATv2 graph encoder, temporal Transformer, learned latent dynamics, and multi-head prediction layers to produce a short-horizon risk trajectory, coarse attack-stage estimates, uncertainty cues, and model metadata.", s["body"]),
        p("The forecast is integrated into a practical investigation workflow. The Command Centre connects network topology, observed flows, timelines, and forecasts. Parallel Futures applies permitted in-memory changes - such as host isolation, port blocking, or rate limiting - to copies of the current graph and compares their predicted future risk with the no-action baseline. These are decision-support simulations; the platform does not silently enforce controls on a production network.", s["body"]),
        p("A bounded offline assistant answers read-only questions about the loaded case. The local validation engine freezes the current forecast and records actual sandbox HTTP responses and SHA-256 response hashes. The Reports module creates an incident brief and encrypts it locally using AES-256-GCM with a fresh random key and nonce. The encrypted JSON excludes the key, allowing the file and key to be shared separately and decrypted inside CYBERMIND.", s["body"]),
        p("Core Innovation", s["h1"]),
        p("Forecasting instead of isolated classification: the model predicts aggregate future graph-window risk rather than assigning unsupported labels to every individual flow.", s["bullet"], bulletText="-"),
        p("Counterfactual decision support: analysts can compare the model's no-action future with simulated defensive alternatives before approving consequential action.", s["bullet"], bulletText="-"),
        p("Evidence separation: observations, rule-based flow triage, model forecasts, validation responses, and analyst decisions remain explicitly distinguishable.", s["bullet"], bulletText="-"),
        p("Offline operation: Windows desktop and Linux Docker variants keep the core pipeline independent of cloud APIs and support protected local reporting.", s["bullet"], bulletText="-"),
        p("Expected Impact", s["h1"]),
        p("CYBERMIND changes the defender workflow from retrospective alert review to evidence-linked prediction, simulation, and informed planning. It helps an analyst understand the present network state, anticipate a plausible near-term escalation, test reversible response options, and preserve the investigation as a protected incident brief. The result is earlier situational awareness without presenting uncertain model outputs as verified truth or autonomous enforcement.", s["body"]),
    ]
    doc.build(story)
    return path


def build_abstract(s):
    path = OUT_DIR / "02_CYBERMIND_Project_Abstract.pdf"
    doc = make_doc(path, "CYBERMIND Project Abstract", "SIH26153 CYBERMIND project abstract")
    story = common_header("Project Abstract", s)
    story += [
        p("Abstract", s["h1"]),
        p("Modern intrusion-detection systems primarily describe traffic that has already occurred, giving defenders limited support for anticipating attack progression or comparing possible responses. CYBERMIND addresses SIH26153 through an offline graph-temporal world model for short-horizon cyber-risk forecasting. The platform transforms packet captures or network-flow records into rolling host-communication graphs, where hosts form nodes and communications form feature-rich edges. A GATv2 encoder learns the spatial structure of each graph, a temporal Transformer models changes across observed windows, and a learned latent dynamics module rolls the network state forward. Multi-head outputs estimate future infiltration risk, coarse attack stage, and predictive dispersion.", s["body"]),
        p("The forecasting engine is integrated with an analyst workspace rather than presented as an isolated model. The Command Centre connects observed topology, flow evidence, and a future risk timeline. Parallel Futures compares the same model's baseline forecast against controlled in-memory graph modifications representing actions such as rate limiting, port blocking, or host isolation. A bounded offline assistant answers case-grounded questions, while a local validation engine records real sandbox HTTP responses and SHA-256 hashes beside a frozen forecast. For secure collaboration, incident briefs are encrypted locally with AES-256-GCM and decrypted inside the application using a separately shared key.", s["body"]),
        p("The selected checkpoint achieved pooled held-out binary F1 of 0.9849, precision of 0.9970, recall of 0.9730, and a false-positive rate of 0.0056 on the documented capture-grouped CIC-IDS2018 four-observed-window to four-future-window protocol. On that split, it outperformed a feature-matched logistic-regression baseline. These results support short-horizon binary graph-window forecasting under the stated evaluation conditions; they do not establish universal performance or verified per-flow attack labels.", s["body"]),
        p("CYBERMIND therefore demonstrates a practical transition from retrospective alerting toward evidence-linked prediction, counterfactual simulation, and informed defensive planning. Its core pipeline runs locally through a Windows desktop application or offline Docker package, keeping operational data and model inference under the analyst's control. Stage estimates, uncertainty indicators, and simulated interventions are clearly presented as decision aids, while consequential actions remain subject to human approval.", s["body"]),
        p("Keywords", s["h1"]),
        p("Predictive cyber defence, graph neural network, temporal Transformer, network world model, attack forecasting, counterfactual simulation, offline security analytics, AES-256-GCM.", s["body"]),
    ]
    doc.build(story)
    return path


def build_architecture(s):
    path = OUT_DIR / "03_CYBERMIND_Architecture_Document.pdf"
    doc = make_doc(path, "CYBERMIND Architecture Document", "SIH26153 CYBERMIND system architecture")
    story = common_header("CYBERMIND Architecture Document", s)
    story += [
        p("System Overview", s["h1"]),
        p("CYBERMIND uses a four-tier local architecture that separates telemetry preparation, learned forecasting, analyst decision support, and trusted delivery. All core processing runs locally. The diagram below is the authoritative visual architecture and shows the main left-to-right data path.", s["body"]),
    ]
    image = Image(str(ARCH), width=178 * mm, height=100.1 * mm)
    image.hAlign = "CENTER"
    story += [image, Spacer(1, 3 * mm), p("Architecture Layers", s["h1"])]
    data = [
        [p("Tier", s["header"]), p("Components", s["header"]), p("Responsibility", s["header"])],
        [p("1  Ingestion", s["small_center"]), p("PCAP and flow ingestion, normaliser, temporal graph windowing, flow triage guard", s["small"]), p("Parses local captures or CSV files, preserves provenance, creates canonical flow events and rolling host-communication graphs, and keeps observed-flow triage separate from AI forecasts.", s["small"])],
        [p("2  Model Core", s["small_center"]), p("GATv2 encoder, temporal Transformer, latent dynamics, risk and stage heads", s["small"]), p("Encodes recent graph history and generates stochastic future trajectories, future graph-window risk, coarse attack-stage estimates, uncertainty cues, and model identity.", s["small"])],
        [p("3  Analyst Layer", s["small_center"]), p("Command Centre, Parallel Futures, defence recommender, offline NLP assistant", s["small"]), p("Links evidence to forecasts, compares in-memory defensive alternatives, ranks reversible suggestions, and answers bounded questions about the loaded case.", s["small"])],
        [p("4  Trust and Delivery", s["small_center"]), p("Local sandbox validator, AES-256-GCM vault, decrypt desk, desktop and Docker runtime", s["small"]), p("Records bounded response evidence, protects incident briefs with authenticated encryption, supports in-app decryption, and keeps core processing local.", s["small"])],
    ]
    table = Table(data, colWidths=[27 * mm, 61 * mm, 90 * mm], repeatRows=1, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D9D9D9")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#EDF4F8")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#EDF4F8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [
        table,
        p("End to End Flow", s["h1"]),
        p("<b>PCAP or CSV -> canonical flows -> temporal graph windows -> best.pt forecast -> analyst simulation and validation -> encrypted incident brief -> authenticated in-app decryption</b>", s["small_center"]),
        Spacer(1, 2 * mm),
        p("<b>Operational boundaries.</b> The trained model forecasts aggregate graph windows, not verified malicious labels for individual flows. Parallel Futures compares model outputs on modified graph copies and does not prove causal impact. The local validator records target responses but does not retrain the model. Consequential defensive actions remain under analyst control.", s["small"]),
        PageBreak(),
        p("Detailed Component Architecture", s["title"]),
        p("Smart India Hackathon 2026  |  SIH26153  |  CYBERMIND Technical Detail", s["meta"]),
        p("1  Ingestion and State Construction", s["h1"]),
        p("The analyst manually selects a <b>.pcap</b>, <b>.pcapng</b>, <b>.cap</b>, or <b>.csv</b> file. The FastAPI ingestion service records source provenance, extracts packets or matches flow columns, and converts the input into a canonical event schema containing endpoints, ports, protocol, timestamps, packet and byte counts, duration, and optional source labels. Missing CSV timestamps are handled only through a disclosed assumed spacing; labels are never invented for raw captures.", s["body"]),
        p("Canonical events are grouped into overlapping 60-second windows with a 30-second stride. Each window becomes a directed host-communication graph: hosts are nodes, communications are edges, and numeric traffic statistics form node and edge features. At least three graph windows are required for forecasting. The flow-triage guard separately derives Critical, High, Medium, secured, or Unassessed investigation hints from observed features and available source labels; these indicators are not predictions from <b>best.pt</b>.", s["body"]),
        p("2  Graph Temporal Forecasting Engine", s["h1"]),
    ]

    model_data = [
        [p("Stage", s["header"]), p("Processing", s["header"]), p("Output", s["header"])],
        [p("Graph encoder", s["small_center"]), p("GATv2 applies attention over each host-communication graph and optionally consumes edge features stored in the checkpoint configuration.", s["small"]), p("One learned embedding per observed graph window.", s["small"])],
        [p("Temporal encoder", s["small_center"]), p("A Transformer reads the ordered graph embeddings and represents the recent evolution of the network.", s["small"]), p("Latent observed state z_t.", s["small"])],
        [p("Dynamics rollout", s["small_center"]), p("A learned diagonal-Gaussian transition model samples multiple future latent trajectories from the current state.", s["small"]), p("Multi-step stochastic future states and dispersion.", s["small"])],
        [p("Prediction heads", s["small_center"]), p("Risk, coarse-stage, and future-state heads decode every forecast horizon. Saved training normalization is applied before inference.", s["small"]), p("Current and horizon risk, stage distribution, confidence and OOD proxies.", s["small"])],
    ]
    model_table = Table(model_data, colWidths=[30 * mm, 101 * mm, 47 * mm], repeatRows=1, hAlign="CENTER")
    model_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D9D9D9")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#EDF4F8")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#EDF4F8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [
        model_table,
        p("3  Analyst and Counterfactual Services", s["h1"]),
        p("The React Command Centre retrieves events, graph snapshots, forecasts, cases, and validation records through local REST endpoints and WebSocket updates. Threat Forecast presents the multi-step trajectory with model identity and uncertainty proxies. Attack Graph reconnects forecast context to observed hosts and edges. The offline NLP assistant uses a bounded TF-IDF and intent-classification pipeline to answer read-only questions from the loaded session; it cannot scan a network or modify evidence.", s["body"]),
        p("Parallel Futures copies the current graph, applies an allowed in-memory mutation such as host isolation, port blocking, or rate limiting, and reruns the same forecasting model. The defence recommender compares each simulated trajectory with the no-action baseline using predicted risk change, confidence, reversibility, and collateral-impact heuristics. Results are model-based comparisons for analyst review, not measured causal effects or automatically executed firewall rules.", s["body"]),
        p("4  Validation Security and Deployment", s["h1"]),
    ]

    runtime_data = [
        [p("Subsystem", s["header"]), p("Implementation and Trust Boundary", s["header"])],
        [p("Local validation", s["small_center"]), p("Freezes a forecast, calls four bounded endpoints on a bundled sandbox target, and stores HTTP status codes plus SHA-256 response-body hashes. It verifies target responses but does not establish attack-stage truth or retrain the model.", s["small"])],
        [p("Protected reports", s["small_center"]), p("Web Crypto generates a fresh random 256-bit key and 96-bit nonce. AES-256-GCM encrypts the incident brief locally. The JSON envelope contains nonce and ciphertext, not the key; the recipient imports it and supplies the separately shared key inside CYBERMIND.", s["small"])],
        [p("Windows runtime", s["small_center"]), p("CYBERMIND.exe packages the React assets, FastAPI backend, dependencies, checkpoint, and PySide6/Qt WebEngine window. The service binds to an ephemeral loopback address and requires no cloud model endpoint.", s["small"])],
        [p("Docker runtime", s["small_center"]), p("Prebuilt Linux x86-64 images run through Docker Compose, bind the application to 127.0.0.1:8000, and retain records in a named volume. Bundled launch scripts load images locally without pulling at runtime.", s["small"])],
    ]
    runtime_table = Table(runtime_data, colWidths=[34 * mm, 144 * mm], repeatRows=1, hAlign="CENTER")
    runtime_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#D9D9D9")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#EDF4F8")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#EDF4F8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [
        runtime_table,
        p("Interface Contracts", s["h1"]),
        p("<b>Input:</b> local packet capture or flow CSV. <b>Intermediate state:</b> canonical events, graph windows, model metadata, case records, and frozen validation evidence. <b>Output:</b> graph-window risk trajectory, coarse stage distribution, uncertainty proxies, counterfactual comparisons, and an optional encrypted incident brief. A missing or invalid checkpoint makes forecasting unavailable rather than generating substitute scores.", s["small"]),
    ]
    doc.build(story)
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (build_idea(styles()), build_abstract(styles()), build_architecture(styles())):
        print(path)


if __name__ == "__main__":
    main()
