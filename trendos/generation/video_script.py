"""Generator: kịch bản video ngắn (hook · nội dung · CTA)."""

from __future__ import annotations

from trendos.generation.base import BaseGenerator
from trendos.generation.prompts import video_script_prompt
from trendos.models import ContentFormat, ContentPiece, ContentPlanItem, Trend


class VideoScriptGenerator(BaseGenerator):
    format = ContentFormat.VIDEO_SCRIPT

    async def generate(self, trend: Trend, item: ContentPlanItem | None = None) -> ContentPiece:
        angle = item.angle if item else ""
        tone = item.tone if item else ""
        system, user = video_script_prompt(trend, angle=angle, tone=tone)
        body = await self.client.complete(user, system=system, max_tokens=2048)
        meta = {"channel": item.channel} if item and item.channel else {}
        return ContentPiece(
            trend_id=trend.id,
            format=self.format,
            title=trend.label,
            body=body,
            meta=meta,
        )
