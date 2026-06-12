import { useEffect, useState } from 'react'
import { Shield, Search, Filter, CheckCircle, XCircle, Clock } from 'lucide-react'
import api from '../lib/api'
import { AuditLog } from '../types'

const actionLabels: Record<string, string> = {
  create: 'إنشاء', read: 'عرض', update: 'تعديل', delete: 'حذف',
  login: 'تسجيل دخول', logout: 'خروج', export: 'تصدير',
  import: 'استيراد', execute: 'تنفيذ', error: 'خطأ'
}

const actionColors: Record<string, string> = {
  create: 'bg-green-100 text-green-700', read: 'bg-blue-100 text-blue-700',
  update: 'bg-yellow-100 text-yellow-700', delete: 'bg-red-100 text-red-700',
  login: 'bg-purple-100 text-purple-700', logout: 'bg-slate-100 text-slate-600',
  export: 'bg-cyan-100 text-cyan-700', import: 'bg-indigo-100 text-indigo-700',
  execute: 'bg-orange-100 text-orange-700', error: 'bg-red-100 text-red-700'
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState('')
  const [stats, setStats] = useState<{ total: number; by_action: Record<string, number> } | null>(null)

  const load = () => {
    const params: Record<string, string> = {}
    if (actionFilter) params.action = actionFilter
    api.get('/audit/logs', { params }).then(r => { setLogs(r.data); setLoading(false) })
    api.get('/audit/stats').then(r => setStats(r.data))
  }

  useEffect(() => { load() }, [actionFilter])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-white">سجل التدقيق</h2>
        <p className="text-sm text-slate-500">تتبع جميع الأنشطة والأحداث في النظام</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(stats.by_action).filter(([, v]) => v > 0).slice(0, 5).map(([action, count]) => (
            <div key={action} className="bg-white dark:bg-slate-800 rounded-xl p-3 shadow-sm border border-slate-100 dark:border-slate-700 text-center">
              <p className="text-2xl font-bold text-slate-800 dark:text-white">{count}</p>
              <p className="text-xs text-slate-500 mt-0.5">{actionLabels[action] || action}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-3">
        <div className="relative">
          <Filter size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <select value={actionFilter} onChange={e => setActionFilter(e.target.value)} className="pr-9 pl-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl text-sm bg-white dark:bg-slate-800 dark:text-white outline-none">
            <option value="">كل الإجراءات</option>
            {Object.entries(actionLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="text-sm text-slate-500 self-center">
          {stats?.total ?? 0} سجل إجمالاً
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <Shield size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">لا توجد سجلات بعد</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                {['الوقت', 'الإجراء', 'المورد', 'الوصف', 'الحالة'].map(h => (
                  <th key={h} className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {logs.map(log => (
                <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-xs text-slate-500">
                      <Clock size={12} />
                      {new Date(log.created_at).toLocaleString('ar-SA')}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${actionColors[log.action] || 'bg-slate-100 text-slate-600'}`}>
                      {actionLabels[log.action] || log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{log.resource || '-'}</td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 max-w-xs truncate">{log.description || '-'}</td>
                  <td className="px-4 py-3">
                    {log.status === 'success' ? (
                      <div className="flex items-center gap-1 text-green-600 text-xs"><CheckCircle size={14} />نجاح</div>
                    ) : (
                      <div className="flex items-center gap-1 text-red-600 text-xs"><XCircle size={14} />خطأ</div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
