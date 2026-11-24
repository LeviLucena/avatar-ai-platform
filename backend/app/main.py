import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import jobs
from .config import settings
from .db import SessionLocal
from .routers import auth, complaints, insights, platform
from .seed import ensure_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


def _weekly_report_job():
    with SessionLocal() as db:
        jobs.enqueue(db, "weekly_report", {"days": 7})


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_seed(settings.seed_demo)
    jobs.start_worker()
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(_weekly_report_job, "cron", day_of_week="mon", hour=11, minute=0, id="weekly_report")  # Monday 08:00 BRT
    sched.start()
    log.info("Started. LLM engine: %s", settings.engine_name)
    yield
    sched.shutdown(wait=False)
    jobs.stop_worker()


app = FastAPI(title="Customer Quality AI Platform (concept demo)", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
for r in (auth, complaints, insights, platform):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": settings.engine_name}
