import { create } from 'zustand'
import { User } from '../types'
import api from '../lib/api'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  fetchMe: () => Promise<void>
  darkMode: boolean
  toggleDarkMode: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isLoading: false,
  darkMode: localStorage.getItem('darkMode') === 'true',

  login: async (username, password) => {
    set({ isLoading: true })
    try {
      const res = await api.post('/auth/login', { username, password })
      const { access_token } = res.data
      localStorage.setItem('access_token', access_token)
      set({ token: access_token })
      await get().fetchMe()
    } finally {
      set({ isLoading: false })
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, token: null })
  },

  fetchMe: async () => {
    try {
      const res = await api.get('/auth/me')
      set({ user: res.data })
    } catch {
      set({ user: null, token: null })
      localStorage.removeItem('access_token')
    }
  },

  toggleDarkMode: () => {
    const next = !get().darkMode
    localStorage.setItem('darkMode', String(next))
    set({ darkMode: next })
    if (next) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
}))
