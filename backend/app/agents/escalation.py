"""Deterministic escalation policy.

The LLM *suggests* a severity; business rules *decide*. The final severity is never
lower than what the rules require, so a model mistake cannot hide a critical case.
"""
import re
from dataclasses import dataclass, field

from ..config import settings
from .classifier import QUALITY_CATEGORIES, SEV_ORDER

SEV_NAMES = {v: k for k, v in SEV_ORDER.items()}
LEGAL = re.compile(r"\b(lawyer|attorney|sue\b|suing|lawsuit|legal action|fda|health department|news|reporter|media|class action)\b", re.I)
HARD_HAZARD = re.compile(r"\b(metal|glass|shard|wire|blade|chipped a tooth|broke a tooth)\b", re.I)
MOLD = re.compile(r"\b(mold|moldy|mouldy|fuzzy)\b", re.I)


@dataclass
class Decision:
    severity: str
    escalate: bool
    reasons: list[str] = field(default_factory=list)
    route_to: str = "support"
    requires_human_approval: bool = True


def _max(a: str, b: str) -> str:
    return a if SEV_ORDER[a] >= SEV_ORDER[b] else b


def decide(
    *,
    category: str,
    ai_severity: str,
    health_risk: bool,
    text: str,
    lot_complaints_30d: int = 0,
    issue_count_14d: int = 0,
) -> Decision:
    sev = ai_severity if ai_severity in SEV_ORDER else "low"
    reasons: list[str] = []
    route = "support"

    if health_risk:
        sev = _max(sev, "critical")
        reasons.append("Customer reports illness, injury or an allergic reaction")
    if category == "allergen_labeling":
        sev = _max(sev, "critical")
        reasons.append("Possible undeclared allergen / labeling error")
    if category == "foreign_object":
        sev = _max(sev, "critical" if HARD_HAZARD.search(text) else "high")
        reasons.append("Foreign object reported in product")
    if category == "spoilage_freshness" and MOLD.search(text):
        sev = _max(sev, "high")
        reasons.append("Mold reported")
    if LEGAL.search(text):
        sev = _max(sev, "high")
        reasons.append("Legal / regulatory / media language detected")
        route = "legal"
    if category in QUALITY_CATEGORIES and lot_complaints_30d >= settings.lot_cluster_threshold:
        sev = _max(sev, "high")
        reasons.append(f"{lot_complaints_30d} complaints on the same lot in 30 days")
    if issue_count_14d >= settings.recurring_issue_threshold:
        sev = _max(sev, "high")
        reasons.append(f"Recurring issue: {issue_count_14d} similar complaints in 14 days")

    if route == "legal":
        pass  # legal/regulatory language always wins the routing
    elif sev == "critical" or (sev == "high" and category in QUALITY_CATEGORIES):
        route = "quality"
    elif category == "billing":
        route = "finance"
    elif category in ("cold_chain", "shipping_delivery") and issue_count_14d >= 3:
        route = "operations"
        reasons.append("Repeated transport-related complaints: route to Operations / Logistics")

    escalate = SEV_ORDER[sev] >= SEV_ORDER["high"]
    # Critical / high-risk replies are never auto-sent: a human must approve.
    return Decision(severity=sev, escalate=escalate, reasons=reasons, route_to=route, requires_human_approval=True)
