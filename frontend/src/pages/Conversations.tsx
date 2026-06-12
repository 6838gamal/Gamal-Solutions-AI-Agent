import { useEffect, useState } from 'react'
import { MessageSquare, Plus, Send, Circle } from 'lucide-react'
import api from '../lib/api'
import { Conversation, Message } from '../types'

const statusLabels: Record<string, { label: string; color: string }> = {
  open: { label: 'مفتوحة', color: 'bg-green-100 text-green-700' },
  pending: { label: 'معلقة', color: 'bg-yellow-100 text-yellow-700' },
  resolved: { label: 'محلولة', color: 'bg-blue-100 text-blue-700' },
  closed: { label: 'مغلقة', color: 'bg-slate-100 text-slate-600' },
}

const channelLabels: Record<string, string> = {
  web: 'موقع الويب', whatsapp: 'واتساب', telegram: 'تيليجرام',
  email: 'البريد', sms: 'رسالة', phone: 'هاتف', internal: 'داخلي'
}

export default function Conversations() {
  const [convs, setConvs] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [newMsg, setNewMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ channel: 'web', subject: '', priority: 'normal' })

  const load = () => api.get('/conversations/').then(r => { setConvs(r.data); setLoading(false) })
  const loadMsgs = (id: number) => api.get(`/conversations/${id}/messages`).then(r => setMessages(r.data))

  useEffect(() => { load() }, [])

  const select = (c: Conversation) => { setSelected(c); loadMsgs(c.id) }

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/conversations/', form)
    setShowForm(false)
    setForm({ channel: 'web', subject: '', priority: 'normal' })
    load()
  }

  const sendMsg = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected || !newMsg.trim()) return
    await api.post(`/conversations/${selected.id}/messages`, { role: 'agent', content: newMsg })
    setNewMsg('')
    loadMsgs(selected.id)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">المحادثات</h2>
          <p className="text-sm text-slate-500">مركز التواصل متعدد القنوات</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm">
          <Plus size={16} />محادثة جديدة
        </button>
      </div>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <form onSubmit={create} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <select value={form.channel} onChange={e => setForm({ ...form, channel: e.target.value })} className="input-field">
              {Object.entries(channelLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })} placeholder="الموضوع" className="input-field" />
            <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} className="input-field">
              <option value="low">منخفضة</option>
              <option value="normal">عادية</option>
              <option value="high">عالية</option>
              <option value="urgent">عاجلة</option>
            </select>
            <div className="md:col-span-3 flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium">إنشاء</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      <div className="flex gap-4 h-[600px]">
        {/* List */}
        <div className="w-80 shrink-0 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-y-auto">
          {loading ? (
            <div className="text-center py-8 text-slate-500">جارٍ التحميل...</div>
          ) : convs.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare size={36} className="mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500 text-sm">لا توجد محادثات</p>
            </div>
          ) : (
            convs.map(c => (
              <button key={c.id} onClick={() => select(c)} className={`w-full text-right p-4 border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors ${selected?.id === c.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-slate-800 dark:text-white text-sm truncate">{c.subject || `محادثة #${c.id}`}</span>
                  <Circle size={8} className={c.status === 'open' ? 'text-green-500 fill-green-500' : 'text-slate-300 fill-slate-300'} />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{channelLabels[c.channel]}</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${statusLabels[c.status]?.color}`}>{statusLabels[c.status]?.label}</span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Chat */}
        <div className="flex-1 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 flex flex-col">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare size={48} className="mx-auto text-slate-300 mb-3" />
                <p className="text-slate-500">اختر محادثة للعرض</p>
              </div>
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-slate-100 dark:border-slate-700">
                <h3 className="font-semibold text-slate-800 dark:text-white">{selected.subject || `محادثة #${selected.id}`}</h3>
                <p className="text-xs text-slate-500">{channelLabels[selected.channel]}</p>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.map(msg => (
                  <div key={msg.id} className={`flex ${msg.role === 'agent' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm ${msg.role === 'agent' ? 'bg-blue-600 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white'}`}>
                      <p className="text-xs opacity-70 mb-1">{msg.role === 'agent' ? 'وكيل' : 'مستخدم'}</p>
                      {msg.content}
                    </div>
                  </div>
                ))}
                {messages.length === 0 && <p className="text-center text-slate-400 text-sm">لا توجد رسائل بعد</p>}
              </div>
              <form onSubmit={sendMsg} className="p-4 border-t border-slate-100 dark:border-slate-700 flex gap-3">
                <input value={newMsg} onChange={e => setNewMsg(e.target.value)} placeholder="اكتب رسالة..." className="flex-1 px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl text-sm bg-white dark:bg-slate-800 dark:text-white outline-none focus:border-blue-400" />
                <button type="submit" className="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors">
                  <Send size={16} className="rotate-180" />
                </button>
              </form>
            </>
          )}
        </div>
      </div>
      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; }`}</style>
    </div>
  )
}
