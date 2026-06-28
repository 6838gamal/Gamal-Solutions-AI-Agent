---
name: Enterprise AI Platform Setup
description: Key technical constraints and fixes for the Gamal Solutions FastAPI platform on Replit.
---

## bcrypt / passlib incompatibility
Use `bcrypt` directly, NOT `passlib[bcrypt]`.
```python
import bcrypt
def get_password_hash(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): return bcrypt.checkpw(p.encode(), h.encode())
```

## SQLAlchemy Enum + PostgreSQL
Always use `native_enum=False` on all Enum columns when PostgreSQL already has those types.

## Database URL env var
`DATABASE_URL` is reserved by Replit runtime. Use `DB_URL` instead.

## CRITICAL: Startup Migration Pattern
SQLAlchemy ORM maps ALL model columns at import time. If a new column is added to a model
but the DB table doesn't have it yet, ANY query on that table fails — even a simple COUNT(*).

**Fix:** Run critical `ALTER TABLE` migrations SYNCHRONOUSLY in the startup event BEFORE
spawning the background `init_db()` thread. Otherwise FastAPI serves requests before
the background thread runs migrations, causing "column does not exist" on every query.

```python
@app.on_event("startup")
def startup():
    # 1. Synchronous: add new columns to existing tables first
    with engine.connect() as _conn:
        for _sql in _critical_alters:
            try: _conn.execute(text(_sql))
            except: pass
        _conn.commit()
    # 2. Background: full init (create new tables, seed data)
    threading.Thread(target=init_db, daemon=True).start()
```

**Why:** FastAPI resumes request serving immediately after `startup()` returns, before
any background thread finishes. New ORM-mapped columns MUST exist in DB before first request.

## Agent Types (full list as of June 2026)
sales, customer_service, market_intel, operations, hr, finance, executive, custom

## Knowledge Domains
customer_support, sales, market_intel, hr, finance, operations, product, general

## Orchestration Module
Located at `app/domains/orchestration/`:
- `engine.py` — classify_domain(), multi_agent_search(), _log_knowledge_gap()
- `router.py` — /orchestration/ask, /route, /handoff, /gaps, /routing-logs, /stats
- `models.py` — AgentRoutingLog, KnowledgeGap, AgentHandoff

DOMAIN_SIGNALS dict in engine.py contains Arabic + English keyword signals per domain.
AGENT_KNOWLEDGE_ACCESS defines which knowledge domains each agent type can read.
