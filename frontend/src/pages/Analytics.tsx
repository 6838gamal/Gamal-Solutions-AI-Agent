import { useEffect, useState } from 'react'
import { BarChart3, TrendingUp, Users, Bot, MessageSquare } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, AreaChart, Area } from 'recharts'
import api from '../lib/api'
import { DashboardStats } from '../types'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

const mockTrend = [
  { month: 'يناير', conversations: 12, customers: 5 },
  { month: 'فبراير', conversations: 19, customers: 8 },
  { month: 'مارس', conversations: 15, customers: 12 },
  { month: 'أبريل', conversations: 28, customers: 18 },
  { month: 'مايو', conversations: 35, customers: 22 },
  { month: 'يونيو', conversations: 42, customers: 30 },
]

export default function Analytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    api.get('/analytics/dashboard').then(r => setStats(r.data))
  }, [])

  const customerData = stats ? Object.entries(stats.customers.by_status).map(([k, v]) => ({
    name: { lead: 'محتمل', prospect: 'مرشح', active: 'نشط', inactive: 'غير نشط', churned: 'مفقود' }[k] || k,
    value: v
  })) : []

  const agentData = stats ? [
    { name: 'نشط', value: stats.agents.active },
    { name: 'غير نشط', value: stats.agents.total - stats.agents.active },
  ] : []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-white">التحليلات والتقارير</h2>
        <p className="text-sm text-slate-500">نظرة شاملة على أداء المنصة</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'إجمالي العملاء', value: stats?.customers.total ?? 0, icon: <Users size={20} />, color: 'text-blue-600 bg-blue-100' },
          { label: 'الوكلاء النشطون', value: stats?.agents.active ?? 0, icon: <Bot size={20} />, color: 'text-green-600 bg-green-100' },
          { label: 'المحادثات المفتوحة', value: stats?.conversations.open ?? 0, icon: <MessageSquare size={20} />, color: 'text-purple-600 bg-purple-100' },
          { label: 'المهام المعلقة', value: stats?.tasks.pending ?? 0, icon: <TrendingUp size={20} />, color: 'text-orange-600 bg-orange-100' },
        ].map(({ label, value, icon, color }) => (
          <div key={label} className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700">
            <div className={`inline-flex p-2.5 rounded-xl mb-3 ${color} dark:opacity-80`}>{icon}</div>
            <p className="text-2xl font-bold text-slate-800 dark:text-white">{value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-500" />النمو الشهري
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={mockTrend}>
              <defs>
                <linearGradient id="conv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="cust" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fontSize: 11, fontFamily: 'Cairo' }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="conversations" name="محادثات" stroke="#3b82f6" fill="url(#conv)" strokeWidth={2} />
              <Area type="monotone" dataKey="customers" name="عملاء" stroke="#10b981" fill="url(#cust)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <Users size={18} className="text-green-500" />حالة العملاء
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={customerData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                {customerData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <Bot size={18} className="text-purple-500" />حالة الوكلاء
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={agentData}>
              <XAxis dataKey="name" tick={{ fontSize: 12, fontFamily: 'Cairo' }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-orange-500" />ملخص الأداء
          </h3>
          <div className="space-y-4 mt-2">
            {[
              { label: 'وكلاء نشطون', value: stats?.agents.active ?? 0, total: stats?.agents.total || 1, color: 'bg-blue-500' },
              { label: 'محادثات مفتوحة', value: stats?.conversations.open ?? 0, total: stats?.conversations.total || 1, color: 'bg-green-500' },
              { label: 'مهام معلقة', value: stats?.tasks.pending ?? 0, total: stats?.tasks.total || 1, color: 'bg-orange-500' },
            ].map(({ label, value, total, color }) => (
              <div key={label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600 dark:text-slate-300">{label}</span>
                  <span className="font-medium text-slate-800 dark:text-white">{value}/{total}</span>
                </div>
                <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min((value / total) * 100, 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
