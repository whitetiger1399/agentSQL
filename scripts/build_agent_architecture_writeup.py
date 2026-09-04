from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "AgentSQL_Agent_Architecture_Writeup.pdf"
ASSETS = ROOT / "assets" / "docs"

NAVY = colors.HexColor("#071525")
INK = colors.HexColor("#172338")
MUTED = colors.HexColor("#5E6B7A")
CYAN = colors.HexColor("#00AFC8")
GREEN = colors.HexColor("#4B8D36")
PALE = colors.HexColor("#EFF7F8")
LINE = colors.HexColor("#D7E1E8")
WHITE = colors.white


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    "Kicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9,
    leading=12, textColor=CYAN, spaceAfter=8, tracking=1.2,
))
styles.add(ParagraphStyle(
    "DocTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=29,
    leading=33, textColor=WHITE, alignment=TA_LEFT, spaceAfter=12,
))
styles.add(ParagraphStyle(
    "CoverSub", parent=styles["Normal"], fontName="Helvetica", fontSize=13,
    leading=19, textColor=colors.HexColor("#DCEAF0"), spaceAfter=18,
))
styles.add(ParagraphStyle(
    "H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20,
    leading=24, textColor=NAVY, spaceBefore=0, spaceAfter=10,
))
styles.add(ParagraphStyle(
    "H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12,
    leading=15, textColor=CYAN, spaceBefore=10, spaceAfter=5,
))
styles.add(ParagraphStyle(
    "Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.4,
    leading=14, textColor=INK, spaceAfter=7,
))
styles.add(ParagraphStyle(
    "Lead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=12,
    leading=17, textColor=NAVY, spaceAfter=12,
))
styles.add(ParagraphStyle(
    "Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8,
    leading=11, textColor=MUTED, spaceAfter=4,
))
styles.add(ParagraphStyle(
    "Caption", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=7.8,
    leading=10, textColor=MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8,
))
styles.add(ParagraphStyle(
    "Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.2,
    leading=15, textColor=NAVY, spaceAfter=0,
))
styles.add(ParagraphStyle(
    "Bulletx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.1,
    leading=13, textColor=INK, leftIndent=14, firstLineIndent=-8, bulletIndent=3,
    spaceAfter=5,
))
styles.add(ParagraphStyle(
    "CellHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5,
    leading=11, textColor=WHITE,
))
styles.add(ParagraphStyle(
    "Cell", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2,
    leading=11, textColor=INK,
))


def header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(LINE)
        canvas.line(0.7 * inch, 10.35 * inch, 7.8 * inch, 10.35 * inch)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.7 * inch, 10.48 * inch, "CAMERA AGENTSQL  /  ARCHITECTURE BRIEF")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(7.8 * inch, 0.42 * inch, f"{doc.page}")
    canvas.restoreState()


def cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, LETTER[0], LETTER[1], fill=1, stroke=0)
    canvas.setFillColor(CYAN)
    canvas.rect(0, 0, 0.14 * inch, LETTER[1], fill=1, stroke=0)
    canvas.restoreState()


def img(name, width):
    item = Image(str(ASSETS / name))
    item.drawHeight = width * item.imageHeight / item.imageWidth
    item.drawWidth = width
    return item


def bullet(text):
    return Paragraph(f"• {text}", styles["Bulletx"])


