"""API tests: auth, role-based access, ingestion pipeline, approval rules, ops-agent permissions, reports."""
import pytest

CRITICAL = "I ate the Birria Rice Bowl, lot BR-2611-A, and got sick, vomiting all night. I think it was spoiled."


def test_unauthenticated_is_rejected(client):
    assert client.get("/api/complaints").status_code == 401
    assert client.get("/api/dashboard").status_code == 401


def test_bad_login(client):
    assert client.post("/api/auth/login", json={"email": "admin@demo.local", "password": "nope"}).status_code == 401


def test_rbac_matrix(client, tokens):
    assert client.get("/api/complaints", headers=tokens["finance"]).status_code == 403
    assert client.get("/api/complaints", headers=tokens["support"]).status_code == 200
    assert client.get("/api/admin/audit", headers=tokens["quality"]).status_code == 403
    assert client.get("/api/admin/audit", headers=tokens["admin"]).status_code == 200
    assert client.post("/api/reports/generate", json={}, headers=tokens["support"]).status_code == 403


def test_seeded_data_has_recurring_issue_and_criticals(client, tokens):
    issues = client.get("/api/issues", headers=tokens["quality"]).json()
    top = issues[0]
    assert top["count"] >= 5 and top["max_severity"] in ("critical", "high")
    crit = client.get("/api/complaints?severity=critical", headers=tokens["quality"]).json()
    assert crit["total"] >= 3


def test_web_form_is_processed_and_escalated(client, tokens):
    r = client.post("/api/ingest/web", json={"name": "Test Person", "email": "t@example.com", "subject": "sick", "message": CRITICAL})
    assert r.status_code == 202
    c = client.get(f"/api/complaints/{r.json()['id']}", headers=tokens["quality"]).json()
    assert c["severity"] == "critical" and c["escalated"] and c["route_to"] == "quality"
    assert c["lot_code"] == "BR-2611-A" and c["product"] == "Birria Rice Bowl"
    assert c["draft_response"] and "Quality" in c["draft_response"]
    assert c["lot_production"]["lot"] == "BR-2611-A"
    assert c["issue"] is not None


def test_web_form_validation(client):
    assert client.post("/api/ingest/web", json={"name": "x", "email": "x", "message": "short"}).status_code == 422


def test_email_webhook_requires_key(client):
    body = {"from_name": "A B", "from_email": "a@b.com", "subject": "s", "body": "My order is late, tracking not updated."}
    assert client.post("/api/ingest/email", json=body).status_code == 401
    assert client.post("/api/ingest/email", json=body, headers={"X-Ingest-Key": "dev-ingest-key"}).status_code == 202


def test_eml_upload(client, tokens):
    eml = b"From: Jane Doe <jane@example.com>\nSubject: Billing\nContent-Type: text/plain\n\nI was charged twice for order SO-12345, please refund.\n"
    r = client.post("/api/ingest/eml", files=[("files", ("a.eml", eml, "message/rfc822"))], headers=tokens["support"])
    assert r.status_code == 202 and len(r.json()["ids"]) == 1
    c = client.get(f"/api/complaints/{r.json()['ids'][0]}", headers=tokens["support"]).json()
    assert c["category"] == "billing" and c["customer_name"] == "Jane Doe"


def test_high_severity_reply_requires_quality_approval(client, tokens):
    cid = client.post("/api/ingest/web", json={"name": "Z Z", "email": "z@example.com", "message": CRITICAL}).json()["id"]
    assert client.post(f"/api/complaints/{cid}/approve", headers=tokens["support"]).status_code == 403
    r = client.post(f"/api/complaints/{cid}/approve", headers=tokens["quality"])
    assert r.status_code == 200 and r.json()["status"] == "sent" and r.json()["approved_by"] == "quality@demo.local"
    assert client.post(f"/api/complaints/{cid}/approve", headers=tokens["quality"]).status_code == 409
    assert client.patch(f"/api/complaints/{cid}", json={"draft_response": "x"}, headers=tokens["quality"]).status_code == 409


def test_low_severity_reply_can_be_approved_by_support(client, tokens):
    cid = client.post("/api/ingest/web", json={"name": "L L", "email": "l@example.com", "message": "Love the cookies, thank you!"}).json()["id"]
    c = client.get(f"/api/complaints/{cid}", headers=tokens["support"]).json()
    assert c["severity"] == "low" and not c["escalated"]
    assert client.patch(f"/api/complaints/{cid}", json={"draft_response": "Thank you!"}, headers=tokens["support"]).status_code == 200
    assert client.post(f"/api/complaints/{cid}/approve", headers=tokens["support"]).json()["status"] == "sent"


def test_notifications_reach_quality_role(client, tokens):
    n = client.get("/api/notifications", headers=tokens["quality"]).json()
    assert n["unread"] > 0
    assert client.get("/api/notifications", headers=tokens["sales"]).json()["items"] == []


def test_ops_agent_respects_roles(client, tokens):
    ok = client.post("/api/ops/ask", json={"question": "Which items are below reorder point?"}, headers=tokens["operations"]).json()
    assert ok["trace"][0]["tool"] == "get_inventory" and ok["trace"][0]["ok"] and "LOW" in ok["answer"]
    denied = client.post("/api/ops/ask", json={"question": "Show overdue invoices"}, headers=tokens["operations"]).json()
    assert denied["trace"][0]["ok"] is False and "can't help" in denied["answer"]
    fin = client.post("/api/ops/ask", json={"question": "Show overdue invoices"}, headers=tokens["finance"]).json()
    assert fin["trace"][0]["ok"] is True
    tools = client.get("/api/ops/tools", headers=tokens["sales"]).json()["allowed"]
    assert "get_sales_summary" in tools and "get_invoices" not in tools


def test_ops_tool_cannot_be_forged(db_session=None):
    from app.agents import ops_agent
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        sales = db.query(User).filter_by(role="sales").first()
        with pytest.raises(ops_agent.ToolDenied):
            ops_agent.call_tool(db, sales, "get_invoices", {})
        with pytest.raises(ops_agent.ToolDenied):
            ops_agent.call_tool(db, sales, "drop_table", {})


def test_report_generation(client, tokens):
    j = client.post("/api/reports/generate", json={"days": 7}, headers=tokens["quality"]).json()
    assert client.get(f"/api/jobs/{j['job_id']}", headers=tokens["quality"]).json()["status"] == "done"
    reps = client.get("/api/reports", headers=tokens["executive"]).json()
    rep = client.get(f"/api/reports/{reps[0]['id']}", headers=tokens["executive"]).json()
    assert "Executive summary" in rep["content_md"] and rep["data"]["total"] > 0


def test_dashboard_sections_depend_on_role(client, tokens):
    ex = client.get("/api/dashboard", headers=tokens["executive"]).json()
    assert "operations" in ex and "finance" in ex and ex["kpis"]["complaints_30d"] > 0
    sup = client.get("/api/dashboard", headers=tokens["support"]).json()
    assert "operations" not in sup and "finance" not in sup


def test_knowledge_search(client, tokens):
    r = client.post("/api/knowledge/search", json={"query": "undeclared allergen reaction"}, headers=tokens["support"]).json()
    assert r and "Allergen" in r[0]["doc"]
