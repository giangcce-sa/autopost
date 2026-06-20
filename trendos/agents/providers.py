"""Interface provider cho các agent phụ thuộc dịch vụ ngoài (⑤⑥⑦⑧).

Claude không tạo ảnh/video, cũng không đăng bài — các agent này gọi dịch vụ
bên ngoài. Ta định nghĩa interface provider (Protocol) để **logic agent hoàn
chỉnh và test được** (tiêm provider giả), còn adapter thật (Stability,
ElevenLabs, Meta Graph API, ...) cắm vào sau mà không sửa agent.
"""

from __future__ import annotations

from typing import Protocol

from trendos.models import ContentPiece, MediaAsset, Publication


class ImageProvider(Protocol):
    """Sinh ảnh từ prompt, trả về URI ảnh."""

    async def generate(self, prompt: str) -> str: ...


class VideoProvider(Protocol):
    """Dựng video từ kịch bản + (tuỳ chọn) ảnh, trả về URI video."""

    async def produce(self, script: str, image_uris: list[str]) -> str: ...


class PublishProvider(Protocol):
    """Đăng/đặt lịch một mẩu nội dung lên một kênh.

    Trả về dict: {"platform": str, "external_url": str|None, "status": str}.
    """

    async def publish(
        self, piece: ContentPiece, assets: list[MediaAsset], channel: str
    ) -> dict: ...


class AnalyticsProvider(Protocol):
    """Lấy metric hiệu suất của một bài đã đăng."""

    async def fetch(self, publication: Publication) -> dict[str, float]: ...


class ProviderNotConfigured(RuntimeError):
    """Ném khi agent được gọi nhưng chưa có adapter provider thật.

    Orchestrator bắt và bỏ qua (cô lập lỗi). Cắm adapter thật bằng cách tiêm
    provider vào agent (hoặc mở rộng factory dựng-từ-settings).
    """
