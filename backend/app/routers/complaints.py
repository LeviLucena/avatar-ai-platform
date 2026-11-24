import random
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_, select, func
from sqlalchemy.orm import Session

from .. import jobs, pipeline, synthetic
from ..config import settings
from ..db import get_db
from ..embeddings import cosine
from ..models import Complaint, ProductionRun, QualityIssue, User, utcnow
from ..security import audit, require_roles

router = APIRouter(prefix="/api", tags=["complaints"])
READ = require_roles("support", "quality", "executive")
WRITE = require_roles("support", "quality")


def out(c: Complaint, detail: bool = False) -> dict:
    d = {
        "id": c.id, "source": c.source, "customer_name": c.customer_name, "customer_email": c.customer_email,
        "subject": c.subject, "received_at": c.received_at.isoformat(), "status": c.status, "category": c.category,
        "severity": c.severity, "sentiment": c.sentiment, "health_risk": c.health_risk, "summary": c.summary,
        "product": c.product.name if c.product else None, "lot_code": c.lot_code, "issue_id": c.issue_id,
        "escalated": c.escalated, "route_to": c.route_to, "engine": c.engine,
    }
    if detail:
        d.update(body=c.body, escalation_reasons=c.escalation_reasons, draft_response=c.draft_response,
                 draft_citations=c.draft_citations, draft_flags=c.draft_flags, approved_by=c.approved_by,
                 sent_at=c.sent_at.isoformat() if c.sent_at else None, language=c.language, error=c.error,
                 requires_human_approval=c.requires_human_approval)
    return d


@router.get("/complaints")
def list_complaints(
    status: str | None = None, severity: str | None = None, category: str | None = None, q: str | None = None,
    issue_id: int | None = None, lot: str | None = None, escalated: bool | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db), _: User = Depends(READ),
):
    stmt = select(Complaint)
    for col, val in ((Complaint.status, status), (Complaint.severity, severity), (Complaint.category, category),
                     (Complaint.issue_id, issue_id), (Complaint.lot_code, lot), (Complaint.escalated, escalated)):
        if val not in (None, ""):
            stmt = stmt.where(col == val)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Complaint.subject.ilike(like), Complaint.body.ilike(like), Complaint.customer_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(desc(Complaint.received_at)).limit(page_size).offset((page - 1) * page_size)).all()
    return {"total": total, "page": page, "items": [out(c) for c in rows]}


@router.get("/complaints/{cid}")
def get_complaint(cid: int, db: Session = Depends(get_db), _: User = Depends(READ)):
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Not found")
    res = out(c, detail=True)
    sims = []
    if c.embedding:
        pool = db.scalars(select(Complaint).where(Complaint.id != c.id, Complaint.category == c.category).order_by(desc(Complaint.received_at)).limit(300)).all()
        sims = sorted(((cosine(c.embedding, o.embedding), o) for o in pool), key=lambda t: -t[0])[:5]
    res["similar"] = [{"id": o.id, "score": round(s, 2), "summary": o.summary, "lot_code": o.lot_code, "received_at": o.received_at.isoformat()} for s, o in sims if s > 0.2]
    iss = db.get(QualityIssue, c.issue_id) if c.issue_id else None
    res["issue"] = {"id": iss.id, "title": iss.title, "count": iss.complaint_count, "status": iss.status, "lots": iss.lot_codes} if iss else None
    if c.lot_code:
        runs = db.scalars(select(ProductionRun).where(ProductionRun.lot_code == c.lot_code)).all()
        if runs:
            prod = sum(r.produced_units for r in runs)
            res["lot_production"] = {"lot": c.lot_code, "runs": len(runs), "produced": prod,
                                     "defect_rate_pct": round(sum(r.defect_units for r in runs) / prod * 100, 2) if prod else 0,
                                     "line": runs[0].line, "facility": runs[0].facility, "date": runs[0].run_date.date().isoformat()}
    return res


class PatchIn(BaseModel):
    draft_response: str | None = None
    category: str | None = None
    severity: str | None = None


