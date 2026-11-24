# Customer Quality AI Platform — concept demo

A multi-agent AI system for the **customer complaint → quality insight** workflow, with extra operations and executive
modules built on the same foundation. Built as a portfolio project for an *AI Backend Engineer* role.

> **Disclaimer:** independent project with 100% fictional data. Not affiliated with or endorsed by any company. The colors
> are inspired by natural-food branding and are **not** anyone's official palette.

## What it does

```
email (webhook / .eml) ──┐
website form  ───────────┼─► job queue ─► PIPELINE ─► inbox, dashboard, reports
simulator ───────────────┘                  │
                                            ├─ 1. Classifier (LLM, structured output / forced tool call)
                                            ├─ 2. Product / lot linking (+ production records)
                                            ├─ 3. Embedding clustering → recurring quality failures
                                            ├─ 4. DETERMINISTIC escalation policy (can only raise severity)
                                            ├─ 5. Reply drafter (RAG over policies + guardrails)
                                            └─ 6. Role-based notifications
Weekly report: numbers computed in code; the AI only writes the narrative (every Monday 08:00, or on demand).
Operations assistant: tool-using agent over inventory, production, sales, finance and purchasing, gated by role (RBAC).
```

### Engineering decisions worth highlighting
| Topic | Decision |
|---|---|
| AI + rules | The LLM *suggests* severity; business rules *decide*. A model mistake cannot hide a critical case (`agents/escalation.py`). |
| Agent security | The model never writes SQL: it only calls parameterised, read-only tools. The tool list is filtered by role **and** every call is re-checked server-side and audited (`agents/ops_agent.py`). |
| Guardrails | Drafts that admit liability or mention money amounts, recalls or "safe to eat" are blocked and replaced by an approved template. High/critical replies are only sent after human approval by the Quality role. |
| Prompt injection | Customer text is delimited in `<complaint>` tags and treated as untrusted data. |
| Resilience | Every agent has a deterministic fallback: with no API key (or on an API error) the system keeps working in `heuristic` mode. A badge in the UI shows which engine analysed each item. |
| Queue | Table-backed jobs with an in-process worker thread, retries and crash recovery. Swapping in Celery/ARQ + Redis is isolated to `jobs.py`. |
| Evaluation | `evals/` measures category accuracy and **critical recall** on a hand-labeled set. |
| Observability | Audit log, job status, per-complaint error capture. |

## Run locally

Prerequisites: Python 3.11+ and Node 20+.

```powershell
.\start.ps1
```
This starts the API on `:8000` (docs at `/docs`) and the app at **http://localhost:5173**. On first start it creates users,
the knowledge base and ~80 fictional complaints (≈15 s). Demo accounts (password `demo1234`): `admin@`, `support@`,
`quality@`, `ops@`, `finance@`, `sales@`, `exec@` + `demo.local`. Each role sees different data.

Manual:
```powershell
cd backend;  python -m venv .venv;  .\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
cd frontend; npm install; npm run dev
```

### Using a real LLM (NVIDIA Nemotron)
```powershell
cd backend; copy .env.example .env      # edit and set NVIDIA_API_KEY=nvapi-...
```
Restart the API. The badge changes from `heuristic` to `✦ Nemotron`. Models (NVIDIA's hosted, OpenAI-compatible API):
`nvidia/nemotron-3.5-lightning-30b-a3b` (fast: classification) and `nvidia/nemotron-3-ultra-550b-a55b` (drafts, agent, report).
You can switch provider with `LLM_PROVIDER=anthropic` plus `ANTHROPIC_API_KEY`. To reprocess a complaint, use the
**Re-run AI** button, or create new ones with **Intake → Simulate**. The seeded complaints were analysed in heuristic mode.

### Tests and evaluation
```powershell
cd backend
.\.venv\Scripts\python -m pytest -q                 # 27 tests: rules, guardrails, RBAC, pipeline, API
.\.venv\Scripts\python -m evals.run_eval --no-llm   # heuristic only
.\.venv\Scripts\python -m evals.run_eval            # with the LLM, if a key is set
```

## Suggested demo walkthrough
1. **Dashboard** (as `exec`): KPIs, trend, the recurring failure on lot `CC-2611-B`, defect rate and low stock.
2. **Quality issues → Foreign object: Chipotle Chicken Bowl**: the complaint cluster plus the lot's production record (≈3% defects vs ≈1% normal).
3. **Complaints → a critical one** (as `quality`): analysis, the rules that escalated it, a draft with cited sources, approve and send.
4. Sign in as `support` and try to approve a critical reply → **403**. That is a business rule, not just UI.
5. **Intake → Simulate** and watch the worker process items live; open `/contact` (the public customer form).
6. **Ops assistant**: ask "Which items are below reorder point?" as `ops`; ask "Show overdue invoices" as `ops` (denied) and as `finance` (allowed).
7. **Reports → Generate report**.

## Structure
```
backend/app
  agents/   classifier · escalation · responder (RAG + guardrails) · reporter · ops_agent (tool use + RBAC)
  llm.py    multi-provider wrapper (NVIDIA Nemotron / Anthropic): structured output, completion, tool-use loop
  pipeline.py  jobs.py  rag.py  embeddings.py  security.py  seed.py  synthetic.py
  routers/  auth · complaints (+ingest) · insights (dashboard, issues, reports, ops) · platform (knowledge, notifications, admin)
backend/data/knowledge   fictional SOP / policy documents used for RAG
backend/evals  backend/tests
frontend/src  React + TypeScript + Vite (Recharts)
```

## Honest limitations
- Embeddings are local (hashing of unigrams/bigrams): good for grouping similar complaints, but not semantic like a dedicated
  model. Production path: a hosted embeddings model + **pgvector** (only `embeddings.py` / `rag.py` change).
- SQLite by default so it runs without Docker; the models are SQLAlchemy and accept PostgreSQL via `DATABASE_URL`.
- Outbound email is simulated and there is no real ERP integration (production, inventory and finance data are synthetic).
- Authentication is JWT with demo users; SSO, rate limiting and secret rotation are missing for production use.
- Automated tests cover the heuristic mode. The Nemotron path was validated manually (classification, drafting, tool-using agent,
  report) but has no automated test.