def callout(text):
    table = Table([[Paragraph(text, styles["Callout"])]], colWidths=[6.82 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.8, CYAN),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def decision_table(rows):
    data = [[Paragraph("Choice", styles["CellHead"]), Paragraph("Why it fits", styles["CellHead"]), Paragraph("Boundary", styles["CellHead"])]]
    for row in rows:
        data.append([Paragraph(cell, styles["Cell"]) for cell in row])
    table = Table(data, colWidths=[1.42 * inch, 3.25 * inch, 2.15 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ]))
    return table


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUT), pagesize=LETTER, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.72 * inch, bottomMargin=0.65 * inch,
        title="Camera AgentSQL — Agent Architecture, Choices and Justification",
        author="Ritik Srivastava",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=cover),
        PageTemplate(id="body", frames=[frame], onPage=header_footer),
    ])

    story = []
    story += [Spacer(1, 1.28 * inch), Paragraph("TECHNICAL DESIGN BRIEF", styles["Kicker"])]
    story += [Paragraph("Camera AgentSQL", styles["DocTitle"])]
    story += [Paragraph("Agent architecture, tool and model choices, and the reliability case for a constrained natural-language database agent.", styles["CoverSub"])]
    story += [Spacer(1, 0.28 * inch)]
    story += [callout("The core decision: use the LLM to understand language—not to own policy, state, query construction, or database access.")]
    story += [Spacer(1, 2.25 * inch)]
    story += [Paragraph("Prepared by Ritik Srivastava", styles["CoverSub"]), Paragraph("Traffic-camera query agent  |  Python 3.12  |  September 2026", styles["Small"])]
    story += [NextPageTemplate("body"), PageBreak()]

    story += [Paragraph("1  Architecture at a glance", styles["H1x"])]
    story += [Paragraph("A narrow model boundary, deterministic execution", styles["Lead"])]
    story += [Paragraph("Camera AgentSQL converts a natural-language request into a validated query plan, then hands control to ordinary Python. The model never emits executable MongoDB syntax. Every consequential operation—camera resolution, date arithmetic, context merging, filter construction, validation, and execution—remains explicit and testable.", styles["Bodyx"])]
    story += [img("production-architecture-3.png", 6.82 * inch), Paragraph("Production flow. Solid arrows remain within a layer; dashed arrows cross trust or execution boundaries.", styles["Caption"])]
    story += [callout("This is intentionally not an autonomous tool loop. One typed extraction call is enough for the bounded problem; adding an agent framework would increase failure modes without improving control.")]
    story += [PageBreak()]

    story += [Paragraph("2  Request-to-result path", styles["H1x"])]
    story += [Paragraph("Ten visible steps; three hard trust boundaries", styles["Lead"])]
    left = [
        Paragraph("<b>1–2 · Intake</b><br/>Streamlit receives the request and maintains session state. Conservative typo normalization corrects known query terms without rewriting camera names.", styles["Bodyx"]),
        Paragraph("<b>3–5 · Interpret</b><br/>Pre-query guardrails reject unsafe intent. The Responses API extracts a strict Pydantic QueryPlan; unknown properties are forbidden.", styles["Bodyx"]),
        Paragraph("<b>6–7 · Resolve</b><br/>Python resolves cameras, Singapore-local dates, weekdays, overnight windows, follow-up context, sort order, and limit.", styles["Bodyx"]),
        Paragraph("<b>8–10 · Execute</b><br/>An allowlisted filter reaches one read-only repository method over traffic_frames. MongoDB results are sorted, capped, display-sanitized, and returned to Streamlit.", styles["Bodyx"]),
    ]
    path_table = Table([[left, img("agent-design.png", 2.65 * inch)]], colWidths=[4.0 * inch, 2.72 * inch])
    path_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 16), ("RIGHTPADDING", (1, 0), (1, 0), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story += [path_table, Paragraph("The model is deliberately boxed into entity and intent extraction.", styles["Caption"])]
    story += [Paragraph("Data contract", styles["H2x"])]
    story += [Paragraph("The cameras collection is reference metadata: camera_id, canonical camera_name, acronym, aliases, and active state. traffic_frames is a native time-series collection keyed by captured_at with camera_name metadata, frame_id, and frame_img_url. The synthetic sample contains 14,640 hourly frame records from 1 August through 30 September 2026.", styles["Bodyx"])]
    story += [PageBreak()]

    story += [Paragraph("3  Tool and model choices", styles["H1x"])]
    story += [Paragraph("Choose the smallest component that can enforce each responsibility", styles["Lead"])]
    story += [decision_table([
        ("OpenAI Responses API", "One structured extraction call maps natural language to QueryPlan.", "No query syntax, tool selection, or direct database access."),
        ("gpt-5.4-mini", "Default model balances instruction following, structured output, latency, and cost for extraction.", "Replaceable through OPENAI_MODEL; downstream controls do not depend on model trust."),
        ("Pydantic", "A strict typed contract rejects extra fields and invalid date/limit shapes.", "Validation proves shape—not business correctness—so Python still resolves values."),
        ("RapidFuzz", "Local matching covers acronyms, aliases, and reasonable spelling errors.", "Low-confidence or close competing matches trigger clarification."),
        ("PyMongo + Atlas", "Explicit find operations fit MongoDB time-series data and remain easy to audit.", "No generic command or write interface; hard maximum of 100 records."),
        ("Streamlit", "Fast multipage review UI, chat state, trace display, and deployment from GitHub main.", "Presentation layer only; it does not weaken repository controls."),
        ("zoneinfo + pytest", "Standard-library timezone conversion plus deterministic tests for boundary behavior.", "Asia/Singapore input is converted to half-open UTC intervals."),
    ])]
    story += [Spacer(1, 10), callout("Reliability comes from separation of duties: probabilistic interpretation at the edge, deterministic enforcement at the core.")]
    story += [PageBreak()]

    story += [Paragraph("4  Guardrails and query validation", styles["H1x"])]
    story += [Paragraph("The database never sees raw user instructions", styles["Lead"])]
    story += [callout("TWO INDEPENDENT DEFENSE LAYERS  ·  Intent layer: guardrails and the constrained LLM reject unsafe intent and emit only a typed plan.  ·  Hard authorization layer: MongoDB Atlas authenticates a read-only user, so server-side permissions deny writes even if an upstream control fails."), Spacer(1, 10)]
    safety_table = Table([[
        [Paragraph("<b>Before the model</b>", styles["H2x"]), bullet("Reject insert, update, delete, drop, truncate, upsert, schema changes, arbitrary MongoDB commands, secret disclosure, and rule-override attempts."), bullet("Reject empty or oversized requests before API or database work.")],
        img("safety-validation.png", 2.9 * inch),
    ]], colWidths=[3.82 * inch, 3.0 * inch])
    safety_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 16), ("RIGHTPADDING", (1, 0), (1, 0), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story += [safety_table]
    story += [Paragraph("Validation layers", styles["H2x"])]
    story += [bullet("QueryPlan permits only known fields and constrained enums; result_limit cannot exceed 100."), bullet("Camera terms must resolve to active canonical records. Ambiguous matches return suggestions instead of guessing."), bullet("Dates resolve in Asia/Singapore, then convert to UTC half-open bounds using $gte and $lt. Overnight ranges advance the end date deterministically."), bullet("Mongo filters accept only camera_name and captured_at, and only $and, $or, $in, $gte, and $lt."), bullet("The user query path exposes only traffic_frames.find(...). Atlas credentials belong to a read-only database user—the final server-enforced barrier against writes and schema changes."), bullet("Authentication, rate-limit, timeout, malformed-output, resolution, empty-result, and database failures become bounded, secret-safe messages.")]
    story += [callout("Injection resistance does not depend on the LLM recognizing every malicious phrase. User text cannot become executable syntax, the repository allowlist blocks unapproved operations, and MongoDB permissions provide the final hard stop.")]
    story += [PageBreak()]

    story += [Paragraph("5  Context, ambiguity, and time", styles["H1x"])]
    story += [Paragraph("Preserve filters—not an unrestricted transcript", styles["Lead"])]
    context_table = Table([[img("context-reliability.png", 3.15 * inch), [Paragraph("<b>Follow-up policy</b>", styles["H2x"]), Paragraph("Session state stores canonical camera names, a validated date window, weekdays, and optional start/end times. Clear follow-ups inherit omitted filters; explicit new values replace the corresponding prior field. Fresh commands do not silently inherit an old camera.", styles["Bodyx"]), Paragraph("<b>Example</b><br/>1. “Show me frames from CTE.”<br/>2. “How about only those from this week?”<br/><br/>The second turn keeps Central Expressway and adds the current-week date constraint.", styles["Bodyx"]), Paragraph("<b>Ambiguity policy</b><br/>Low-confidence camera text or competing matches returns clarification suggestions. The system prefers a visible non-answer over a confident query against the wrong camera.", styles["Bodyx"])] ]], colWidths=[3.25 * inch, 3.57 * inch])
    context_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (1, 0), (1, 0), 16), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story += [context_table]
    story += [Paragraph("Temporal semantics", styles["H2x"]), Paragraph("A session-wide Singapore date anchors “today,” “yesterday,” “this week,” and relative month ranges such as “15th to 18th of last month.” The synthetic dataset extends from 1 August to 30 September 2026 so relative-date queries remain testable later in September. Future rows are test fixtures, not forecasts: explicit dates after the session date are rejected, and broad queries are automatically capped at today. Calendar validity is checked before execution.", styles["Bodyx"])]
    story += [PageBreak()]

    story += [Paragraph("6  Why this architecture is robust", styles["H1x"])]
    story += [Paragraph("Control increases as the request approaches data", styles["Lead"])]
    story += [img("data-schema.png", 4.7 * inch), Paragraph("Reference metadata supports resolution; only time-series frame records are queryable through chat.", styles["Caption"])]
    story += [Paragraph("Design judgment", styles["H2x"])]
    story += [bullet("One model call keeps prompts short, latency bounded, and failures attributable."), bullet("Typed plans make model output inspectable without exposing hidden reasoning."), bullet("Deterministic Python makes dates, context, future-date rejection, filters, and limits unit-testable."), bullet("A repository allowlist provides a final technical boundary independent of prompt quality."), bullet("The Query Processing UI reveals normalized input, resolved values, safe filter, sort, limit, and row count—enough to audit behavior without leaking prompts or credentials.")]
    story += [Spacer(1, 6), callout("The trade-off is deliberate: less autonomy, more predictability. For a read-only traffic-camera retrieval task, that is the correct engineering choice.")]
    story += [Spacer(1, 12), Paragraph("Verification focus", styles["H2x"]), Paragraph("The test suite covers strict validation, malformed plans, typo and alias resolution, ambiguity, relative and ranged dates, weekdays, overnight windows, Singapore-to-UTC conversion, follow-up inheritance and reset, unsafe requests, filter allowlists, hard limits, and mocked API/database failures.", styles["Bodyx"])]
    story += [Spacer(1, 10), Paragraph("Implementation basis: agents.md, docs/project_context.md, and the current Camera AgentSQL source on feature-v2.", styles["Small"])]

    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
