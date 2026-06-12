import { useEffect, useState } from 'react'
import { UserCog, Plus, Shield, User, CheckCircle, XCircle } from 'lucide-react'
import api from '../lib/api'
import { User as UserType } from '../types'
import { useAuthStore } from '../store/authStore'

export default function Users() {
  const [users, setUsers] = useState<UserType[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', username: '', full_name: '', password: '', department: '', is_superuser: false })
  const { user: me } = useAuthStore()

  const load = () => {
    api.get('/auth/users').then(r => { setUsers(r.data); setLoading(false) }).catch(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/auth/users', form)
    setShowForm(false)
    setForm({ email: '', username: '', full_name: '', password: '', department: '', is_superuser: false })
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">المستخدمون والصلاحيات</h2>
          <p className="text-sm text-slate-500">إدارة فريق العمل وصلاحيات الوصول</p>
        </div>
        {me?.is_superuser && (
          <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm">
            <Plus size={16} />مستخدم جديد
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="البريد الإلكتروني *" type="email" className="input-field" required />
            <input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} placeholder="اسم المستخدم *" className="input-field" required />
            <input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} placeholder="الاسم الكامل" className="input-field" />
            <input value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="كلمة المرور *" type="password" className="input-field" required />
            <input value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} placeholder="القسم" className="input-field" />
            <div className="flex items-center gap-3 px-3 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl">
              <input type="checkbox" id="superuser" checked={form.is_superuser} onChange={e => setForm({ ...form, is_superuser: e.target.checked })} className="w-4 h-4" />
              <label htmlFor="superuser" className="text-sm text-slate-700 dark:text-slate-300">مدير النظام</label>
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium">حفظ</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : !me?.is_superuser ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <Shield size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">هذه الصفحة للمدراء فقط</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                {['المستخدم', 'البريد الإلكتروني', 'القسم', 'الصلاحية', 'الحالة', 'تاريخ الإنشاء'].map(h => (
                  <th key={h} className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-sm font-bold">
                        {(u.full_name || u.username).charAt(0)}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800 dark:text-white text-sm">{u.full_name || u.username}</p>
                        <p className="text-xs text-slate-500">@{u.username}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{u.email}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{u.department || '-'}</td>
                  <td className="px-4 py-3">
                    {u.is_superuser ? (
                      <span className="flex items-center gap-1 text-xs font-medium text-purple-600 bg-purple-100 dark:bg-purple-900/30 px-2.5 py-1 rounded-lg">
                        <Shield size={12} />مدير
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs font-medium text-blue-600 bg-blue-100 dark:bg-blue-900/30 px-2.5 py-1 rounded-lg">
                        <User size={12} />مستخدم
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <div className="flex items-center gap-1 text-green-600 text-xs"><CheckCircle size={14} />نشط</div>
                    ) : (
                      <div className="flex items-center gap-1 text-red-600 text-xs"><XCircle size={14} />غير نشط</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">{new Date(u.created_at).toLocaleDateString('ar-SA')}</td>
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
