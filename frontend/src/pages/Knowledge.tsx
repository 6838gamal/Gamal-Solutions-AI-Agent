import { useEffect, useState } from 'react'
import { BookOpen, Plus, Search, Trash2, FileText, Tag } from 'lucide-react'
import api from '../lib/api'
import { KnowledgeDocument } from '../types'

const typeLabels: Record<string, string> = {
  pdf: 'PDF', word: 'Word', excel: 'Excel', csv: 'CSV',
  text: 'نص', url: 'رابط', manual: 'يدوي', policy: 'سياسة',
  procedure: 'إجراء', contract: 'عقد', faq: 'أسئلة شائعة', other: 'أخرى'
}

export default function Knowledge() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', content: '', summary: '', doc_type: 'manual', source: '', tags: '' })

  const load = (q = '') => {
    api.get('/knowledge/documents', { params: { search: q || undefined, limit: 100 } }).then(r => {
      setDocs(r.data)
      setLoading(false)
    })
  }

  useEffect(() => { load() }, [])

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); load(search) }

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/knowledge/documents', {
      ...form,
      tags: form.tags.split(',').map(t => t.trim()).filter(Boolean)
    })
    setShowForm(false)
    setForm({ title: '', content: '', summary: '', doc_type: 'manual', source: '', tags: '' })
    load()
  }

  const remove = async (id: number) => {
    if (!confirm('حذف هذا المستند؟')) return
    await api.delete(`/knowledge/documents/${id}`)
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white">قاعدة المعرفة</h2>
          <p className="text-sm text-slate-500 mt-1">إدارة المستندات والمعرفة المؤسسية</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm">
          <Plus size={16} />مستند جديد
        </button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="البحث في قاعدة المعرفة..."
            className="w-full pr-10 pl-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl text-sm bg-white dark:bg-slate-800 dark:text-white outline-none focus:border-blue-400" />
        </div>
        <button type="submit" className="px-5 py-2.5 bg-slate-800 dark:bg-slate-600 text-white rounded-xl text-sm font-medium">بحث</button>
      </form>

      {showForm && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700">
          <h3 className="font-bold text-slate-800 dark:text-white mb-4">إضافة مستند جديد</h3>
          <form onSubmit={create} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="عنوان المستند *" className="input-field" required />
              <select value={form.doc_type} onChange={e => setForm({ ...form, doc_type: e.target.value })} className="input-field">
                {Object.entries(typeLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <input value={form.source} onChange={e => setForm({ ...form, source: e.target.value })} placeholder="المصدر (رابط أو اسم الملف)" className="input-field" />
            <input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="الوسوم (مفصولة بفاصلة)" className="input-field" />
            <textarea value={form.summary} onChange={e => setForm({ ...form, summary: e.target.value })} placeholder="ملخص المستند" rows={2} className="input-field resize-none" />
            <textarea value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} placeholder="محتوى المستند" rows={4} className="input-field resize-none" />
            <div className="flex gap-3">
              <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">حفظ</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-6 py-2.5 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700">إلغاء</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">جارٍ التحميل...</div>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
          <BookOpen size={48} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500">لا توجد مستندات بعد</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {docs.map(doc => (
            <div key={doc.id} className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileText size={18} className="text-blue-500 shrink-0" />
                  <h3 className="font-semibold text-slate-800 dark:text-white text-sm line-clamp-2">{doc.title}</h3>
                </div>
                <button onClick={() => remove(doc.id)} className="p-1.5 rounded-lg text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 shrink-0">
                  <Trash2 size={14} />
                </button>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-medium">
                  {typeLabels[doc.doc_type] || doc.doc_type}
                </span>
                <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg text-xs font-medium">
                  {doc.status === 'active' ? 'نشط' : doc.status}
                </span>
              </div>
              {doc.summary && <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-3">{doc.summary}</p>}
              {doc.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {doc.tags.slice(0, 3).map((t, i) => (
                    <span key={i} className="flex items-center gap-1 px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg text-xs">
                      <Tag size={10} />{t}
                    </span>
                  ))}
                </div>
              )}
              <p className="text-xs text-slate-400 mt-3">{new Date(doc.created_at).toLocaleDateString('ar-SA')}</p>
            </div>
          ))}
        </div>
      )}
      <style>{`.input-field { width: 100%; padding: 0.625rem 1rem; border: 1px solid #e2e8f0; border-radius: 0.75rem; font-family: Cairo, sans-serif; font-size: 0.875rem; outline: none; background: white; } .dark .input-field { background: #1e293b; border-color: #475569; color: white; } .input-field:focus { border-color: #3b82f6; }`}</style>
    </div>
  )
}
