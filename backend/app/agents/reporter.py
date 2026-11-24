"""Agent 4 - Management report. Numbers are computed in SQL/Python; Claude only writes the narrative."""
import json
import logging
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm
from ..models import Complaint, QualityIssue, Report, utcnow
from .classifier import CATEGORIES

log = logging.getLogger("agent.reporter")

SYSTEM = """You write the weekly quality briefing for the executive team of a food manufacturer.
Use ONLY the numbers in the JSON provided; never invent figures, lots or products. Output markdown with exactly
three sections: '## Executive summary' (3-4 sentences), '## What changed this week' (3-5 bullets),
'## Recommended actions' (3-5 concrete bullets, each naming an owner role: Quality, Operations, Support, Logistics or Finance).
Be direct and plain. No preamble."""


def compute_stats(db: Session, end: datetime, days: int = 7) -> dict:
    start, prev_start = end - timedelta(days=days), end - timedelta(days=2 * days)
    cur = db.scalars(select(Complaint).where(Complaint.received_at > start, Complaint.received_at <= end)).all()
    prev = db.scalars(select(Complaint).where(Complaint.received_at > prev_start, Complaint.received_at <= start)).all()

    def pct(a: int, b: int) -> float | None:
        return round((a - b) / b * 100, 1) if b else None

    cat = Counter(c.category for c in cur)
    prev_cat = Counter(c.category for c in prev)
    lots = Counter(c.lot_code for c in cur if c.lot_code)
    prods = Counter(c.product.name if c.product else "Unknown" for c in cur)
    issue_ids = {c.issue_id for c in cur if c.issue_id}
    issues = []
    for iss in db.scalars(select(QualityIssue).where(QualityIssue.id.in_(issue_ids or {-1}))):
        n = sum(1 for c in cur if c.issue_id == iss.id)
        issues.append({"id": iss.id, "title": iss.title, "count_in_period": n, "total": iss.complaint_count,
                       "lots": iss.lot_codes, "max_severity": iss.max_severity, "status": iss.status})
    issues.sort(key=lambda x: -x["count_in_period"])
    return {
        "period_start": start.date().isoformat(),
        "period_end": end.date().isoformat(),
        "total": len(cur),
        "previous_total": len(prev),
        "change_pct": pct(len(cur), len(prev)),
        "by_severity": dict(Counter(c.severity for c in cur)),
        "by_source": dict(Counter(c.source for c in cur)),
        "by_category": [
            {"category": k, "label": CATEGORIES.get(k, k), "count": v, "previous": prev_cat.get(k, 0)}
            for k, v in cat.most_common()
        ],
        "by_product": dict(prods.most_common(6)),
        "top_lots": [{"lot": k, "complaints": v} for k, v in lots.most_common(5)],
        "escalated": sum(1 for c in cur if c.escalated),
        "critical": [
            {"id": c.id, "summary": c.summary, "lot": c.lot_code, "status": c.status}
            for c in cur if c.severity == "critical"
        ][:10],
        "avg_sentiment": round(sum(c.sentiment for c in cur) / len(cur), 2) if cur else 0,
        "awaiting_approval": sum(1 for c in cur if c.status in ("escalated", "draft_ready")),
        "recurring_issues": [i for i in issues if i["count_in_period"] >= 3][:6],
    }


def _fallback_narrative(s: dict) -> str:
    chg = s["change_pct"]
    trend = "no prior-week baseline" if chg is None else f"{'up' if chg >= 0 else 'down'} {abs(chg)}% versus the previous period"
    top = s["by_category"][0] if s["by_category"] else None
    crit = len(s["critical"])
    rec = s["recurring_issues"]
    lines = [
        "## Executive summary",
        f"We received **{s['total']}** complaints between {s['period_start']} and {s['period_end']}, {trend}. "
        + (f"The largest category was *{top['label']}* ({top['count']}). " if top else "")
        + f"**{crit}** were critical and **{s['escalated']}** were escalated to a human owner.",
        "",
        "## What changed this week",
    ]
    for i in rec[:3]:
        lots = f" (lots {', '.join(i['lots'])})" if i["lots"] else ""
        lines.append(f"- Recurring issue: **{i['title']}**, {i['count_in_period']} complaints this period{lots}.")
    for c in s["by_category"][:3]:
        d = c["count"] - c["previous"]
        lines.append(f"- {c['label']}: {c['count']} ({'+' if d >= 0 else ''}{d} vs previous).")
    lines += ["", "## Recommended actions"]
    if rec:
        lines.append(f"- **Quality:** open or review the investigation for \"{rec[0]['title']}\" and check production records for the lots listed.")
    if s["top_lots"]:
        lines.append(f"- **Operations:** review lot {s['top_lots'][0]['lot']} ({s['top_lots'][0]['complaints']} complaints) and consider a stock hold.")
    lines.append(f"- **Support:** review and approve the {s['awaiting_approval']} drafted replies that are still waiting.")
    lines.append("- **Executive:** confirm owners and due dates for every critical case listed below.")
    return "\n".join(lines)


def _tables(s: dict) -> str:
    out = ["", "---", "", "## Data", "", "| Category | This period | Previous |", "|---|---:|---:|"]
    out += [f"| {c['label']} | {c['count']} | {c['previous']} |" for c in s["by_category"]]
    if s["top_lots"]:
        out += ["", "| Lot | Complaints |", "|---|---:|"] + [f"| {x['lot']} | {x['complaints']} |" for x in s["top_lots"]]
    if s["recurring_issues"]:
        out += ["", "| Recurring issue | Complaints | Severity | Lots |", "|---|---:|---|---|"]
        out += [f"| {i['title']} | {i['count_in_period']} | {i['max_severity']} | {', '.join(i['lots']) or '-'} |" for i in s["recurring_issues"]]
    if s["critical"]:
        out += ["", "**Critical cases**", ""] + [f"- #{c['id']} {c['summary']} (lot {c['lot'] or 'n/a'}, status {c['status']})" for c in s["critical"]]
    return "\n".join(out)


def generate_report(db: Session, days: int = 7, end: datetime | None = None, use_llm: bool = True) -> Report:
    end = end or utcnow()
    stats = compute_stats(db, end, days)
    engine, narrative = "heuristic", ""
    if use_llm and llm.is_live():
        try:
            narrative = llm.complete(system=SYSTEM, user=json.dumps(stats, default=str), max_tokens=900)
            engine = llm.engine_name()
        except Exception as exc:
            log.warning("Claude report narrative failed: %s", exc)
    if not narrative:
        narrative = _fallback_narrative(stats)
    title = f"# Weekly Quality & Customer Report ({stats['period_start']} to {stats['period_end']})\n\n"
    rep = Report(
        kind="weekly_quality", period_start=end - timedelta(days=days), period_end=end,
        content_md=title + narrative + _tables(stats), data=stats, engine=engine,
    )
    db.add(rep)
    db.commit()
    return rep
