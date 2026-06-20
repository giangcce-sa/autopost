"""Generator: bài đăng mạng xã hội (caption + hook + hashtag)."""

from __future__ import annotations

from trendos.generation.base import BaseGenerator
from trendos.generation.prompts import social_post_prompt
from trendos.models import ContentFormat, ContentPiece, ContentPlanItem, Trend
from trendos.text import extract_hashtags


class SocialPostGenerator(BaseGenerator):
    format = ContentFormat.SOCIAL_POST

    async def generate(self, trend: Trend, item: ContentPlanItem | None = None) -> ContentPiece:
        angle = item.angle if item else ""
        tone = item.tone if item else ""
        system, user = social_post_prompt(trend, angle=angle, tone=tone)
        body = await self.client.complete(user, system=system, max_tokens=1024)

        meta: dict[str, str] = {}
        hashtags = extract_hashtags(body)
        if hashtags:
            meta["hashtags"] = " ".join(hashtags)
        if item and item.channel:
            meta["channel"] = item.channel
        return ContentPiece(
            trend_id=trend.id,
            format=self.format,
            title=trend.label,
            body=body,
            meta=meta,
        )
