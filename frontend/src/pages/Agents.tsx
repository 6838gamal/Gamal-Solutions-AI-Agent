import { useEffect, useState } from 'react'
import { Bot, Plus, Trash2, Edit2, Play, Pause, CheckCircle, AlertCircle } from 'lucide-react'
import api from '../lib/api'
import { Agent } from '../types'

const agentTypeLabels: Record<string, string> = {
  sales: 'وكيل المبيعات',
  customer_service: 'خدمة العملاء',
  operations: 'العمليات',
  executive: 'التنفيذي',
  custom: 'مخصص',
}

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  inactive: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  training: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  maintenance: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

const defaultAgents = [
  { name: 'وكيل المبيعات', name_ar: 'Sales Agent', agent_type: 'sales', description: 'يتولى إدارة العملاء المحتملين وإنشاء عروض الأسعار ومتابعة الفرص البيعية' },
  { name: 'وكيل خدمة العملاء', name_ar: 'Customer Service Agent', agent_type: 'customer_service', description: 'يرد على استفسارات العملاء ويصنف المشكلات ويتابع الحل' },
  { name: 'وكيل العمليات', name_ar: 'Operations Agent', agent_type: 'operations', description: 'يراقب العمليات ويتابع المهام ويكشف التأخير وينشئ التنبيهات' },
  { name: 'الوكيل التنفيذي', name_ar: 'Executive Agent', agent_type: 'executive', description: 'يحلل البيانات ويعد التقارير ويكشف المخاطر ويقدم التوصيات الاستراتيجية' },
]

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', name_ar: '', agent_type: 'sales', description: '' })

  const load = () => {
    api.get('/agents/').then(r => {
      setAgents(r.data)
      setLoading(false)
    })
  }

  useEffect(() => { load() }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/agents/', form)
    setShowForm(false)
    setForm({ name: '', name_ar: '', agent_type: 'sales', description: '' })
    load()
  }

  const remove = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا الوكيل؟')) return
    await api.delete(`/agents/${id}`)
    load()
  }

  const toggle = async (agent: Agent) => {
    const newStatus = agent.status === 'active' ? 'inactive' : 'active'
    await api.put(`/agents/${agent.id}`, { status: newStatus })
    load()
  }

  const seedDefaults = async () => {
    for (const a of defaultAgents) {
      await api.post('/agents/', a).catch(() => {})
    }
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">الوكلاء الذكيون</h2>
          <p className="text-sm text-slate-500 mt-1">إدارة وتكوين وكلاء الذكاء الاصطناعي</p>
        </div>
        <div className="flex gap-2">
          {agents.length === 0 && !loading && (
            <button onClick={seedDefaults} className="flex items-center gap-2 px-4 py-2 border border-blue-200 text-blue-600 rounded-xl text-sm font-medium hover:bg-blue-50">
              إضافة الوكلاء الافتراضيين
            </button>
          )}
          <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm">
            <Plus size={16} />
            وكيل جديد
          </button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4">إضافة وكيل جديد</h3>
          <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="اسم الوكيل (عربي)" className="input-field" required />
            <input value={form.name_ar} onChange={e => setForm({ ...form, name_ar: e.target.value })} placeholder="Agent Name (English)" className="input-field" />
            <select value={form.agent_type} onChange={e => setForm({ ...form, agent_type: e.target.value })} className="input-field">
              {Object.entries(agentTypeLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="وصف الوكيل" className="input-field" />
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">حفظ</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : agents.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <Bot size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500 font-medium">لا يوجد وكلاء بعد</p>
          <p className="text-slate-400 text-sm mt-1">أضف وكيلاً جديداً أو استخدم الوكلاء الافتراضيين</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {agents.map(agent => (
            <div key={agent.id} className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
                    <Bot size={22} className="text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-800 dark:text-white text-sm">{agent.name}</h3>
                    <p className="text-xs text-slate-500">{agentTypeLabels[agent.agent_type]}</p>
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${statusColors[agent.status]}`}>
                  {agent.status === 'active' ? 'نشط' : agent.status === 'inactive' ? 'غير نشط' : agent.status === 'training' ? 'تدريب' : 'صيانة'}
                </span>
              </div>

              {agent.description && (
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-4 leading-relaxed line-clamp-2">{agent.description}</p>
              )}

              <div className="grid grid-cols-2 gap-2 mb-4 text-center">
                <div className="bg-slate-50 dark:bg-slate-700 rounded-xl py-2">
                  <p className="text-lg font-bold text-slate-800 dark:text-white">{agent.total_tasks}</p>
                  <p className="text-xs text-slate-500">مهمة</p>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700 rounded-xl py-2">
                  <p className="text-lg font-bold text-slate-800 dark:text-white">{(agent.performance_score * 100).toFixed(0)}%</p>
                  <p className="text-xs text-slate-500">الأداء</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={() => toggle(agent)} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-medium transition-colors ${agent.status === 'active' ? 'bg-orange-50 text-orange-600 hover:bg-orange-100 dark:bg-orange-900/20' : 'bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-900/20'}`}>
                  {agent.status === 'active' ? <><Pause size={14} />إيقاف</> : <><Play size={14} />تشغيل</>}
                </button>
                <button onClick={() => remove(agent.id)} className="p-2 rounded-xl bg-red-50 text-red-500 hover:bg-red-100 dark:bg-red-900/20 transition-colors">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }`}</style>
    </div>
  )
}
