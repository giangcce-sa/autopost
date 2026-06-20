"""Interface chung cho mọi nguồn dữ liệu.

Mỗi nền tảng (Hacker News, Reddit, YouTube...) cài đặt một `BaseCollector`.
Orchestrator chạy nhiều collector song song và cô lập lỗi của từng nguồn —
một nguồn hỏng không làm sập pipeline (xem ARCHITECTURE.md §3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from trendos.config import Settings
from trendos.models import Signal, SourceName


class BaseCollector(ABC):
    """Lớp cơ sở cho collector.

    Cài đặt mới chỉ cần: đặt `source` và viết `collect()`.
    """

    #: Định danh nguồn — phải được lớp con ghi đè.
    source: ClassVar[SourceName]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def collect(self) -> list[Signal]:
        """Thu thập và trả về danh sách tín hiệu thô đã chuẩn hoá.

        Phải là idempotent và an toàn để gọi lặp lại (orchestrator chạy định kỳ).
        Ném ngoại lệ khi lỗi — orchestrator sẽ bắt, log, và bỏ qua nguồn này.
        """

    def is_configured(self) -> bool:
        """Collector đã đủ cấu hình (API key...) để chạy thật chưa?

        Mặc định: True (nguồn công khai). Nguồn cần key ghi đè để báo
        thiếu cấu hình thay vì lỗi lúc chạy.
        """
        return True

    @property
    def name(self) -> str:
        return self.source.value
