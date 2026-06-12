import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Bot, BookOpen, Users, MessageSquare,
  GitBranch, CheckSquare, BarChart3, Shield, Settings,
  UserCog, ChevronRight, Zap
} from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'لوحة التحكم', label_en: 'Dashboard' },
  { to: '/agents', icon: Bot, label: 'الوكلاء الذكيون', label_en: 'AI Agents' },
  { to: '/knowledge', icon: BookOpen, label: 'قاعدة المعرفة', label_en: 'Knowledge Base' },
  { to: '/customers', icon: Users, label: 'إدارة العملاء', label_en: 'Customers' },
  { to: '/conversations', icon: MessageSquare, label: 'المحادثات', label_en: 'Conversations' },
  { to: '/workflows', icon: GitBranch, label: 'سير العمل', label_en: 'Workflows' },
  { to: '/tasks', icon: CheckSquare, label: 'المهام', label_en: 'Tasks' },
  { to: '/analytics', icon: BarChart3, label: 'التحليلات', label_en: 'Analytics' },
  { to: '/audit', icon: Shield, label: 'سجل التدقيق', label_en: 'Audit Logs' },
  { to: '/users', icon: UserCog, label: 'المستخدمون', label_en: 'Users & Roles' },
  { to: '/settings', icon: Settings, label: 'الإعدادات', label_en: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 h-screen bg-gradient-to-b from-blue-950 to-blue-900 text-white flex flex-col shadow-2xl fixed right-0 top-0 z-40">
      {/* Logo */}
      <div className="p-6 border-b border-blue-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center">
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight">Gamal Solutions</h1>
            <p className="text-blue-300 text-xs">منصة الذكاء الاصطناعي</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <div className="space-y-1">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group',
                  isActive
                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                    : 'text-blue-200 hover:bg-blue-800/50 hover:text-white'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} className={isActive ? 'text-white' : 'text-blue-300 group-hover:text-white'} />
                  <span className="flex-1">{label}</span>
                  {isActive && <ChevronRight size={14} className="opacity-70 rotate-180" />}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-blue-800/50">
        <p className="text-xs text-blue-400 text-center">v1.0.0 — Enterprise AI Platform</p>
      </div>
    </aside>
  )
}
