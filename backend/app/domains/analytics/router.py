from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.domains.auth.models import User
from app.domains.auth import models as auth_models
from app.domains.agents import models as agent_models
from app.domains.customers import models as customer_models
from app.domains.conversations import models as conv_models
from app.domains.knowledge import models as kb_models
from app.domains.workflows import models as wf_models

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total_users = db.query(auth_models.User).count()
    total_agents = db.query(agent_models.Agent).count()
    active_agents = db.query(agent_models.Agent).filter(
        agent_models.Agent.status == agent_models.AgentStatus.ACTIVE
    ).count()
    total_customers = db.query(customer_models.Customer).count()
    total_conversations = db.query(conv_models.Conversation).count()
    open_conversations = db.query(conv_models.Conversation).filter(
        conv_models.Conversation.status == conv_models.ConversationStatus.OPEN
    ).count()
    total_documents = db.query(kb_models.KnowledgeDocument).count()
    total_workflows = db.query(wf_models.Workflow).count()
    total_tasks = db.query(wf_models.Task).count()
    pending_tasks = db.query(wf_models.Task).filter(
        wf_models.Task.status == wf_models.TaskStatus.PENDING
    ).count()

    customer_by_status = {}
    for s in customer_models.CustomerStatus:
        count = db.query(customer_models.Customer).filter(
            customer_models.Customer.status == s
        ).count()
        customer_by_status[s.value] = count

    return {
        "users": {"total": total_users},
        "agents": {"total": total_agents, "active": active_agents},
        "customers": {"total": total_customers, "by_status": customer_by_status},
        "conversations": {"total": total_conversations, "open": open_conversations},
        "knowledge": {"total_documents": total_documents},
        "workflows": {"total": total_workflows},
        "tasks": {"total": total_tasks, "pending": pending_tasks},
    }
