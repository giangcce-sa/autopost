"""Generator: bài đăng mạng xã hội (caption + hook + hashtag)."""

from __future__ import annotations

from trendos.generation.base import BaseGenerator
from trendos.generation.prompts import social_post_prompt
from trendos.models import ContentFormat, ContentPiece, Trend


class SocialPostGenerator(BaseGenerator):
    format = ContentFormat.SOCIAL_POST

    async def generate(self, trend: Trend) -> ContentPiece:
        system, user = social_post_prompt(trend)
        body = await self.client.complete(user, system=system, max_tokens=1024)
        # TODO(impl): parse tách hashtag/CTA vào ContentPiece.meta nếu cần.
        return ContentPiece(
            trend_id=trend.id,
            format=self.format,
            title=trend.label,
            body=body,
        )
