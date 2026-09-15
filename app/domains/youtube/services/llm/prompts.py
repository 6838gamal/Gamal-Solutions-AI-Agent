"""
قوالب البرومبت — مخصصة لنيتش AI automation / AI Agents / AI workflow / Productivity.
"""
from typing import Optional


SYSTEM_TITLES = """أنت خبير في كتابة عناوين فيديوهات YouTube عالية الأداء.
تتخصص في نيتش: AI automation, AI Agents, AI workflow, productivity.

قواعدك:
1. اكتب عناوين محددة، واضحة، وتُثير الفضول
2. استخدم أرقامًا عند الإمكان (5 طرق، 10 دقائق، ...)
3. تجنب التكرار — كل عنوان يجب أن يقدّم زاوية مختلفة
4. الأطوال: 40-70 حرفًا للعربية، 50-90 حرفًا للإنجليزية
5. لا تستخدم مقدمات مثل "هل تريد أن..." — كن مباشرًا
6. اهتم بمصلحة المشاهد (توفير وقت، زيادة إنتاجية، أتمتة، ...)
7. أعطِ عناوين قابلة للنقر لكن غير مضللة"""


def build_titles_prompt(
    topic: str,
    language: str,
    count: int,
    top_titles: list[str] = None,
    co_keywords: list[str] = None,
    videos_count: int = 0,
    avg_views: int = 0,
    days_since_latest: int = None,
) -> str:
    """يبني برومبت توليد العناوين."""

    lang_instruction = {
        "ar": f"اكتب {count} عنوانًا بالعربية الفصحى المبسطة.",
        "en": f"Write {count} video titles in English.",
        "both": (
            f"Write {count} titles total: "
            f"half in Arabic (العربية الفصحى المبسطة) and half in English."
        ),
    }.get(language, f"Write {count} titles in English.")

    context_lines = [f"الموضوع (topic): {topic}"]

    if videos_count > 0:
        context_lines.append(f"عدد الفيديوهات الناجحة حول هذا الموضوع: {videos_count}")
    if avg_views > 0:
        context_lines.append(f"متوسط المشاهدات لهذه الفيديوهات: {avg_views:,}")
    if days_since_latest is not None:
        context_lines.append(f"آخر فيديو ناجح نُشر قبل: {days_since_latest} يوم")

    if co_keywords:
        context_lines.append(
            f"كلمات مرتبطة بالموضوع: {', '.join(co_keywords[:8])}"
        )

    if top_titles:
        context_lines.append("\nأمثلة على عناوين ناجحة سابقة:")
        for t in top_titles[:5]:
            context_lines.append(f"  • {t}")

    context = "\n".join(context_lines)

    return f"""{context}

المطلوب: {lang_instruction}

قواعد إضافية:
- كل عنوان يجب أن يقدّم زاوية مختلفة (تعليمي، قائمة، مقارنة، قصة، تحذير، ...)
- لا تكرر نفس الكلمات في كل عنوان
- ركز على AI automation / agents / workflow / productivity

أخرج النتيجة كـ JSON فقط بهذا الشكل:
{{
  "titles": [
    "العنوان 1",
    "العنوان 2",
    ...
  ]
}}

لا تضف أي نص آخر قبل أو بعد JSON."""
