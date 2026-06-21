"""Local provider adapters for end-to-end development.

These adapters avoid external side effects: images are SVG files, videos are
script/storyboard text files, publishing writes JSON receipts, and analytics is
deterministic from publication metadata.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from textwrap import shorten

from trendos.config import Settings
from trendos.models import ContentPiece, MediaAsset, Publication


class LocalImageProvider:
    def __init__(self, output_dir: str) -> None:
        self._dir = Path(output_dir) / "images"
        self._dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, prompt: str) -> str:
        path = self._dir / f"image-{abs(hash(prompt))}.svg"
        title = escape(shorten(prompt, width=80, placeholder="..."))
        svg = "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"',
                ' viewBox="0 0 1200 630">',
                "<defs>",
                '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">',
                '<stop stop-color="#111827"/>',
                '<stop offset="1" stop-color="#2563eb"/>',
                "</linearGradient>",
                "</defs>",
                '<rect width="1200" height="630" fill="url(#g)"/>',
                '<circle cx="980" cy="120" r="180" fill="#ffffff" opacity="0.12"/>',
                '<text x="72" y="120" fill="#93c5fd" font-family="Arial, sans-serif"',
                ' font-size="32" font-weight="700">TrendOS</text>',
                '<text x="72" y="290" fill="#ffffff" font-family="Arial, sans-serif"',
                f' font-size="54" font-weight="800">{title}</text>',
                '<text x="72" y="520" fill="#dbeafe" font-family="Arial, sans-serif"',
                ' font-size="28">Local generated visual</text>',
                "</svg>",
            ]
        )
        path.write_text(svg, encoding="utf-8")
        return str(path)


class LocalVideoProvider:
    def __init__(self, output_dir: str) -> None:
        self._dir = Path(output_dir) / "videos"
        self._dir.mkdir(parents=True, exist_ok=True)

    async def produce(self, script: str, image_uris: list[str]) -> str:
        path = self._dir / f"video-{abs(hash(script))}.md"
        body = {
            "script": script,
            "image_uris": image_uris,
            "note": "Local storyboard placeholder. Replace with real video adapter in production.",
        }
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)


class LocalPublishProvider:
    def __init__(self, output_dir: str) -> None:
        self._dir = Path(output_dir) / "publications"
        self._dir.mkdir(parents=True, exist_ok=True)

    async def publish(
        self, piece: ContentPiece, assets: list[MediaAsset], channel: str
    ) -> dict:
        platform = channel or "local"
        path = self._dir / f"publication-{piece.id}.json"
        receipt = {
            "content": piece.model_dump(mode="json"),
            "assets": [a.model_dump(mode="json") for a in assets],
            "platform": platform,
            "status": "published",
        }
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"platform": platform, "external_url": str(path), "status": "published"}


class LocalAnalyticsProvider:
    async def fetch(self, publication: Publication) -> dict[str, float]:
        seed = sum(ord(c) for c in publication.id + publication.platform)
        likes = float(10 + seed % 90)
        shares = float(3 + seed % 30)
        reach = float(500 + seed % 5000)
        return {
            "reach": reach,
            "likes": likes,
            "shares": shares,
            "engagement_rate": min(1.0, (likes + shares) / reach),
        }


def image_provider(settings: Settings) -> LocalImageProvider:
    return LocalImageProvider(settings.output_dir)


def video_provider(settings: Settings) -> LocalVideoProvider:
    return LocalVideoProvider(settings.output_dir)


def publish_provider(settings: Settings) -> LocalPublishProvider:
    return LocalPublishProvider(settings.output_dir)


def analytics_provider(settings: Settings) -> LocalAnalyticsProvider:
    return LocalAnalyticsProvider()
