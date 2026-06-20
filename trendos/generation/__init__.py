"""Tầng GENERATE — sản xuất nội dung đa định dạng qua Claude.

`ALL_GENERATORS` là registry để orchestrator sinh mọi định dạng cho một xu hướng.
Thêm định dạng mới = viết lớp `BaseGenerator` rồi thêm vào đây.
"""

from __future__ import annotations

from trendos.generation.base import BaseGenerator
from trendos.generation.blog_article import BlogArticleGenerator
from trendos.generation.claude_client import ClaudeClient
from trendos.generation.social_post import SocialPostGenerator
from trendos.generation.video_script import VideoScriptGenerator

ALL_GENERATORS: list[type[BaseGenerator]] = [
    SocialPostGenerator,
    BlogArticleGenerator,
    VideoScriptGenerator,
]

__all__ = ["BaseGenerator", "ClaudeClient", "ALL_GENERATORS"]
