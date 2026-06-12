import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

const pageTitles: Record<string, string> = {
  '/dashboard': 'لوحة التحكم',
  '/agents': 'الوكلاء الذكيون',
  '/knowledge': 'قاعدة المعرفة',
  '/customers': 'إدارة العملاء',
  '/conversations': 'المحادثات',
  '/workflows': 'سير العمل',
  '/tasks': 'المهام',
  '/analytics': 'التحليلات',
  '/audit': 'سجل التدقيق',
  '/users': 'المستخدمون والصلاحيات',
  '/settings': 'الإعدادات',
}

export default function MainLayout() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || ''

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900 flex">
      <Sidebar />
      <div className="flex-1 mr-64 flex flex-col min-h-screen">
        <Header title={title} />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
