# app/core/templates.py
from fastapi.templating import Jinja2Templates
from pathlib import Path

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ═══ Globals — متاحة لكل القوالب ═══
_TYPE_BG = {
    'pdf': 'bg-red-100', 'word': 'bg-blue-100', 'excel': 'bg-emerald-100',
    'csv': 'bg-teal-100', 'text': 'bg-slate-100', 'json': 'bg-amber-100',
    'url': 'bg-sky-100', 'manual': 'bg-indigo-100', 'policy': 'bg-purple-100',
    'procedure': 'bg-violet-100', 'contract': 'bg-orange-100',
    'faq': 'bg-pink-100', 'other': 'bg-slate-100',
}
_TYPE_BADGE = {
    'pdf': 'bg-red-50 text-red-700', 'word': 'bg-blue-50 text-blue-700',
    'excel': 'bg-emerald-50 text-emerald-700', 'csv': 'bg-teal-50 text-teal-700',
    'text': 'bg-slate-100 text-slate-600', 'json': 'bg-amber-50 text-amber-700',
    'url': 'bg-sky-50 text-sky-700', 'manual': 'bg-indigo-50 text-indigo-700',
    'policy': 'bg-purple-50 text-purple-700', 'procedure': 'bg-violet-50 text-violet-700',
    'contract': 'bg-orange-50 text-orange-700', 'faq': 'bg-pink-50 text-pink-700',
    'other': 'bg-slate-100 text-slate-500',
}
_TYPE_LABEL = {
    'pdf': 'PDF', 'word': 'Word', 'excel': 'Excel', 'csv': 'CSV',
    'text': 'نص', 'json': 'JSON', 'url': 'رابط', 'manual': 'دليل',
    'policy': 'سياسة', 'procedure': 'إجراء', 'contract': 'عقد',
    'faq': 'أسئلة شائعة', 'other': 'أخرى',
}

templates.env.globals['doc_type_bg']     = lambda dt: _TYPE_BG.get(str(dt), 'bg-slate-100')
templates.env.globals['type_badge_class'] = lambda dt: _TYPE_BADGE.get(str(dt), 'bg-slate-100 text-slate-500')
templates.env.globals['doc_type_label']  = lambda dt: _TYPE_LABEL.get(str(dt), str(dt))
