import { useEffect, useState } from 'react'
import { Bot, Users, MessageSquare, BookOpen, GitBranch, CheckSquare, TrendingUp, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import api from '../lib/api'
import { DashboardStats } from '../types'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/analytics/dashboard').then(r => {
      setStats(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const customerChartData = stats ? Object.entries(stats.customers.by_status).map(([name, value]) => ({
    name: { lead: 'عميل محتمل', prospect: 'مرشح', active: 'نشط', inactive: 'غير نشط', churned: 'مفقود' }[name] || name,
    value
  })) : []

  const overviewData = stats ? [
    { name: 'الوكلاء', value: stats.agents.total },
    { name: 'العملاء', value: stats.customers.total },
    { name: 'المحادثات', value: stats.conversations.total },
    { name: 'المستندات', value: stats.knowledge.total_documents },
    { name: 'المهام', value: stats.tasks.total },
  ] : []

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="الوكلاء النشطون"
          value={loading ? '...' : `${stats?.agents.active ?? 0} / ${stats?.agents.total ?? 0}`}
          icon={<Bot size={22} />}
          gradient="stat-gradient-blue"
          sub="وكلاء يعملون الآن"
        />
        <StatCard
          label="إجمالي العملاء"
          value={loading ? '...' : String(stats?.customers.total ?? 0)}
          icon={<Users size={22} />}
          gradient="stat-gradient-green"
          sub={`${stats?.customers.by_status?.active ?? 0} نشط`}
        />
        <StatCard
          label="المحادثات المفتوحة"
          value={loading ? '...' : String(stats?.conversations.open ?? 0)}
          icon={<MessageSquare size={22} />}
          gradient="stat-gradient-purple"
          sub={`من أصل ${stats?.conversations.total ?? 0}`}
        />
        <StatCard
          label="مستندات المعرفة"
          value={loading ? '...' : String(stats?.knowledge.total_documents ?? 0)}
          icon={<BookOpen size={22} />}
          gradient="stat-gradient-orange"
          sub="في قاعدة المعرفة"
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3 mb-2">
            <GitBranch size={18} className="text-blue-500" />
            <span className="font-semibold text-slate-700 dark:text-slate-200">سير العمل</span>
          </div>
          <p className="text-3xl font-bold text-slate-800 dark:text-white">{loading ? '...' : stats?.workflows.total ?? 0}</p>
          <p className="text-xs text-slate-500 mt-1">إجمالي الأتمتة</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3 mb-2">
            <CheckSquare size={18} className="text-green-500" />
            <span className="font-semibold text-slate-700 dark:text-slate-200">المهام المعلقة</span>
          </div>
          <p className="text-3xl font-bold text-slate-800 dark:text-white">{loading ? '...' : stats?.tasks.pending ?? 0}</p>
          <p className="text-xs text-slate-500 mt-1">من {stats?.tasks.total ?? 0} مهمة</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3 mb-2">
            <Activity size={18} className="text-purple-500" />
            <span className="font-semibold text-slate-700 dark:text-slate-200">المستخدمون</span>
          </div>
          <p className="text-3xl font-bold text-slate-800 dark:text-white">{loading ? '...' : stats?.users.total ?? 0}</p>
          <p className="text-xs text-slate-500 mt-1">في النظام</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-500" />
            نظرة عامة على البيانات
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={overviewData}>
              <XAxis dataKey="name" tick={{ fontSize: 12, fontFamily: 'Cairo' }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <Users size={18} className="text-green-500" />
            حالة العملاء
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={customerChartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {customerChartData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, icon, gradient, sub }: {
  label: string; value: string; icon: React.ReactNode; gradient: string; sub: string
}) {
  return (
    <div className={`${gradient} rounded-2xl p-5 text-white shadow-lg`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium opacity-90">{label}</span>
        <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold mb-1">{value}</p>
      <p className="text-xs opacity-75">{sub}</p>
    </div>
  )
}
