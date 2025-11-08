# app/services/notes.py
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from markdown_it import MarkdownIt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.notes import MeetingSummary, Topic, ActionItem

from openai import OpenAI
client = OpenAI()

#PROMPT 
_SYSTEM_PROMPT = """You are a meeting notes generator.
Given a raw meeting transcript (with optional timestamps), produce a clean, structured summary.
Respond in JSON with keys: executive_summary, topics[], decisions[], actions[].
- topics[]: {title, start?, end?}
- actions[]: {owner?, action, due?}
Keep it concise and faithful to the transcript. Keep language same as transcript.
If unsure about owner/due, leave them null.
"""

def _build_user_prompt(transcript_text: str, lang: str = "auto") -> str:
    return f"""LANGUAGE: {lang}
TRANSCRIPT:
{transcript_text}
"""

def generate_structured_notes(transcript_text: str, language: str = "auto") -> MeetingSummary:
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # model
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(transcript_text, language)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    data = completion.choices[0].message.content

    import json
    parsed = json.loads(data)

    topics = [Topic(**t) for t in parsed.get("topics", [])]
    decisions = parsed.get("decisions", [])
    actions = [ActionItem(**a) for a in parsed.get("actions", [])]

    return MeetingSummary(
        executive_summary=parsed.get("executive_summary", "").strip(),
        topics=topics,
        decisions=decisions,
        actions=actions,
    )


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def render_markdown(summary: MeetingSummary, transcript_text: str) -> str:
    lines: List[str] = []
    lines.append("# Notes de réunion")
    lines.append("")
    lines.append("## Résumé exécutif")
    lines.append(summary.executive_summary or "_(Non disponible)_")
    lines.append("")
    if summary.topics:
        lines.append("## Sujets abordés")
        for t in summary.topics:
            tline = f"- **{t.title}**"
            if t.start or t.end:
                ts = []
                if t.start: ts.append(f"start {t.start}")
                if t.end: ts.append(f"end {t.end}")
                tline += f" (_{', '.join(ts)}_)"
            lines.append(tline)
        lines.append("")
    if summary.decisions:
        lines.append("## Décisions")
        for d in summary.decisions:
            lines.append(f"- {d}")
        lines.append("")
    if summary.actions:
        lines.append("## Actions à réaliser")
        for a in summary.actions:
            who = f"**{a.owner}**: " if a.owner else ""
            due = f" _(due {a.due})_" if a.due else ""
            lines.append(f"- {who}{a.action}{due}")
        lines.append("")

    lines.append("---")
    lines.append("## Transcription complète")
    lines.append("")
    lines.append("```text")
    lines.append(transcript_text.strip())
    lines.append("```")
    return "\n".join(lines)

def save_markdown(md_text: str, out_dir: str) -> str:
    _ensure_dir(out_dir)
    md_path = os.path.join(out_dir, "meeting-notes.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    return md_path

def save_pdf_simple(md_text: str, out_dir: str) -> str:
    """
    Export PDF simple.
    Le Markdown sera 'aplati' .
    """
    _ensure_dir(out_dir)
    pdf_path = os.path.join(out_dir, "meeting-notes.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Marges
    x = 40
    y = height - 40
    max_width = width - 80

    import textwrap
    for paragraph in md_text.split("\n"):
        paragraph = paragraph.replace("## ", "").replace("# ", "").replace("**", "")
        for line in textwrap.wrap(paragraph, width=95):
            c.drawString(x, y, line)
            y -= 14
            if y < 40:
                c.showPage()
                y = height - 40
        y -= 6  # espace après paragraphe

    c.showPage()
    c.save()
    return pdf_path

def make_report_id() -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    rid = uuid.uuid4().hex[:6]
    return f"{ts}_{rid}"
