import { useEffect, useState } from 'react'
import { Users, Plus, Search, Trash2, Star, Phone, Mail, Building2 } from 'lucide-react'
import api from '../lib/api'
import { Customer } from '../types'

const statusLabels: Record<string, { label: string; color: string }> = {
  lead: { label: 'عميل محتمل', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  prospect: { label: 'مرشح', color: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' },
  active: { label: 'نشط', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  inactive: { label: 'غير نشط', color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300' },
  churned: { label: 'مفقود', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
}

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', phone: '', company: '', status: 'lead', country: '', notes: '' })

  const load = () => {
    api.get('/customers/', { params: { search: search || undefined, status: statusFilter || undefined, limit: 100 } })
      .then(r => { setCustomers(r.data); setLoading(false) })
  }

  useEffect(() => { load() }, [statusFilter])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/customers/', form)
    setShowForm(false)
    setForm({ name: '', email: '', phone: '', company: '', status: 'lead', country: '', notes: '' })
    load()
  }

  const remove = async (id: number) => {
    if (!confirm('حذف هذا العميل؟')) return
    await api.delete(`/customers/${id}`)
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">إدارة العملاء</h2>
          <p className="text-sm text-slate-500 mt-1">قاعدة بيانات العملاء والملفات الذكية</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm">
          <Plus size={16} />عميل جديد
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} placeholder="بحث..." className="w-full pr-9 pl-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl text-sm bg-white dark:bg-slate-800 dark:text-white outline-none focus:border-blue-400" />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl text-sm bg-white dark:bg-slate-800 dark:text-white outline-none">
          <option value="">جميع الحالات</option>
          {Object.entries(statusLabels).map(([v, { label }]) => <option key={v} value={v}>{label}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4">إضافة عميل جديد</h3>
          <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="الاسم *" className="input-field" required />
            <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="البريد الإلكتروني" type="email" className="input-field" />
            <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="رقم الهاتف" className="input-field" />
            <input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="الشركة" className="input-field" />
            <input value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} placeholder="الدولة" className="input-field" />
            <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })} className="input-field">
              {Object.entries(statusLabels).map(([v, { label }]) => <option key={v} value={v}>{label}</option>)}
            </select>
            <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="ملاحظات" rows={2} className="input-field md:col-span-2 resize-none" />
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">حفظ</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : customers.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <Users size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">لا يوجد عملاء بعد</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                {['العميل', 'التواصل', 'الشركة', 'الحالة', 'النقاط', 'الإجراءات'].map(h => (
                  <th key={h} className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {customers.map(c => (
                <tr key={c.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-sm shrink-0">
                        {c.name.charAt(0)}
                      </div>
                      <span className="font-medium text-slate-800 dark:text-white text-sm">{c.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-0.5">
                      {c.email && <div className="flex items-center gap-1 text-xs text-slate-500"><Mail size={12} />{c.email}</div>}
                      {c.phone && <div className="flex items-center gap-1 text-xs text-slate-500"><Phone size={12} />{c.phone}</div>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {c.company && <div className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300"><Building2 size={14} />{c.company}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${statusLabels[c.status]?.color}`}>
                      {statusLabels[c.status]?.label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Star size={14} className="text-yellow-500" />
                      <span className="text-sm font-medium text-slate-800 dark:text-white">{c.score.toFixed(1)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => remove(c.id)} className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; }`}</style>
    </div>
  )
}
