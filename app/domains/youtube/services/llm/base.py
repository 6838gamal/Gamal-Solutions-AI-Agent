"""
LLM Provider interface — abstract base.

الهدف: لو غيّرت المزود (Gemini → HuggingFace → Ollama)، لا يتغير
أي كود آخر في النظام. فقط أنشئ Provider جديد.

لا يستورد أي شيء من youtube. مستقل تمامًا.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """استجابة موحّدة من أي LLM."""
    text: str
    raw: dict = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.text)


class LLMProvider(ABC):
    """واجهة موحّدة لأي مزود LLM."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Args:
            prompt: نص الطلب
            system: تعليمات النظام (system prompt)
            temperature: 0..1 (منخفض = دقيق، مرتفع = إبداعي)
            max_tokens: أقصى عدد tokens في الاستجابة
            json_mode: هل نريد استجابة JSON صارمة؟

        Returns:
            LLMResponse
        """
        ...
