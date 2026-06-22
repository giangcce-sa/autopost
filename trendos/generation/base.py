"""Interface chung cho mọi generator nội dung.

Thêm một định dạng mới = viết một lớp `BaseGenerator` (prompt + parse), không
đụng tới phần còn lại. Việc gọi Claude tập trung ở `ClaudeClient`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from trendos.generation.claude_client import ClaudeClient
from trendos.models import ContentFormat, ContentPiece, ContentPlanItem, Trend


class BaseGenerator(ABC):
    #: Định dạng nội dung — lớp con phải ghi đè.
    format: ClassVar[ContentFormat]

    def __init__(self, client: ClaudeClient) -> None:
        self.client = client

    @abstractmethod
    async def generate(self, trend: Trend, item: ContentPlanItem | None = None) -> ContentPiece:
        """Sinh một mẩu nội dung cho xu hướng.

        `item` (tuỳ chọn) mang định hướng từ Content Strategist (góc/tone/kênh).
        """
