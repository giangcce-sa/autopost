"""Prompt theo từng định dạng — tách riêng để dễ A/B test và version hoá.

Mỗi hàm nhận một `Trend` và trả về (system_prompt, user_prompt). Giữ phần
"con người đọc" ở đây, tách khỏi phần gọi API (claude_client) và parse (generator).
"""

from __future__ import annotations

from trendos.models import Trend


def _trend_brief(trend: Trend) -> str:
    """Tóm tắt ngắn về xu hướng để nhồi vào prompt."""
    sources = ", ".join(s.value for s in trend.sources)
    titles = "\n".join(f"- {sig.title}" for sig in trend.signals[:5])
    return (
        f"Xu hướng: {trend.label}\n"
        f"Từ khoá: {', '.join(trend.keywords) or '(chưa có)'}\n"
        f"Nguồn: {sources}\n"
        f"Điểm momentum: {trend.score:.2f}\n"
        f"Tín hiệu tiêu biểu:\n{titles}"
    )


def social_post_prompt(trend: Trend) -> tuple[str, str]:
    system = (
        "Bạn là chuyên gia content social media, viết tiếng Việt tự nhiên, bắt trend nhanh. "
        "Luôn mở đầu bằng một hook mạnh và kết bằng CTA + hashtag."
    )
    user = (
        f"{_trend_brief(trend)}\n\n"
        "Viết một bài đăng mạng xã hội (Facebook/X/LinkedIn) khai thác xu hướng này. "
        "Yêu cầu: 1 hook ở dòng đầu, 2-4 câu nội dung súc tích, 1 CTA, 3-5 hashtag liên quan."
    )
    return system, user


def blog_article_prompt(trend: Trend) -> tuple[str, str]:
    system = (
        "Bạn là cây viết blog/SEO tiếng Việt. Viết bài có cấu trúc rõ ràng "
        "(tiêu đề, mở bài, các mục H2, kết luận), tối ưu từ khoá tự nhiên, không nhồi nhét."
    )
    user = (
        f"{_trend_brief(trend)}\n\n"
        "Viết một bài blog 600-900 từ chuẩn SEO bám theo xu hướng này. "
        "Gồm: tiêu đề hấp dẫn, meta description ~150 ký tự, thân bài có H2, kết luận có CTA."
    )
    return system, user


def video_script_prompt(trend: Trend) -> tuple[str, str]:
    system = (
        "Bạn là biên kịch video ngắn (TikTok/Reels/Shorts) tiếng Việt. "
        "Kịch bản phải giữ chân người xem trong 3 giây đầu."
    )
    user = (
        f"{_trend_brief(trend)}\n\n"
        "Viết kịch bản video ngắn 30-45 giây cho xu hướng này. "
        "Cấu trúc: HOOK (3s đầu) · NỘI DUNG (các cảnh kèm gợi ý hình ảnh) · CTA. "
        "Kèm gợi ý caption và hashtag."
    )
    return system, user
