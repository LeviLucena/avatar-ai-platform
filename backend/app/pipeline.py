"""Complaint pipeline: classify -> link product/lot -> cluster -> escalate -> draft -> notify."""
import logging
import re
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import jobs
from .agents import classifier, escalation, responder
from .config import settings
from .embeddings import cosine, embed, mean_vector
from .models import Complaint, Notification, Product, ProductionRun, QualityIssue, SEVERITIES, utcnow
from .security import audit

log = logging.getLogger("pipeline")
GENERIC = {"bettr", "bowl", "bowls", "chicken", "rice", "cookies", "cookie", "chips", "salt", "with", "eat", "sea"}


def ingest(
    db: Session,
    *,
    source: str,
    body: str,
    subject: str = "",
    customer_name: str = "",
    customer_email: str = "",
    received_at=None,
    enqueue: bool = True,
) -> Complaint:
    c = Complaint(
        source=source,
        body=body.strip(),
        subject=subject.strip()[:300],
        customer_name=customer_name.strip()[:120],
        customer_email=customer_email.strip()[:200],
        received_at=received_at or utcnow(),
        status="new",
    )
    db.add(c)
    db.commit()
    if enqueue:
        jobs.enqueue(db, "process_complaint", {"complaint_id": c.id})
    return c


def resolve_product(db: Session, hint: str, text: str) -> Product | None:
    hay = f"{hint} {text}".lower()
    best, best_hits = None, 0
    for p in db.scalars(select(Product)):
        keys = {t for t in re.findall(r"[a-z]+", f"{p.name} {p.brand}".lower()) if len(t) >= 4 and t not in GENERIC}
        hits = sum(1 for k in keys if k in hay)
        if hits > best_hits:
            best, best_hits = p, hits
    return best


def _assign_issue(db: Session, c: Complaint, category: str) -> QualityIssue | None:
    if category == "praise_other":
        return None
    since = c.received_at - timedelta(days=30)
    cands = db.scalars(
        select(QualityIssue).where(
            QualityIssue.category == category,
            QualityIssue.last_seen >= since,
            QualityIssue.status != "resolved",
        )
    ).all()
    best, best_score = None, 0.0
    for iss in cands:
        s = cosine(c.embedding, iss.centroid)
        if c.product_id and iss.product_id == c.product_id:
            s += 0.10
        if c.lot_code and c.lot_code in (iss.lot_codes or []):
            s += 0.30
        if s > best_score:
            best, best_score = iss, s
    label = classifier.CATEGORIES[category]
    if best is not None and best_score >= settings.similarity_threshold:
        best.centroid = mean_vector(best.centroid, best.complaint_count, c.embedding)
        best.complaint_count += 1
        best.last_seen = max(best.last_seen, c.received_at)
        best.first_seen = min(best.first_seen, c.received_at)
        if c.lot_code and c.lot_code not in (best.lot_codes or []):
            best.lot_codes = [*(best.lot_codes or []), c.lot_code]
        if best.product_id is None and c.product_id:
            best.product_id = c.product_id
            best.title = f"{label}: {c.product.name}"
        return best
    title = f"{label}: {c.product.name}" if c.product else f"{label}: multiple / unknown product"
    iss = QualityIssue(
        title=title,
        category=category,
        product_id=c.product_id,
        lot_codes=[c.lot_code] if c.lot_code else [],
        complaint_count=1,
        first_seen=c.received_at,
        last_seen=c.received_at,
        centroid=c.embedding,
    )
    db.add(iss)
    db.flush()
    return iss


def _notify(db: Session, role: str, title: str, body: str, level: str, complaint_id: int) -> None:
    db.add(Notification(role=role, title=title, body=body, level=level, complaint_id=complaint_id))


def process_complaint(db: Session, complaint_id: int, use_llm: bool = True) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise ValueError(f"complaint {complaint_id} not found")
    text = f"{c.subject}\n{c.body}"

    # 1. classify (LLM structured output, heuristic fallback)
    a = classifier.classify(c.body, c.subject, use_llm=use_llm)
    c.category, c.sentiment, c.health_risk, c.language, c.engine = (
        a["category"], a["sentiment"], a["health_risk"], a["language"], a["engine"],
    )
    c.summary = a["summary"]
    c.lot_code = a["lot_code"]
    c.product = resolve_product(db, a["product_hint"], text)
    if c.product is None and c.lot_code:  # trace product through the production record of the lot
        run = db.scalar(select(ProductionRun).where(ProductionRun.lot_code == c.lot_code).limit(1))
        c.product = run.product if run else None
    c.product_id = c.product.id if c.product else None
    c.embedding = embed(text)

    # 2. cluster into a recurring quality issue
    issue = _assign_issue(db, c, c.category)
    c.issue_id = issue.id if issue else None
    db.flush()

    lot_n = 0
    if c.lot_code:
        lot_n = db.scalar(
            select(func.count()).select_from(Complaint).where(
                Complaint.lot_code == c.lot_code,
                Complaint.received_at >= c.received_at - timedelta(days=30),
                Complaint.received_at <= c.received_at,
            )
        ) or 0
    issue_n = 0
    if issue:
        issue_n = db.scalar(
            select(func.count()).select_from(Complaint).where(
                Complaint.issue_id == issue.id,
                Complaint.received_at >= c.received_at - timedelta(days=14),
                Complaint.received_at <= c.received_at,
            )
        ) or 0

    # 3. deterministic escalation policy (can only raise the AI severity)
    d = escalation.decide(
        category=c.category, ai_severity=a["severity"], health_risk=c.health_risk,
        text=text, lot_complaints_30d=lot_n, issue_count_14d=issue_n,
    )
    c.severity, c.escalated, c.escalation_reasons = d.severity, d.escalate, d.reasons
    c.route_to, c.requires_human_approval = d.route_to, d.requires_human_approval
    if issue and SEVERITIES.index(d.severity) > SEVERITIES.index(issue.max_severity):
        issue.max_severity = d.severity

    # 4. draft a reply with RAG + guardrails
    dr = responder.draft(db, c, category=c.category, severity=c.severity, summary=c.summary, use_llm=use_llm)
    c.draft_response, c.draft_citations, c.draft_flags = dr["text"], dr["citations"], dr["flags"]
    if dr["engine"] != "heuristic":
        c.engine = dr["engine"]

    # 5. notify
    if d.escalate:
        lvl = "critical" if d.severity == "critical" else "warning"
        target = d.route_to if d.route_to in ("finance", "operations") else "quality"  # no 'legal' user: Quality coordinates with Legal
        _notify(db, target, f"[{d.severity.upper()}] {c.summary[:90]}",
                "; ".join(d.reasons) or "Escalated by policy", lvl, c.id)
        if d.severity == "critical":
            _notify(db, "executive", f"Critical complaint #{c.id}", c.summary[:140], "critical", c.id)
    if issue and issue_n == settings.recurring_issue_threshold:
        _notify(db, "quality", f"Recurring issue detected: {issue.title}",
                f"{issue_n} similar complaints in 14 days" + (f" (lots: {', '.join(issue.lot_codes)})" if issue.lot_codes else ""),
                "warning", c.id)

    c.status = "escalated" if d.escalate else "draft_ready"
    c.processed_at, c.error = utcnow(), ""
    db.commit()
    audit(db, "system", "complaint.processed", complaint_id=c.id, engine=c.engine, severity=c.severity, category=c.category)
    return c
