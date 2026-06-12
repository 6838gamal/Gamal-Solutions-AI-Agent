---
name: Enterprise AI Platform Setup
description: Key lessons from setting up FastAPI + React + Render PostgreSQL platform on Replit
---

## bcrypt / passlib incompatibility
Use `bcrypt` package directly, NOT `passlib[bcrypt]`. Passlib's detect_wrap_bug() fails with newer bcrypt versions ("password cannot be longer than 72 bytes").
```python
import bcrypt
def get_password_hash(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def verify_password(p, h): return bcrypt.checkpw(p.encode(), h.encode())
```

## SQLAlchemy Enum + PostgreSQL
Always use `native_enum=False` on all Enum columns when PostgreSQL already has those types from a previous run. Otherwise `create_all` throws UniqueViolation on pg_type.

## Backend host for Replit workflow detection
Backend uvicorn must bind to `0.0.0.0` (not `localhost`) for the Replit workflow port monitor to detect port 8000. Without this, the workflow times out even though the server is actually running.

## Non-blocking startup
Move heavy DB initialization (create_all, seed data) into a background thread during FastAPI startup to avoid port-detection timeouts:
```python
@app.on_event("startup")
def startup():
    import threading
    threading.Thread(target=init_db, daemon=True).start()
```

## Database URL env var
`DATABASE_URL` is reserved by Replit runtime. Use `DB_URL` instead.

**Why:** Replit blocks setting DATABASE_URL via setEnvVars — it's runtime-managed.
