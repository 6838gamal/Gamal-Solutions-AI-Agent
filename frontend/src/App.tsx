import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import MainLayout from './components/layout/MainLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Knowledge from './pages/Knowledge'
import Customers from './pages/Customers'
import Conversations from './pages/Conversations'
import WorkflowsPage from './pages/Workflows'
import Analytics from './pages/Analytics'
import AuditLogs from './pages/AuditLogs'
import Users from './pages/Users'
import Settings from './pages/Settings'
import Tasks from './pages/Tasks'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const { fetchMe, token, darkMode } = useAuthStore()

  useEffect(() => {
    if (darkMode) document.documentElement.classList.add('dark')
    if (token) fetchMe()
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="agents" element={<Agents />} />
          <Route path="knowledge" element={<Knowledge />} />
          <Route path="customers" element={<Customers />} />
          <Route path="conversations" element={<Conversations />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="audit" element={<AuditLogs />} />
          <Route path="users" element={<Users />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
