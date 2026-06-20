"""Wrapper mỏng quanh Anthropic SDK — một nơi duy nhất quản model/thinking/streaming.

Mặc định theo khuyến nghị của Anthropic:
  - model `claude-opus-4-8`
  - adaptive thinking cho tác vụ sáng tạo/suy luận
  - streaming cho đầu ra dài (bài blog) để tránh timeout HTTP
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic

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
        msg = await self._client.messages.create(**kwargs)
        return json.loads(self._text(msg))

    @staticmethod
    def _text(msg: Any) -> str:
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
