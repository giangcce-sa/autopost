"""Wrapper mỏng quanh Anthropic SDK — một nơi duy nhất quản model/thinking/streaming.

Mặc định theo khuyến nghị của Anthropic:
  - model `claude-opus-4-8`
  - adaptive thinking cho tác vụ sáng tạo/suy luận
  - streaming cho đầu ra dài (bài blog) để tránh timeout HTTP
"""

from __future__ import annotations

import json
import re
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic

from trendos.config import Settings


class ClaudeClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # SDK tự đọc ANTHROPIC_API_KEY; truyền tường minh để rõ ràng.
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key or None)

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> str:
        """Gọi Claude và trả về văn bản kết quả.

        Dùng `stream=True` cho đầu ra dài (bài blog) — gom lại bằng
        `get_final_message()` để vừa an toàn timeout vừa lấy trọn nội dung.
        """
        kwargs: dict = {
            "model": self._settings.claude_model,
            "max_tokens": max_tokens or self._settings.claude_max_tokens,
            "thinking": {"type": "adaptive"},
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        if stream:
            async with self._client.messages.stream(**kwargs) as s:
                msg = await s.get_final_message()
        else:
            msg = await self._client.messages.create(**kwargs)

        # Lấy các block văn bản (bỏ qua block thinking).
        return self._text(msg)

    async def complete_json(
        self,
        prompt: str,
        *,
        schema: dict,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """Gọi Claude với structured output (JSON Schema), trả về object đã parse.

        Dùng cho các agent cần dữ liệu có cấu trúc (Research → brief,
        Strategist → kế hoạch). `schema` là JSON Schema mô tả đầu ra mong muốn.
        """
        kwargs: dict = {
            "model": self._settings.claude_model,
            "max_tokens": max_tokens or self._settings.claude_max_tokens,
            "thinking": {"type": "adaptive"},
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        try:
            msg = await self._client.messages.create(**kwargs)
            return self._json_from_text(self._text(msg))
        except (TypeError, APIStatusError) as exc:
            if not self._should_fallback_structured_output(exc):
                raise

        fallback_prompt = (
            f"{prompt}\n\n"
            "Trả về DUY NHẤT một JSON object hợp lệ theo schema sau, không markdown, "
            f"không giải thích:\n{json.dumps(schema, ensure_ascii=False)}"
        )
        fallback_text = await self.complete(
            fallback_prompt,
            system=system,
            max_tokens=max_tokens,
            stream=False,
        )
        return self._json_from_text(fallback_text)

    @staticmethod
    def _text(msg: Any) -> str:
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

    @staticmethod
    def _json_from_text(text: str) -> Any:
        text = text.strip()
        if not text:
            raise ValueError("Claude returned empty JSON response")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match is None:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _should_fallback_structured_output(exc: Exception) -> bool:
        if isinstance(exc, TypeError):
            return "output_config" in str(exc)
        if isinstance(exc, APIStatusError):
            return exc.status_code == 400 and "output_config" in str(exc).lower()
        return False
