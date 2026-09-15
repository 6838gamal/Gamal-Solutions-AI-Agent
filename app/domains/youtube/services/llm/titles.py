"""
generate_titles — يحوّل Opportunity إلى عناوين مقترحة.
"""
import json
import logging
from typing import Optional

from app.domains.youtube.services.llm.base import LLMResponse
from app.domains.youtube.services.llm.gemini import GeminiProvider
from app.domains.youtube.services.llm.prompts import (
    SYSTEM_TITLES,
    build_titles_prompt,
)

logger = logging.getLogger(__name__)


async def generate_titles(
    opportunity: dict,
    language: str = "both",
    count: int = 10,
) -> dict:
    """
    Args:
        opportunity: dict من get_opportunities()
        language: "ar" | "en" | "both"
        count: عدد العناوين

    Returns:
        {
            "topic": str,
            "language": str,
            "titles": [...],
            "model": str,
            "tokens": {"in": int, "out": int},
            "error": str | None,
        }
    """
    topic = opportunity.get("topic", "")
    if not topic:
        return {
            "topic": "",
            "language": language,
            "titles": [],
            "error": "topic مفقود",
        }

    # ── اجمع السياق من opportunity ────────────────────────
    sample_titles = opportunity.get("sample_titles", [])
    co_keywords = opportunity.get("co_keywords", [])
    videos_count = opportunity.get("videos_count", 0)
    avg_views = int(opportunity.get("avg_views", 0) or 0)
    days_since_latest = opportunity.get("days_since_latest")

    # ── ابنِ البرومبت ─────────────────────────────────────
    prompt = build_titles_prompt(
        topic=topic,
        language=language,
        count=count,
        top_titles=sample_titles,
        co_keywords=co_keywords,
        videos_count=videos_count,
        avg_views=avg_views,
        days_since_latest=days_since_latest,
    )

    # ── استدعِ LLM ────────────────────────────────────────
    provider = GeminiProvider()
    response: LLMResponse = await provider.generate(
        prompt=prompt,
        system=SYSTEM_TITLES,
        temperature=0.85,       # أعلى قليلًا للإبداع
        max_tokens=2048,
        json_mode=True,
    )

    if not response.ok:
        logger.error(f"[generate_titles] LLM error: {response.error}")
        return {
            "topic": topic,
            "language": language,
            "titles": [],
            "model": response.model,
            "error": response.error,
        }

    # ── حلّل JSON ─────────────────────────────────────────
    titles = []
    try:
        data = json.loads(response.text)
        titles = data.get("titles", [])
        if not isinstance(titles, list):
            titles = []
        titles = [str(t).strip() for t in titles if str(t).strip()]
    except json.JSONDecodeError:
        # محاولة استخراج array من نص
        import re
        match = re.search(r"\[(.*?)\]", response.text, re.DOTALL)
        if match:
            try:
                titles = json.loads(f"[{match.group(1)}]")
            except Exception:
                pass
        if not titles:
            logger.warning(f"[generate_titles] فشل تحليل JSON: {response.text[:200]}")

    return {
        "topic": topic,
        "language": language,
        "titles": titles,
        "model": response.model,
        "tokens": {
            "in": response.tokens_in,
            "out": response.tokens_out,
        },
        "error": None,
    }
