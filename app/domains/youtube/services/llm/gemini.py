"""
Gemini Provider — عبر HTTP request مباشر (بدون SDK).

يستخدم GEMINI_API_KEY من config.
Endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
"""
import json
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.domains.youtube.services.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        self.timeout = timeout or getattr(settings, "LLM_TIMEOUT_SECONDS", 45)
        self.base_url = getattr(
            settings, "GEMINI_API_URL",
            "https://generativelanguage.googleapis.com/v1beta/models"
        )

        if not self.api_key:
            logger.warning("[GeminiProvider] GEMINI_API_KEY غير مُعرَّف")

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:

        if not self.api_key:
            return LLMResponse(
                text="", provider="gemini", model=self.model,
                error="GEMINI_API_KEY غير مُعرَّف في الإعدادات",
            )

        url = f"{self.base_url}/{self.model}:generateContent"
        params = {"key": self.api_key}

        # ── بناء الـcontents ───────────────────────────────
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "فهمت."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        # ── إعدادات التوليد ────────────────────────────────
        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.95,
            "topK": 40,
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        body = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        # ── الطلب ─────────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(url, params=params, json=body)
        except httpx.TimeoutException:
            return LLMResponse(
                text="", provider="gemini", model=self.model,
                error=f"timeout بعد {self.timeout}s",
            )
        except Exception as e:
            return LLMResponse(
                text="", provider="gemini", model=self.model,
                error=f"خطأ في الاتصال: {e}",
            )

        # ── معالجة الاستجابة ──────────────────────────────
        if r.status_code != 200:
            error_text = r.text[:400]
            logger.error(f"[Gemini] {r.status_code}: {error_text}")
            return LLMResponse(
                text="", provider="gemini", model=self.model,
                error=f"HTTP {r.status_code}: {error_text}",
            )

        try:
            data = r.json()
        except Exception as e:
            return LLMResponse(
                text="", provider="gemini", model=self.model,
                error=f"فشل تحليل JSON: {e}",
            )

        # ── استخراج النص ──────────────────────────────────
        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        # ── استخراج tokens ────────────────────────────────
        usage = data.get("usageMetadata", {})
        tokens_in = usage.get("promptTokenCount")
        tokens_out = usage.get("candidatesTokenCount")

        if not text:
            return LLMResponse(
                text="", provider="gemini", model=self.model,
                raw=data,
                error="استجابة فارغة من Gemini",
            )

        return LLMResponse(
            text=text,
            raw=data,
            provider="gemini",
            model=self.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
