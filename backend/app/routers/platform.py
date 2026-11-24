from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import rag
from ..config import settings
from ..db import get_db
from ..models import AuditLog, Complaint, Job, KnowledgeChunk, KnowledgeDoc, Notification, User
from ..security import audit, current_user, require_roles

router = APIRouter(prefix="/api", tags=["platform"])


# ---------------------------------------------------------------- knowledge (RAG)
@router.get("/knowledge")
def knowledge(db: Session = Depends(get_db), _: User = Depends(current_user)):
    docs = db.scalars(select(KnowledgeDoc).order_by(KnowledgeDoc.title)).all()
    counts = dict(db.execute(select(KnowledgeChunk.doc_id, func.count()).group_by(KnowledgeChunk.doc_id)).all())
    return [{"id": d.id, "title": d.title, "source": d.source, "chunks": counts.get(d.id, 0), "updated_at": d.updated_at.isoformat()} for d in docs]


@router.get("/knowledge/{did}")
def knowledge_doc(did: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    d = db.get(KnowledgeDoc, did)
    if not d:
        raise HTTPException(404, "Not found")
    return {"id": d.id, "title": d.title, "content": d.content}


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)


@router.post("/knowledge/search")
def knowledge_search(body: SearchIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    return rag.search(db, body.query, k=5)


class DocIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=20, max_length=100_000)


@router.post("/knowledge", status_code=201)
def knowledge_add(body: DocIn, db: Session = Depends(get_db), user: User = Depends(require_roles("quality"))):
    d = rag.upsert_doc(db, body.title, body.content, source="uploaded")
    audit(db, user, "knowledge.upsert", title=body.title)
    return {"id": d.id, "title": d.title}


# ---------------------------------------------------------------- notifications
@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Notification).order_by(Notification.created_at.desc()).limit(40)
    if user.role != "admin":
        q = q.where(Notification.role == user.role)
    rows = db.scalars(q).all()
    return {"unread": sum(1 for n in rows if not n.read),
            "items": [{"id": n.id, "title": n.title, "body": n.body, "level": n.level, "complaint_id": n.complaint_id, "read": n.read,
                       "created_at": n.created_at.isoformat(), "role": n.role} for n in rows]}


@router.post("/notifications/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Notification).where(Notification.read.is_(False))
    if user.role != "admin":
        q = q.where(Notification.role == user.role)
    for n in db.scalars(q):
        n.read = True
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- admin
ADMIN = require_roles()  # admin only


@router.get("/admin/audit")
def audit_log(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(ADMIN)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500))).all()
    return [{"id": r.id, "ts": r.ts.isoformat(), "actor": r.actor, "role": r.role, "action": r.action, "detail": r.detail} for r in rows]


@router.get("/admin/jobs")
def admin_jobs(db: Session = Depends(get_db), _: User = Depends(ADMIN)):
    rows = db.scalars(select(Job).order_by(Job.id.desc()).limit(60)).all()
    return [{"id": j.id, "kind": j.kind, "status": j.status, "attempts": j.attempts, "error": j.error, "created_at": j.created_at.isoformat()} for j in rows]


@router.get("/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(ADMIN)):
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role, "active": u.active} for u in db.scalars(select(User))]


@router.get("/system")
def system(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return {
        "engine": settings.engine_name,
        "model_fast": settings.model_fast, "model_smart": settings.model_smart,
        "complaints": db.scalar(select(func.count()).select_from(Complaint)),
        "queued_jobs": db.scalar(select(func.count()).select_from(Job).where(Job.status.in_(("queued", "running")))),
        "disclaimer": "Independent concept demo with fictional data. Not affiliated with Avatar Natural Foods.",
    }
