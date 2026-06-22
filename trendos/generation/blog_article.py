"""Generator: bài blog chuẩn SEO (đầu ra dài → dùng streaming)."""

from __future__ import annotations

from textwrap import shorten

from trendos.generation.base import BaseGenerator
from trendos.generation.prompts import blog_article_prompt
from trendos.models import ContentFormat, ContentPiece, ContentPlanItem, Trend


class BlogArticleGenerator(BaseGenerator):
    format = ContentFormat.BLOG_ARTICLE

    async def generate(self, trend: Trend, item: ContentPlanItem | None = None) -> ContentPiece:
        angle = item.angle if item else ""
        tone = item.tone if item else ""
        system, user = blog_article_prompt(trend, angle=angle, tone=tone)
        # Bài dài → stream để tránh timeout HTTP.
        body = await self.client.complete(user, system=system, max_tokens=4096, stream=True)
        meta = {"channel": item.channel} if item and item.channel else {}
        meta["meta_description"] = shorten(" ".join(body.split()), width=160, placeholder="...")
        return ContentPiece(
            trend_id=trend.id,
            format=self.format,
            title=trend.label,
            body=body,
            meta=meta,
        )
