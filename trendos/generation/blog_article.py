"""Generator: bài blog chuẩn SEO (đầu ra dài → dùng streaming)."""

from __future__ import annotations

from trendos.generation.base import BaseGenerator
from trendos.generation.prompts import blog_article_prompt
from trendos.models import ContentFormat, ContentPiece, Trend


class BlogArticleGenerator(BaseGenerator):
    format = ContentFormat.BLOG_ARTICLE

    async def generate(self, trend: Trend) -> ContentPiece:
        system, user = blog_article_prompt(trend)
        # Bài dài → stream để tránh timeout HTTP.
        body = await self.client.complete(user, system=system, max_tokens=4096, stream=True)
        # TODO(impl): tách meta description ra ContentPiece.meta["meta_description"].
        return ContentPiece(
            trend_id=trend.id,
            format=self.format,
            title=trend.label,
            body=body,
        )
