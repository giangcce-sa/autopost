"""Tầng AGENT — dây chuyền 9 AI agent của TrendOS.

`AGENT_PIPELINE` là thứ tự chạy chuẩn (①→⑨). Orchestrator lặp qua danh sách
này. Thêm/đổi chỗ agent = sửa danh sách này, không đụng orchestrator.
"""

from __future__ import annotations

from trendos.agents.analyst import AnalystAgent
from trendos.agents.base import BaseAgent, PipelineContext
from trendos.agents.copywriter import CopywriterAgent
from trendos.agents.image_creator import ImageCreatorAgent
from trendos.agents.learning import LearningAgent
from trendos.agents.publisher import PublisherAgent
from trendos.agents.research import ResearchAgent
from trendos.agents.strategist import ContentStrategistAgent
from trendos.agents.trend_hunter import TrendHunterAgent
from trendos.agents.video_producer import VideoProducerAgent

#: Dây chuyền agent theo đúng thứ tự ①→⑨.
AGENT_PIPELINE: list[type[BaseAgent]] = [
    TrendHunterAgent,        # ①
    ResearchAgent,           # ②
    ContentStrategistAgent,  # ③
    CopywriterAgent,         # ④
    ImageCreatorAgent,       # ⑤
    VideoProducerAgent,      # ⑥
    PublisherAgent,          # ⑦
    AnalystAgent,            # ⑧
    LearningAgent,           # ⑨
]

#: Agent chạy ở chế độ --dry-run (chỉ phân tích, không gọi LLM/provider).
DRY_RUN_AGENTS: list[type[BaseAgent]] = [TrendHunterAgent]

__all__ = ["BaseAgent", "PipelineContext", "AGENT_PIPELINE", "DRY_RUN_AGENTS"]
