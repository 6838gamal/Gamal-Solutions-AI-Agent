export interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  department: string | null
  is_active: boolean
  is_superuser: boolean
  language: string
  created_at: string
  last_login: string | null
  roles: Role[]
}

export interface Role {
  id: number
  name: string
  description: string | null
  is_system: boolean
}

export interface Agent {
  id: number
  name: string
  name_ar: string | null
  description: string | null
  agent_type: 'sales' | 'customer_service' | 'operations' | 'executive' | 'custom'
  status: 'active' | 'inactive' | 'training' | 'maintenance'
  performance_score: number
  total_tasks: number
  successful_tasks: number
  capabilities: string[]
  created_at: string
}

export interface KnowledgeDocument {
  id: number
  title: string
  title_ar: string | null
  content: string | null
  summary: string | null
  doc_type: string
  status: string
  source: string | null
  version: string
  confidence_score: number
  tags: string[]
  category_id: number | null
  created_at: string
  updated_at: string
}

export interface Customer {
  id: number
  name: string
  email: string | null
  phone: string | null
  company: string | null
  status: 'lead' | 'prospect' | 'active' | 'inactive' | 'churned'
  score: number
  purchase_probability: number
  lifetime_value: number
  interests: string[]
  tags: string[]
  created_at: string
  updated_at: string
}

export interface Conversation {
  id: number
  customer_id: number | null
  channel: string
  status: 'open' | 'pending' | 'resolved' | 'closed'
  subject: string | null
  priority: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'agent' | 'system'
  content: string
  is_read: boolean
  created_at: string
}

export interface Workflow {
  id: number
  name: string
  name_ar: string | null
  description: string | null
  trigger: string
  status: string
  run_count: number
  last_run: string | null
  steps: any[]
  created_at: string
}

export interface Task {
  id: number
  title: string
  description: string | null
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  priority: string
  due_date: string | null
  assigned_to: number | null
  customer_id: number | null
  created_at: string
}

export interface AuditLog {
  id: number
  user_id: number | null
  action: string
  resource: string | null
  resource_id: string | null
  description: string | null
  status: string
  created_at: string
}

export interface DashboardStats {
  users: { total: number }
  agents: { total: number; active: number }
  customers: { total: number; by_status: Record<string, number> }
  conversations: { total: number; open: number }
  knowledge: { total_documents: number }
  workflows: { total: number }
  tasks: { total: number; pending: number }
}
