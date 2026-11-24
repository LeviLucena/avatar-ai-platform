"""Evaluate the classifier + escalation policy on the labeled set.

Reports category accuracy and, most importantly, CRITICAL RECALL after the deterministic
escalation rules (a missed critical complaint is the costly failure).
"""
import sys

from app.agents import classifier, escalation
from evals.cases import CASES


def run(use_llm: bool = True) -> dict:
    ok_cat = n_cat = 0
    crit_total = crit_hit = 0
    rows = []
    for text, exp_cat, must_crit in CASES:
        a = classifier.classify(text, use_llm=use_llm)
        d = escalation.decide(category=a["category"], ai_severity=a["severity"], health_risk=a["health_risk"], text=text)
        if exp_cat:
            n_cat += 1
            ok_cat += a["category"] == exp_cat
        if must_crit:
            crit_total += 1
            crit_hit += d.severity == "critical"
        rows.append((text[:60], exp_cat, a["category"], d.severity, must_crit, a["engine"]))
    return {
        "engine": rows[0][-1], "category_accuracy": ok_cat / n_cat, "critical_recall": crit_hit / crit_total,
        "n": len(CASES), "rows": rows,
    }


if __name__ == "__main__":
    r = run(use_llm="--no-llm" not in sys.argv)
    for t, e, g, sev, mc, _ in r["rows"]:
        flag = "OK " if (e is None or e == g) and (not mc or sev == "critical") else "XX "
        print(f"{flag}{t:62s} exp={e} got={g} sev={sev}")
    print(f"\nengine={r['engine']}  category_accuracy={r['category_accuracy']:.0%}  critical_recall={r['critical_recall']:.0%}  (n={r['n']})")
