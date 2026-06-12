import { Sun, Moon, LogOut, Bell, User } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useNavigate } from 'react-router-dom'

export default function Header({ title }: { title?: string }) {
  const { user, logout, darkMode, toggleDarkMode } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-16 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-6 sticky top-0 z-30 shadow-sm">
      <div className="flex items-center gap-3">
        {title && <h2 className="font-bold text-slate-800 dark:text-white text-lg">{title}</h2>}
      </div>

      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button className="relative p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
          <Bell size={20} className="text-slate-600 dark:text-slate-300" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* Dark mode toggle */}
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        >
          {darkMode ? (
            <Sun size={20} className="text-yellow-500" />
          ) : (
            <Moon size={20} className="text-slate-600" />
          )}
        </button>

        {/* User */}
        <div className="flex items-center gap-2 pr-3 border-r border-slate-200 dark:border-slate-600 mr-1">
          <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
            <User size={18} className="text-white" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-semibold text-slate-800 dark:text-white leading-tight">
              {user?.full_name || user?.username}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {user?.is_superuser ? 'مدير النظام' : 'مستخدم'}
            </p>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors group"
        >
          <LogOut size={20} className="text-slate-500 group-hover:text-red-500 transition-colors" />
        </button>
      </div>
    </header>
  )
}
