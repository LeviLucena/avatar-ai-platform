from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLES = ["admin", "support", "quality", "operations", "finance", "sales", "executive"]
SEVERITIES = ["low", "medium", "high", "critical"]


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------- business data
class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(40))  # frozen_meal | cookie | pita
    allergens: Mapped[str] = mapped_column(String(200), default="")


class ProductionRun(Base):
    __tablename__ = "production_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    lot_code: Mapped[str] = mapped_column(String(30), index=True)
    line: Mapped[str] = mapped_column(String(30))
    facility: Mapped[str] = mapped_column(String(30))
    run_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    planned_units: Mapped[int] = mapped_column(Integer)
    produced_units: Mapped[int] = mapped_column(Integer)
    defect_units: Mapped[int] = mapped_column(Integer)
    product: Mapped[Product] = relationship()


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(60))
    lead_time_days: Mapped[int] = mapped_column(Integer)
    on_time_rate: Mapped[float] = mapped_column(Float)


class InventoryItem(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))  # raw | packaging | finished
    qty: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    reorder_point: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(60))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(String(30), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    item_sku: Mapped[str] = mapped_column(String(40))
    qty: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))  # open | shipped | received | late
    expected_date: Mapped[datetime] = mapped_column(DateTime)
    supplier: Mapped[Supplier] = relationship()


class SalesOrder(Base):
    __tablename__ = "sales_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(30), unique=True)
    customer: Mapped[str] = mapped_column(String(120))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    amount: Mapped[float] = mapped_column(Float)
    order_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(20))
    product: Mapped[Product] = relationship()


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    kind: Mapped[str] = mapped_column(String(5))  # AR | AP
    party: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Float)
    issued: Mapped[datetime] = mapped_column(DateTime)
    due: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20))  # open | paid | overdue


# ---------------------------------------------------------------- complaints
class QualityIssue(Base):
    """A cluster of similar complaints = a recurring quality failure."""

    __tablename__ = "quality_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    lot_codes: Mapped[list] = mapped_column(JSON, default=list)
    complaint_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime)
    last_seen: Mapped[datetime] = mapped_column(DateTime)
    max_severity: Mapped[str] = mapped_column(String(10), default="low")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | investigating | resolved
    centroid: Mapped[list] = mapped_column(JSON, default=list)
    product: Mapped[Product | None] = relationship()


class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(10))  # email | web
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    customer_email: Mapped[str] = mapped_column(String(200), default="")
    subject: Mapped[str] = mapped_column(String(300), default="")
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    # new | triaged | escalated | draft_ready | sent | closed | failed

    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    lot_code: Mapped[str] = mapped_column(String(30), default="", index=True)
    category: Mapped[str] = mapped_column(String(40), default="", index=True)
    severity: Mapped[str] = mapped_column(String(10), default="low", index=True)
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    health_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(10), default="en")
    engine: Mapped[str] = mapped_column(String(20), default="")  # claude | heuristic

    issue_id: Mapped[int | None] = mapped_column(ForeignKey("quality_issues.id"), nullable=True, index=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reasons: Mapped[list] = mapped_column(JSON, default=list)
    route_to: Mapped[str] = mapped_column(String(30), default="support")

    draft_response: Mapped[str] = mapped_column(Text, default="")
    draft_citations: Mapped[list] = mapped_column(JSON, default=list)
    draft_flags: Mapped[list] = mapped_column(JSON, default=list)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by: Mapped[str] = mapped_column(String(120), default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    embedding: Mapped[list] = mapped_column(JSON, default=list)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")

    product: Mapped[Product | None] = relationship()
    issue: Mapped[QualityIssue | None] = relationship()


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(10), default="info")
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- RAG / reports / ops
class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), unique=True)
    source: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("knowledge_docs.id", ondelete="CASCADE"), index=True)
    heading: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON, default=list)
    doc: Mapped[KnowledgeDoc] = relationship()


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), default="weekly_quality")
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    content_md: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    engine: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="")
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(15), default="queued", index=True)  # queued|running|done|failed
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
