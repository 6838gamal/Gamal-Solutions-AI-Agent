import { useState } from 'react'
import { Settings as SettingsIcon, Key, Globe, Bell, Shield, Save } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import api from '../lib/api'

export default function Settings() {
  const { user } = useAuthStore()
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState('')
  const [pwError, setPwError] = useState('')

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwMsg(''); setPwError('')
    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('كلمتا المرور غير متطابقتين'); return
    }
    try {
      await api.put('/auth/me/password', { current_password: pwForm.current_password, new_password: pwForm.new_password })
      setPwMsg('تم تغيير كلمة المرور بنجاح')
      setPwForm({ current_password: '', new_password: '', confirm: '' })
    } catch {
      setPwError('كلمة المرور الحالية غير صحيحة')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-white">الإعدادات</h2>
        <p className="text-sm text-slate-500">إعدادات الحساب والنظام</p>
      </div>

      {/* Profile */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
        <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
          <Globe size={18} className="text-blue-500" />معلومات الحساب
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">اسم المستخدم</label>
            <p className="px-4 py-2.5 bg-slate-50 dark:bg-slate-700 rounded-xl text-sm text-slate-800 dark:text-white">{user?.username}</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">البريد الإلكتروني</label>
            <p className="px-4 py-2.5 bg-slate-50 dark:bg-slate-700 rounded-xl text-sm text-slate-800 dark:text-white">{user?.email}</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">الاسم الكامل</label>
            <p className="px-4 py-2.5 bg-slate-50 dark:bg-slate-700 rounded-xl text-sm text-slate-800 dark:text-white">{user?.full_name || '-'}</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">القسم</label>
            <p className="px-4 py-2.5 bg-slate-50 dark:bg-slate-700 rounded-xl text-sm text-slate-800 dark:text-white">{user?.department || '-'}</p>
          </div>
        </div>
      </div>

      {/* Password change */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
        <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
          <Key size={18} className="text-orange-500" />تغيير كلمة المرور
        </h3>
        <form onSubmit={changePassword} className="space-y-4">
          <input type="password" value={pwForm.current_password} onChange={e => setPwForm({ ...pwForm, current_password: e.target.value })} placeholder="كلمة المرور الحالية" className="input-field" required />
          <input type="password" value={pwForm.new_password} onChange={e => setPwForm({ ...pwForm, new_password: e.target.value })} placeholder="كلمة المرور الجديدة" className="input-field" required />
          <input type="password" value={pwForm.confirm} onChange={e => setPwForm({ ...pwForm, confirm: e.target.value })} placeholder="تأكيد كلمة المرور الجديدة" className="input-field" required />
          {pwMsg && <p className="text-green-600 text-sm">{pwMsg}</p>}
          {pwError && <p className="text-red-600 text-sm">{pwError}</p>}
          <button type="submit" className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">
            <Save size={16} />حفظ التغييرات
          </button>
        </form>
      </div>

      {/* System info */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
        <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
          <SettingsIcon size={18} className="text-slate-500" />معلومات النظام
        </h3>
        <div className="space-y-3">
          {[
            { label: 'الإصدار', value: '1.0.0' },
            { label: 'المنصة', value: 'Gamal Solutions AI Platform' },
            { label: 'البيئة', value: 'Development' },
            { label: 'قاعدة البيانات', value: 'PostgreSQL (Render)' },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-700 last:border-0">
              <span className="text-sm text-slate-500">{label}</span>
              <span className="text-sm font-medium text-slate-800 dark:text-white">{value}</span>
            </div>
          ))}
        </div>
      </div>

      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; }`}</style>
    </div>
  )
}
