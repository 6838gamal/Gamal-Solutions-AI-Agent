import { useEffect, useState } from 'react'
import { CheckSquare, Plus, Circle, CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react'
import api from '../lib/api'
import { Task } from '../types'

const statusConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  pending: { label: 'معلقة', icon: <Clock size={14} />, color: 'bg-yellow-100 text-yellow-700' },
  in_progress: { label: 'جارية', icon: <Circle size={14} className="fill-blue-500 text-blue-500" />, color: 'bg-blue-100 text-blue-700' },
  completed: { label: 'مكتملة', icon: <CheckCircle2 size={14} />, color: 'bg-green-100 text-green-700' },
  failed: { label: 'فشلت', icon: <XCircle size={14} />, color: 'bg-red-100 text-red-700' },
  cancelled: { label: 'ملغاة', icon: <AlertCircle size={14} />, color: 'bg-slate-100 text-slate-600' },
}

const priorityColors: Record<string, string> = {
  low: 'text-slate-400', normal: 'text-blue-500', high: 'text-orange-500', urgent: 'text-red-500'
}
const priorityLabels: Record<string, string> = { low: 'منخفضة', normal: 'عادية', high: 'عالية', urgent: 'عاجلة' }

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', priority: 'normal', due_date: '' })

  const load = () => api.get('/tasks/').then(r => { setTasks(r.data); setLoading(false) })
  useEffect(() => { load() }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/tasks/', { ...form, due_date: form.due_date || undefined })
    setShowForm(false)
    setForm({ title: '', description: '', priority: 'normal', due_date: '' })
    load()
  }

  const updateStatus = async (id: number, status: string) => {
    await api.put(`/tasks/${id}`, { status })
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">إدارة المهام</h2>
          <p className="text-sm text-slate-500">تتبع ومتابعة المهام والأعمال</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm">
          <Plus size={16} />مهمة جديدة
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="عنوان المهمة *" className="input-field md:col-span-2" required />
            <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} className="input-field">
              {Object.entries(priorityLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input type="datetime-local" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} className="input-field" />
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="وصف المهمة" rows={2} className="input-field md:col-span-2 resize-none" />
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium">حفظ</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <CheckSquare size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">لا توجد مهام بعد</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map(task => {
            const sc = statusConfig[task.status]
            return (
              <div key={task.id} className="bg-white dark:bg-slate-800 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-slate-700 flex items-start gap-4">
                <div className={`mt-0.5 shrink-0 ${sc?.color} p-1.5 rounded-lg`}>
                  {sc?.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className={`font-medium text-slate-800 dark:text-white text-sm ${task.status === 'completed' ? 'line-through opacity-60' : ''}`}>{task.title}</h3>
                    <span className={`shrink-0 text-xs font-medium ${priorityColors[task.priority]}`}>
                      {priorityLabels[task.priority]}
                    </span>
                  </div>
                  {task.description && <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{task.description}</p>}
                  {task.due_date && (
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                      <Clock size={10} />{new Date(task.due_date).toLocaleDateString('ar-SA')}
                    </p>
                  )}
                </div>
                <div className="flex gap-1.5 shrink-0">
                  {task.status !== 'completed' && (
                    <button onClick={() => updateStatus(task.id, 'completed')} className="p-1.5 rounded-lg bg-green-50 text-green-600 hover:bg-green-100 text-xs">
                      <CheckCircle2 size={14} />
                    </button>
                  )}
                  {task.status === 'pending' && (
                    <button onClick={() => updateStatus(task.id, 'in_progress')} className="p-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 text-xs">
                      <Circle size={14} />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; }`}</style>
    </div>
  )
}
