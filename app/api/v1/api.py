from fastapi import APIRouter
from app.domains.auth.router import router as auth_router
from app.domains.agents.router import router as agents_router
from app.domains.knowledge.router import router as knowledge_router
from app.domains.customers.router import router as customers_router
from app.domains.conversations.router import router as conversations_router
from app.domains.workflows.router import router as workflows_router
from app.domains.workflows.router import task_router
from app.domains.audit.router import router as audit_router
from app.domains.analytics.router import router as analytics_router
from app.domains.telegram.router import router as telegram_router
from app.domains.api_keys.router import router as api_keys_router
from app.domains.orchestration.router import router as orchestration_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(knowledge_router)
api_router.include_router(customers_router)
api_router.include_router(conversations_router)
api_router.include_router(workflows_router)
api_router.include_router(task_router)
api_router.include_router(audit_router)
api_router.include_router(analytics_router)
api_router.include_router(telegram_router)
api_router.include_router(api_keys_router)
api_router.include_router(orchestration_router)
