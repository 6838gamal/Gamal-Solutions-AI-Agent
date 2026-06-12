import { useEffect, useState } from 'react'
import { GitBranch, Plus, Trash2, Play, ToggleLeft, ToggleRight } from 'lucide-react'
import api from '../lib/api'
import { Workflow } from '../types'

const statusColors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-600',
  active: 'bg-green-100 text-green-700',
  paused: 'bg-yellow-100 text-yellow-700',
  archived: 'bg-red-100 text-red-700',
}

const triggerLabels: Record<string, string> = {
  manual: 'يدوي', scheduled: 'مجدول', event: 'حدث', api: 'API'
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', trigger: 'manual' })

  const load = () => api.get('/workflows/').then(r => { setWorkflows(r.data); setLoading(false) })
  useEffect(() => { load() }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/workflows/', form)
    setShowForm(false)
    setForm({ name: '', description: '', trigger: 'manual' })
    load()
  }

  const remove = async (id: number) => {
    if (!confirm('حذف سير العمل؟')) return
    await api.delete(`/workflows/${id}`)
    load()
  }

  const toggleStatus = async (wf: Workflow) => {
    const newStatus = wf.status === 'active' ? 'paused' : 'active'
    await api.put(`/workflows/${wf.id}`, { status: newStatus })
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">سير العمل والأتمتة</h2>
          <p className="text-sm text-slate-500">إدارة قواعد الأعمال والعمليات الآلية</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm">
          <Plus size={16} />سير عمل جديد
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="اسم سير العمل *" className="input-field" required />
            <select value={form.trigger} onChange={e => setForm({ ...form, trigger: e.target.value })} className="input-field">
              {Object.entries(triggerLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="الوصف" className="input-field" />
            <div className="md:col-span-3 flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium">حفظ</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : workflows.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <GitBranch size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">لا توجد تدفقات عمل بعد</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {workflows.map(wf => (
            <div key={wf.id} className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                    <GitBranch size={18} className="text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800 dark:text-white text-sm">{wf.name}</h3>
                    <p className="text-xs text-slate-500">{triggerLabels[wf.trigger]}</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded-lg text-xs font-medium ${statusColors[wf.status]}`}>
                  {wf.status === 'active' ? 'نشط' : wf.status === 'draft' ? 'مسودة' : wf.status === 'paused' ? 'موقوف' : 'مؤرشف'}
                </span>
              </div>
              {wf.description && <p className="text-xs text-slate-500 dark:text-slate-400 mb-3 line-clamp-2">{wf.description}</p>}
              <div className="flex items-center gap-2 mb-3 text-xs text-slate-500">
                <Play size={12} /><span>تشغيلات: {wf.run_count}</span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => toggleStatus(wf)} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-medium transition-colors ${wf.status === 'active' ? 'bg-yellow-50 text-yellow-600 hover:bg-yellow-100' : 'bg-green-50 text-green-600 hover:bg-green-100'}`}>
                  {wf.status === 'active' ? <><ToggleRight size={14} />إيقاف</> : <><ToggleLeft size={14} />تفعيل</>}
                </button>
                <button onClick={() => remove(wf.id)} className="p-2 rounded-xl bg-red-50 text-red-500 hover:bg-red-100">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; }`}</style>
    </div>
  )
}
