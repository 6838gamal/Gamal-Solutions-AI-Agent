# Gamal Solutions – Enterprise AI Platform

A full-stack Business Intelligence & AI Automation Platform (العقل الرقمي المؤسسي).

## Architecture

- **Frontend**: React 18 + Vite + Tailwind CSS — port 5000
- **Backend**: FastAPI + SQLAlchemy — port 8000
- **Database**: PostgreSQL (Render cloud) via `DB_URL` env var
- **Language**: Arabic RTL UI with Cairo font

## Running the Project

1. **Backend** (`Backend API` workflow): `cd backend && python3 run.py`
2. **Frontend** (`Start application` workflow): `cd frontend && npm run dev`

## Default Login

- Username: `admin`
- Password: `Admin@2024!`

## Modules

| Domain | Description |
|--------|-------------|
| Auth + RBAC | JWT auth, users, roles, permissions |
| AI Agents | Sales, Customer Service, Operations, Executive agents |
| Knowledge Base | Documents, categories, search |
| Customers | CRM with scoring and opportunities |
| Conversations | Multi-channel messaging hub |
| Workflows | Business process automation |
| Tasks | Task management and tracking |
| Analytics | Dashboard stats and charts |
| Audit Logs | Full audit trail |

## Pages

Login → Dashboard → Agents → Knowledge → Customers → Conversations → Workflows → Tasks → Analytics → Audit Logs → Users → Settings

## User Preferences

- Arabic RTL interface as primary language
- Enterprise-grade design with blue color scheme
- Cairo font for Arabic typography
