"""Tiny DB-backed job queue with an in-process worker thread (swap for Celery/ARQ + Redis at scale)."""
import logging
import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Job, utcnow

log = logging.getLogger("jobs")
MAX_ATTEMPTS = 3
_stop = threading.Event()
_thread: threading.Thread | None = None


def enqueue(db: Session, kind: str, payload: dict | None = None) -> Job:
    job = Job(kind=kind, payload=payload or {})
    db.add(job)
    db.commit()
    if settings.inline_jobs:
        run_job(db, job.id)
        db.refresh(job)
    return job


def _handlers():
    from . import pipeline
    from .agents import reporter

    return {
        "process_complaint": lambda db, p: {"complaint_id": pipeline.process_complaint(db, p["complaint_id"]).id},
        "weekly_report": lambda db, p: {"report_id": reporter.generate_report(db, days=p.get("days", 7)).id},
    }


def run_job(db: Session, job_id: int) -> None:
    job = db.get(Job, job_id)
    if job is None or job.status not in ("queued",):
        return
    job.status, job.attempts = "running", job.attempts + 1
    db.commit()
    try:
        job.result = _handlers()[job.kind](db, job.payload)
        job.status, job.error = "done", ""
    except Exception as exc:
        db.rollback()
        log.exception("job %s failed", job_id)
        job = db.get(Job, job_id)
        job.error = f"{type(exc).__name__}: {exc}"[:2000]
        job.status = "queued" if job.attempts < MAX_ATTEMPTS and not settings.inline_jobs else "failed"
        if job.kind == "process_complaint" and job.status == "failed":
            from .models import Complaint

            c = db.get(Complaint, job.payload.get("complaint_id"))
            if c:
                c.status, c.error = "failed", job.error
    job.finished_at = utcnow() if job.status in ("done", "failed") else None
    db.commit()


def run_pending(db: Session, limit: int = 1000) -> int:
    n = 0
    while n < limit:
        job = db.scalar(select(Job).where(Job.status == "queued").order_by(Job.id).limit(1))
        if job is None:
            break
        run_job(db, job.id)
        n += 1
    return n


def _loop():
    while not _stop.is_set():
        db = SessionLocal()
        try:
            job = db.scalar(select(Job).where(Job.status == "queued").order_by(Job.id).limit(1))
            if job:
                run_job(db, job.id)
                continue
        except Exception:
            log.exception("worker loop error")
        finally:
            db.close()
        time.sleep(0.5)


def start_worker() -> None:
    global _thread
    if settings.inline_jobs or (_thread and _thread.is_alive()):
        return
    # recover jobs interrupted by a crash/restart
    db = SessionLocal()
    for j in db.scalars(select(Job).where(Job.status == "running")):
        j.status = "queued"
    db.commit()
    db.close()
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="job-worker", daemon=True)
    _thread.start()


def stop_worker() -> None:
    _stop.set()
