"""Interface chung cho mọi AI agent + blackboard context dùng chung.

Dây chuyền 9 agent (Trend Hunter → ... → Learning) trao đổi qua một
`PipelineContext`: mỗi agent đọc artifact của agent trước và ghi artifact của
mình. Cách này hợp với pipeline nhiều bước có kiểu dữ liệu khác nhau, và giữ
cùng phong cách interface-rõ-ràng như BaseCollector/BaseGenerator. Xem
ARCHITECTURE.md §10.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from trendos.config import Settings
from trendos.models import (
    ContentPiece,
    ContentPlan,
    LearningUpdate,
    MediaAsset,
    PerformanceReport,
    Publication,
    ResearchBrief,
    Trend,
)
from trendos.storage import Repository


@dataclass
class PipelineContext:
    """Bảng đen (blackboard) mang toàn bộ artifact qua dây chuyền agent.

    Là dataclass (không phải pydantic) vì giữ các đối tượng runtime như
    `Settings` và `Repository`.
    """

    settings: Settings
    repo: Repository

    # Artifact, điền dần qua từng agent.
    trends: list[Trend] = field(default_factory=list)
    briefs: dict[str, ResearchBrief] = field(default_factory=dict)  # theo trend_id
    plans: dict[str, ContentPlan] = field(default_factory=dict)  # theo trend_id
    content: list[ContentPiece] = field(default_factory=list)
    assets: list[MediaAsset] = field(default_factory=list)
    publications: list[Publication] = field(default_factory=list)
    reports: list[PerformanceReport] = field(default_factory=list)
    learning: list[LearningUpdate] = field(default_factory=list)


class BaseAgent(ABC):
    """Lớp cơ sở cho một AI agent trong dây chuyền.

    Cài đặt mới chỉ cần: đặt `name` và viết `run()`. Agent đọc/ghi `ctx` tại chỗ.
    """

    #: Tên agent (để log & registry) — lớp con phải ghi đè.
    name: ClassVar[str]

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> None:
        """Thực thi agent: đọc artifact cần dùng từ `ctx`, ghi kết quả vào `ctx`.

        Ném ngoại lệ khi lỗi — orchestrator bắt, log, và tiếp tục agent sau
        (cô lập lỗi).
        """

    def is_ready(self, settings: Settings) -> bool:
        """Agent đã đủ cấu hình (API key, provider...) để chạy thật chưa?

        Mặc định True. Agent cần khoá/provider ghi đè để được bỏ qua an toàn
        khi thiếu cấu hình thay vì lỗi lúc chạy.
        """
        return True