@router.patch("/complaints/{cid}")
def patch_complaint(cid: int, body: PatchIn, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Not found")
    if c.status == "sent":
        raise HTTPException(409, "Reply already sent")
    changes = body.model_dump(exclude_none=True)
    if "severity" in changes and changes["severity"] not in ("low", "medium", "high", "critical"):
        raise HTTPException(422, "Invalid severity")
    for k, v in changes.items():
        setattr(c, k, v)
    db.commit()
    audit(db, user, "complaint.edit", complaint_id=cid, fields=list(changes))
    return out(c, detail=True)


@router.post("/complaints/{cid}/approve")
def approve(cid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Not found")
    if c.status == "sent":
        raise HTTPException(409, "Already sent")
    if c.severity in ("high", "critical") and user.role not in ("quality", "admin"):
        raise HTTPException(403, "High/critical replies must be approved by Quality")
    if not c.draft_response.strip():
        raise HTTPException(422, "Empty draft")
    c.status, c.approved_by, c.sent_at = "sent", user.email, utcnow()  # outbound email is simulated
    db.commit()
    audit(db, user, "complaint.reply_sent", complaint_id=cid, severity=c.severity)
    return out(c, detail=True)


@router.post("/complaints/{cid}/reprocess")
def reprocess(cid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Not found")
    if c.status == "sent":
        raise HTTPException(409, "Already sent")
    c.status = "new"
    db.commit()
    jobs.enqueue(db, "process_complaint", {"complaint_id": cid})
    audit(db, user, "complaint.reprocess", complaint_id=cid)
    return {"queued": True}


# ------------------------------------------------------------------ ingestion
class WebForm(BaseModel):
    name: str = Field(max_length=120)
    email: str = Field(max_length=200)
    subject: str = Field("", max_length=300)
    message: str = Field(min_length=10, max_length=5000)


class EmailIn(BaseModel):
    from_name: str = ""
    from_email: str = ""
    subject: str = ""
    body: str = Field(min_length=5, max_length=20000)


@router.post("/ingest/web", status_code=202)
def ingest_web(form: WebForm, db: Session = Depends(get_db)):
    """Public endpoint behind the website's contact form."""
    c = pipeline.ingest(db, source="web", body=form.message, subject=form.subject, customer_name=form.name, customer_email=form.email)
    return {"id": c.id, "status": c.status}


@router.post("/ingest/email", status_code=202)
def ingest_email(body: EmailIn, x_ingest_key: str = Header(default=""), db: Session = Depends(get_db)):
    """Webhook for an inbound-mail provider (shared secret in X-Ingest-Key)."""
    if x_ingest_key != settings.ingest_key:
        raise HTTPException(401, "Bad ingest key")
    c = pipeline.ingest(db, source="email", body=body.body, subject=body.subject, customer_name=body.from_name, customer_email=body.from_email)
    return {"id": c.id, "status": c.status}


@router.post("/ingest/eml", status_code=202)
async def ingest_eml(files: list[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(WRITE)):
    ids = []
    for f in files[:50]:
        raw = await f.read()
        if len(raw) > 2_000_000:
            raise HTTPException(413, f"{f.filename} is too large")
        msg = BytesParser(policy=policy.default).parsebytes(raw)
        part = msg.get_body(preferencelist=("plain", "html"))
        text = part.get_content() if part else ""
        name, addr = parseaddr(str(msg.get("From", "")))
        if len(text.strip()) < 5:
            continue
        ids.append(pipeline.ingest(db, source="email", body=text, subject=str(msg.get("Subject", "")), customer_name=name, customer_email=addr).id)
    audit(db, user, "ingest.eml", count=len(ids))
    return {"ids": ids}


@router.post("/ingest/simulate", status_code=202)
def simulate(n: int = Query(5, ge=1, le=50), db: Session = Depends(get_db), user: User = Depends(WRITE)):
    rng = random.Random()
    ids = [pipeline.ingest(db, **synthetic.make_live_complaint(rng)).id for _ in range(n)]
    audit(db, user, "ingest.simulate", count=n)
    return {"ids": ids}
