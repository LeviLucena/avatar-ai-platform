from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import jobs
from ..agents import ops_agent
from ..agents.classifier import CATEGORIES
from ..config import settings
from ..db import get_db
from ..models import (Complaint, InventoryItem, Invoice, Job, ProductionRun, PurchaseOrder, QualityIssue, Report, User, utcnow)
from ..security import audit, current_user, require_roles

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = utcnow()
    d30, d14, d7 = now - timedelta(days=30), now - timedelta(days=14), now - timedelta(days=7)
    c30 = db.scalars(select(Complaint).where(Complaint.received_at >= d30)).all()
    total_all = db.scalar(select(func.count()).select_from(Complaint)) or 0
    processed = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.processed_at.is_not(None))) or 0
    open_status = ("escalated", "draft_ready", "new")
    sent_draft = [c for c in c30 if c.severity != "low" or c.status != "sent"]
    del sent_draft
    recurring = 0
    for iss in db.scalars(select(QualityIssue).where(QualityIssue.status != "resolved")):
        n = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.issue_id == iss.id, Complaint.received_at >= d14)) or 0
        recurring += 1 if n >= settings.recurring_issue_threshold else 0

    days = []
    for i in range(27, -1, -1):
        day = (now - timedelta(days=i)).date()
        subset = [c for c in c30 if c.received_at.date() == day] if i < 30 else []
        sev = Counter(c.severity for c in subset)
        days.append({"date": day.isoformat(), "total": len(subset), **{s: sev.get(s, 0) for s in ("low", "medium", "high", "critical")}})

    by_cat = Counter(c.category for c in c30)
    lots = Counter(c.lot_code for c in c30 if c.lot_code)
    top_issues = db.scalars(select(QualityIssue).where(QualityIssue.status != "resolved").order_by(QualityIssue.complaint_count.desc()).limit(5)).all()
    res = {
        "role": user.role,
        "llm_engine": settings.engine_name,
        "kpis": {
            "complaints_30d": len(c30),
            "complaints_7d": sum(1 for c in c30 if c.received_at >= d7),
            "critical_open": sum(1 for c in c30 if c.severity == "critical" and c.status != "sent"),
            "escalated_open": sum(1 for c in c30 if c.escalated and c.status in open_status),
            "awaiting_approval": sum(1 for c in c30 if c.status in ("escalated", "draft_ready")),
            "recurring_issues": recurring,
            "avg_sentiment_7d": round(sum(c.sentiment for c in c30 if c.received_at >= d7) / max(1, sum(1 for c in c30 if c.received_at >= d7)), 2),
            "auto_triaged_pct": round(processed / total_all * 100, 1) if total_all else 0,
        },
        "series": days,
        "by_category": [{"category": k, "label": CATEGORIES.get(k, k), "count": v} for k, v in by_cat.most_common()],
        "by_severity": dict(Counter(c.severity for c in c30)),
        "by_source": dict(Counter(c.source for c in c30)),
        "top_lots": [{"lot": k, "complaints": v} for k, v in lots.most_common(5)],
        "top_issues": [{"id": i.id, "title": i.title, "count": i.complaint_count, "severity": i.max_severity, "lots": i.lot_codes, "status": i.status} for i in top_issues],
    }
    if user.role in ("operations", "executive", "admin", "quality"):
        runs = db.scalars(select(ProductionRun).where(ProductionRun.run_date >= d14)).all()
        prod = sum(r.produced_units for r in runs)
        inv = db.scalars(select(InventoryItem)).all()
        res["operations"] = {
            "defect_rate_14d_pct": round(sum(r.defect_units for r in runs) / prod * 100, 2) if prod else 0,
            "yield_14d_pct": round(prod / max(1, sum(r.planned_units for r in runs)) * 100, 1),
            "low_stock_items": [{"name": i.name, "qty": i.qty, "unit": i.unit, "reorder_point": i.reorder_point} for i in inv if i.qty <= i.reorder_point],
            "late_pos": db.scalar(select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status == "late")) or 0,
        }
    if user.role in ("finance", "executive", "admin"):
        ar = db.scalars(select(Invoice).where(Invoice.kind == "AR", Invoice.status == "overdue")).all()
        res["finance"] = {"overdue_ar_total": round(sum(i.amount for i in ar), 2), "overdue_ar_count": len(ar)}
    return res


# ------------------------------------------------------------------ quality issues
ISSUE_READ = require_roles("support", "quality", "executive")


def issue_out(i: QualityIssue) -> dict:
    return {"id": i.id, "title": i.title, "category": i.category, "product": i.product.name if i.product else None,
            "lots": i.lot_codes, "count": i.complaint_count, "first_seen": i.first_seen.isoformat(), "last_seen": i.last_seen.isoformat(),
            "max_severity": i.max_severity, "status": i.status}


