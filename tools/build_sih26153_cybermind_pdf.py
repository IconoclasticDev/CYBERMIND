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
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "SIH26153_CYBERMIND_Idea_Abstract_Architecture.pdf"
ARCH = ROOT / "releases" / "CYBERMIND_ARCHITECTURE_2026-09-29.png"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(A4[0] / 2, 8 * mm, f"SIH26153  |  CYBERMIND  |  Page {doc.page}")
    canvas.restoreState()


def p(text, style, **kwargs):
    return Paragraph(text, style, **kwargs)


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title="CYBERMIND Project Brief and Architecture",
        author="CYBERMIND Team",
        subject="SIH26153 idea description abstract and architecture",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="two-page", frames=[frame], onPage=footer)])

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleBlack",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=22,
        textColor=colors.black,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    meta = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.4,
        leading=10,
        textColor=colors.HexColor("#2D3E50"),
        spaceAfter=5,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.black,
        spaceBefore=5,
        spaceAfter=3,
        keepWithNext=True,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11,
        textColor=colors.black,
        spaceBefore=4,
        spaceAfter=2,
        keepWithNext=True,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.25,
        leading=10.1,
        alignment=TA_JUSTIFY,
        textColor=colors.black,
        spaceAfter=3.2,
    )
    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        leftIndent=11,
        firstLineIndent=-7,
        bulletIndent=2,
        spaceAfter=1.5,
    )
    small = ParagraphStyle(
        "Small",
        parent=body,
        fontSize=7.4,
        leading=8.9,
        spaceAfter=0,
    )
    small_center = ParagraphStyle(
        "SmallCenter",
        parent=small,
        alignment=TA_CENTER,
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=small_center,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = [
        p("CYBERMIND Project Brief and Architecture", title),
        p("Smart India Hackathon 2026  |  Problem Statement SIH26153  |  Predictive Cyber Defence", meta),
        p("Idea Description", h1),
        p("CYBERMIND is an offline, analyst-centred predictive cyber-defence platform that moves beyond the conventional detect-and-alert model. It represents a network as a time-ordered sequence of host communication graphs, learns how that state changes, and forecasts the risk and coarse attack stage of upcoming graph windows. This gives defenders an evidence-linked view of what may happen next while an intrusion is still developing.", body),
        p("An analyst imports a PCAP, PCAPNG, CAP, or network-flow CSV. CYBERMIND parses the input locally, preserves file provenance, converts records into a canonical flow schema, and builds overlapping temporal graph windows in which hosts are nodes and communications are edges. A pinned graph-temporal model then combines a GATv2 graph encoder, temporal Transformer, learned latent dynamics, and multi-head prediction layers to generate a short-horizon risk trajectory, coarse stage estimates, and uncertainty indicators.", body),
        p("The forecast is placed inside a practical investigation workflow. The Command Centre links network topology, observed flows, timelines, and forecasts. Parallel Futures evaluates permitted in-memory changes such as host isolation, port blocking, or rate limiting and compares their predicted future risk with the no-action baseline. These outputs are decision-support simulations; CYBERMIND does not silently enforce controls on a production network. A bounded offline assistant answers read-only questions about the loaded case, while local validation records actual sandbox HTTP responses and SHA-256 hashes beside a frozen forecast.", body),
        p("For secure collaboration, the Reports module creates an incident brief and encrypts it locally using AES-256-GCM with a fresh random key and nonce. The encrypted JSON does not contain the secret key. A recipient imports the file into CYBERMIND, enters the separately shared key, and can view or download the readable report. The complete system runs locally as a Windows desktop application or from prebuilt offline Docker images, keeping the core analysis pipeline independent of cloud APIs.", body),
        p("Why the Solution Stands Out", h2),
        p("Forecasts future graph-window risk instead of classifying isolated flows only.", bullet, bulletText="-"),
        p("Connects prediction to counterfactual defence comparisons and analyst approval.", bullet, bulletText="-"),
        p("Keeps observations, rule-based flow triage, model forecasts, and validation evidence explicitly separate.", bullet, bulletText="-"),
        p("Operates offline and supports authenticated, encrypted incident-report exchange.", bullet, bulletText="-"),
        p("Project Abstract", h1),
        p("Modern intrusion-detection systems mainly describe traffic that has already occurred, leaving defenders little support for anticipating attack progression or comparing possible responses. CYBERMIND addresses SIH26153 through an offline graph-temporal world model for short-horizon cyber-risk forecasting. The platform transforms packet captures or flow records into rolling host-communication graphs, encodes spatial relationships with GATv2, models temporal evolution with a Transformer, and rolls a learned latent dynamics model forward to estimate future infiltration risk and coarse attack stage. The forecasts are integrated with an analyst workspace that provides network visualisation, rule-based flow triage, uncertainty cues, counterfactual intervention comparisons, bounded case questions, sandbox-response validation, and AES-256-GCM incident reporting. The selected checkpoint achieved pooled held-out binary F1 of 0.9849, precision of 0.9970, recall of 0.9730, and false-positive rate of 0.0056 on the documented capture-grouped CIC-IDS2018 protocol, outperforming the feature-matched logistic baseline on that split. CYBERMIND therefore demonstrates a practical shift from retrospective alerting toward evidence-linked prediction, simulation, and informed defensive planning, while clearly treating stage estimates and simulated interventions as decision aids rather than verified ground truth or autonomous enforcement.", body),
        PageBreak(),
        p("System Architecture", title),
        p("The architecture keeps ingestion, learned forecasting, analyst decision support, validation, and protected reporting within one local application boundary.", body),
    ]

    diagram = Image(str(ARCH), width=181 * mm, height=110.9 * mm)
    diagram.hAlign = "CENTER"
    story.extend([diagram, Spacer(1, 3 * mm), p("Architecture Layers", h1)])

    data = [
        [p("Layer", table_header), p("Core Components", table_header), p("Responsibility and Output", table_header)],
        [p("1  Ingestion", small_center), p("Local parser, provenance, normaliser, graph builder", small), p("Converts PCAP or CSV into source-tagged canonical flows and overlapping host-communication graph windows. Rule-based flow triage remains separate from model predictions.", small)],
        [p("2  Model Core", small_center), p("GATv2, temporal Transformer, latent dynamics, risk and stage heads", small), p("Encodes graph history and produces multi-step graph-window risk, coarse stage, predictive dispersion, model identity, and attribution evidence.", small)],
        [p("3  Analyst Layer", small_center), p("Command Centre, Threat Forecast, Parallel Futures, assistant", small), p("Links evidence to forecasts, compares in-memory defensive alternatives, ranks reversible suggestions, and answers bounded case questions.", small)],
        [p("4  Trust and Delivery", small_center), p("Local validator, AES-256-GCM reports, Windows and Docker runtimes", small), p("Stores bounded response evidence, encrypts incident briefs locally, supports in-app decryption, and keeps core processing offline.", small)],
    ]
    table = Table(data, colWidths=[29 * mm, 52 * mm, 100 * mm], repeatRows=1, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
    story.extend([
        table,
        p("End to End Data Flow", h2),
        p("<b>PCAP or CSV -> canonical flows -> temporal graphs -> best.pt forecast -> analyst simulation and validation -> encrypted incident brief</b>", small_center),
        Spacer(1, 1.5 * mm),
        p("<b>Operational boundaries.</b> The model forecasts aggregate graph windows, not verified malicious labels for individual flows. Parallel Futures compares model outcomes on modified graph copies and does not prove causal impact. Local validation records target responses but does not retrain the checkpoint. Consequential defensive actions remain under analyst control.", small),
    ])

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
