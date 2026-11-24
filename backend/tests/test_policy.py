"""Pure-logic tests: escalation policy, guardrails, classifier evaluation set."""
from app.agents import classifier, escalation, responder
from evals.run_eval import run


def decide(**kw):
    base = dict(category="taste_texture", ai_severity="low", health_risk=False, text="too salty")
    return escalation.decide(**{**base, **kw})


def test_model_cannot_downgrade_health_risk():
    d = decide(category="foreign_object", ai_severity="low", health_risk=True, text="I got sick")
    assert d.severity == "critical" and d.escalate and d.route_to == "quality"


def test_allergen_is_always_critical():
    assert decide(category="allergen_labeling", ai_severity="low").severity == "critical"


def test_metal_and_glass_critical_plastic_high():
    assert decide(category="foreign_object", text="piece of glass").severity == "critical"
    assert decide(category="foreign_object", text="hard plastic").severity == "high"


def test_lot_cluster_escalates_low_taste_complaint():
    d = decide(lot_complaints_30d=3)
    assert d.severity == "high" and d.escalate


def test_legal_language_routes_to_legal():
    d = decide(text="I will call my lawyer", category="billing")
    assert d.route_to == "legal" and d.escalate


def test_billing_is_routed_to_finance_and_not_escalated():
    d = decide(category="billing", text="charged twice")
    assert d.route_to == "finance" and not d.escalate


def test_praise_not_escalated():
    assert not decide(category="praise_other", text="love it").escalate


def test_guardrails_block_liability_money_and_recall():
    assert "admits liability" in responder.check_draft("This was our fault.", "low")
    assert "mentions a money amount" in responder.check_draft("We will pay $500", "low")
    assert "mentions recall" in responder.check_draft("There is a recall", "low")
    assert "claims product is safe" in responder.check_draft("The product is safe to eat", "low")
    assert responder.check_draft("Hi Ana, we are sorry. Our Quality team will contact you.", "critical") == []


def test_critical_draft_must_mention_quality():
    assert responder.check_draft("We are sorry about that.", "critical")


def test_lot_extraction():
    assert classifier.extract_lot("lot CC-2611-B was bad") == "CC-2611-B"
    assert classifier.extract_lot("batch code: XY12345") == "XY12345"
    assert classifier.extract_lot("nothing here") == ""


def test_classifier_eval_set_thresholds():
    r = run(use_llm=False)
    assert r["critical_recall"] == 1.0  # a missed critical complaint is the costly failure
    assert r["category_accuracy"] >= 0.9