@router.get("/issues")
def issues(db: Session = Depends(get_db), _: User = Depends(ISSUE_READ)):
    rows = db.scalars(select(QualityIssue).order_by(QualityIssue.last_seen.desc())).all()
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted((issue_out(i) for i in rows), key=lambda x: (x["status"] == "resolved", rank[x["max_severity"]], -x["count"]))


@router.get("/issues/{iid}")
def issue_detail(iid: int, db: Session = Depends(get_db), _: User = Depends(ISSUE_READ)):
    i = db.get(QualityIssue, iid)
    if not i:
        raise HTTPException(404, "Not found")
    cs = db.scalars(select(Complaint).where(Complaint.issue_id == iid).order_by(Complaint.received_at.desc()).limit(50)).all()
    timeline = Counter(c.received_at.date().isoformat() for c in cs)
    runs = db.scalars(select(ProductionRun).where(ProductionRun.lot_code.in_(i.lot_codes or ["-"]))).all()
    return {**issue_out(i), "timeline": sorted(({"date": k, "count": v} for k, v in timeline.items()), key=lambda x: x["date"]),
            "complaints": [{"id": c.id, "summary": c.summary, "severity": c.severity, "status": c.status, "received_at": c.received_at.isoformat(), "lot_code": c.lot_code} for c in cs],
            "production": [{"lot": r.lot_code, "line": r.line, "date": r.run_date.date().isoformat(), "produced": r.produced_units, "defect_rate_pct": round(r.defect_units / r.produced_units * 100, 2)} for r in runs]}


class IssuePatch(BaseModel):
    status: str


@router.patch("/issues/{iid}")
def issue_patch(iid: int, body: IssuePatch, db: Session = Depends(get_db), user: User = Depends(require_roles("quality"))):
    if body.status not in ("open", "investigating", "resolved"):
        raise HTTPException(422, "Invalid status")
    i = db.get(QualityIssue, iid)
    if not i:
        raise HTTPException(404, "Not found")
    i.status = body.status
    db.commit()
    audit(db, user, "issue.status", issue_id=iid, status=body.status)
    return issue_out(i)


# ------------------------------------------------------------------ reports + jobs
REPORT_READ = require_roles("quality", "executive", "support")


@router.get("/reports")
def reports(db: Session = Depends(get_db), _: User = Depends(REPORT_READ)):
    rows = db.scalars(select(Report).order_by(Report.created_at.desc()).limit(30)).all()
    return [{"id": r.id, "kind": r.kind, "period_start": r.period_start.date().isoformat(), "period_end": r.period_end.date().isoformat(),
             "engine": r.engine, "created_at": r.created_at.isoformat(), "total": r.data.get("total")} for r in rows]


@router.get("/reports/{rid}")
def report(rid: int, db: Session = Depends(get_db), _: User = Depends(REPORT_READ)):
    r = db.get(Report, rid)
    if not r:
        raise HTTPException(404, "Not found")
    return {"id": r.id, "content_md": r.content_md, "data": r.data, "engine": r.engine, "created_at": r.created_at.isoformat(),
            "period_start": r.period_start.date().isoformat(), "period_end": r.period_end.date().isoformat()}


class ReportIn(BaseModel):
    days: int = 7


@router.post("/reports/generate", status_code=202)
def generate(body: ReportIn, db: Session = Depends(get_db), user: User = Depends(require_roles("quality", "executive"))):
    job = jobs.enqueue(db, "weekly_report", {"days": max(1, min(body.days, 90))})
    audit(db, user, "report.generate", days=body.days)
    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{jid}")
def job(jid: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    j = db.get(Job, jid)
    if not j:
        raise HTTPException(404, "Not found")
    return {"id": j.id, "kind": j.kind, "status": j.status, "result": j.result, "error": j.error}


# ------------------------------------------------------------------ ops assistant
class AskIn(BaseModel):
    question: str
    history: list[dict] = []


@router.post("/ops/ask")
def ops_ask(body: AskIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = body.question.strip()
    if not q or len(q) > 2000:
        raise HTTPException(422, "Question must be 1-2000 characters")
    hist = [{"role": m["role"], "content": str(m["content"])[:4000]} for m in body.history if m.get("role") in ("user", "assistant")]
    audit(db, user, "ops.ask", question=q[:300])
    return ops_agent.ask(db, user, q, hist)


@router.get("/ops/tools")
def ops_tools(user: User = Depends(current_user)):
    return {"role": user.role, "allowed": ops_agent.allowed_tools(user.role),
            "all": [{"name": n, "description": t["description"], "roles": sorted(t["roles"])} for n, t in ops_agent.TOOLS.items()]}
