# Kiến trúc TrendOS

Tài liệu này mô tả thiết kế của TrendOS: các thành phần, luồng dữ liệu, và những quyết định kiến trúc cốt lõi. Mục tiêu là một hệ thống **dễ mở rộng từng phần** — thêm một nguồn dữ liệu hay một định dạng nội dung không được đụng tới phần còn lại.

## 1. Tổng quan luồng

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
│  COLLECT    │──►│   DETECT     │──►│   GENERATE    │──►│   STORE/API  │
│ collectors/ │   │ detection/   │   │ generation/   │   │ storage/,api/│
└─────────────┘   └──────────────┘   └───────────────┘   └──────────────┘
   Signal[]          Trend[]            ContentPiece[]        persisted
```

Toàn bộ được nối lại trong `pipeline/orchestrator.py`. Mỗi giai đoạn nhận đầu ra của giai đoạn trước qua **domain model** rõ ràng (`models.py`), nên có thể test và thay thế độc lập.

## 2. Domain models (`trendos/models.py`)

Ba kiểu dữ liệu xương sống, đều là `pydantic.BaseModel` (immutable nơi hợp lý):

| Model | Ý nghĩa | Trường chính |
|---|---|---|
| `Signal` | Một quan sát thô từ một nguồn, đã chuẩn hoá | `source`, `external_id`, `title`, `url`, `metrics`, `keywords`, `captured_at` |
| `Trend` | Một cụm tín hiệu được nhận diện là cùng một xu hướng | `id`, `label`, `keywords`, `signals`, `score`, `momentum`, `first_seen`, `sources` |
| `ContentPiece` | Một mẩu nội dung được sinh ra cho một xu hướng | `trend_id`, `format`, `title`, `body`, `meta`, `created_at` |

`Signal.metrics` là `dict[str, float]` mở (vd. `views`, `upvotes`, `search_index`) để mỗi nguồn báo cáo số liệu riêng mà không phá vỡ schema chung.

## 3. COLLECT — nguồn dữ liệu (`trendos/collectors/`)

### Interface

Mọi collector kế thừa `BaseCollector` (`collectors/base.py`):

```python
class BaseCollector(ABC):
    source: ClassVar[SourceName]          # định danh nguồn
    @abstractmethod
    async def collect(self) -> list[Signal]: ...
```

`collect()` là **async** vì hầu hết nguồn là I/O mạng — chạy song song nhiều collector dễ dàng bằng `asyncio.gather`.

### Các collector

| Nguồn | File | Cần API key? | Ghi chú |
|---|---|---|---|
| Hacker News | `hackernews.py` | Không | Firebase API công khai — **nên cài đầu tiên** |
| RSS / News | `rss.py` | Không | `feedparser`, danh sách feed cấu hình được |
| GitHub | `github.py` | Token (tuỳ chọn) | Trending repos, sự kiện star tăng đột biến |
| Google Trends | `google_trends.py` | Không chính thức | Qua `pytrends` (không official, dễ rate-limit) |
| Reddit | `reddit.py` | Có | PRAW / API; subreddit hot, rising |
| X (Twitter) | `twitter.py` | Có (trả phí) | API v2; cân nhắc chi phí |
| YouTube | `youtube.py` | Có | Data API v3, mục `mostPopular` |
| TikTok | `tiktok.py` | Không chính thức | Khó — qua API bên thứ ba/unofficial |

> **Khuyến nghị triển khai theo thứ tự "rào cản thấp trước":** Hacker News → RSS → GitHub → Google Trends → Reddit → YouTube → X → TikTok. Bốn nguồn đầu không/ít cần API key trả phí, đủ để chạy pipeline thật sớm.

### Khả năng chịu lỗi

Một collector hỏng (rate-limit, đổi schema) **không được làm sập pipeline**. Orchestrator gọi từng collector trong khối bắt lỗi, log cảnh báo, và tiếp tục với các nguồn còn lại.

## 4. DETECT — engine phát hiện xu hướng (`trendos/detection/`)

Đây là phần tạo nên giá trị "trước đám đông". Ba bước:

### 4.1 Dedup / clustering (`dedup.py`)

Gom các `Signal` nói về cùng một chủ đề (vd. cùng một sản phẩm xuất hiện trên HN, Reddit, GitHub) thành một `Trend`. Khởi đầu: chuẩn hoá keyword + so khớp mờ (fuzzy/embedding). Mở rộng sau: embedding semantic + clustering.

### 4.2 Scoring (`scorer.py`) — trái tim của hệ thống

Điểm xu hướng là tổ hợp có trọng số:

```
score = w_v · velocity        # tốc độ tăng (đạo hàm bậc 1 của volume theo thời gian)
      + w_a · acceleration    # gia tốc      (đạo hàm bậc 2)  ← tín hiệu "sớm" quan trọng nhất
      + w_n · novelty         # độ mới        (mới xuất hiện = điểm cao)
      + w_x · cross_source    # số nguồn độc lập cùng nhắc tới
      − w_s · saturation      # phạt nếu volume đã rất cao mà đà chững (đám đông đã biết)
```

**Lý do:** thứ đã viral có `velocity` cao nhưng `acceleration` thấp và `saturation` cao → điểm bị kéo xuống. Thứ đang chớm nổi có `acceleration` và `novelty` cao → nổi lên đầu bảng. Trọng số `w_*` nằm trong `config.py` để tinh chỉnh.

> Velocity/acceleration cần **chuỗi thời gian**: cùng một tín hiệu phải được quan sát qua nhiều lần chạy. Vì vậy storage lưu lịch sử metric theo `(external_id, captured_at)`; scorer đọc lại để tính đạo hàm.

### 4.3 Ranking (`ranker.py`)

Sắp xếp `Trend` theo điểm, lọc ngưỡng tối thiểu, giới hạn top-N để đưa sang giai đoạn sinh nội dung (kiểm soát chi phí Claude API).

## 5. GENERATE — sản xuất nội dung (`trendos/generation/`)

### Interface

```python
class BaseGenerator(ABC):
    format: ClassVar[ContentFormat]
    @abstractmethod
    async def generate(self, trend: Trend) -> ContentPiece: ...
```

### Các generator (đa định dạng)

| Định dạng | File | Đầu ra |
|---|---|---|
| Post MXH | `social_post.py` | Caption + hook + hashtag cho FB/X/LinkedIn |
| Bài blog/SEO | `blog_article.py` | Bài dài chuẩn SEO bám keyword |
| Kịch bản video | `video_script.py` | Hook · nội dung · CTA cho Shorts/Reels/TikTok |

### Tích hợp Claude

`generation/claude_client.py` là wrapper mỏng quanh **Anthropic Python SDK**:

- Model mặc định: `claude-opus-4-8`.
- **Adaptive thinking** (`thinking={"type": "adaptive"}`) cho tác vụ sáng tạo/suy luận.
- **Streaming** cho đầu ra dài (bài blog) để tránh timeout HTTP.
- Prompt theo từng định dạng tách riêng ở `prompts.py` để dễ A/B và version hoá.

Mỗi generator chỉ lo "prompt + parse"; phần gọi API tập trung một chỗ.

## 6. STORE (`trendos/storage/`)

`storage/repository.py` định nghĩa interface lưu trữ (`save_signals`, `get_signal_history`, `save_trend`, `save_content`...). Cài đặt khởi đầu: **SQLite** (đủ cho một máy, không cần hạ tầng). Vì là interface, có thể đổi sang Postgres/ClickHouse khi cần chuỗi thời gian quy mô lớn mà không sửa pipeline.

Lưu lịch sử metric là **bắt buộc** để scorer tính velocity/acceleration (xem 4.2).

## 7. API (`trendos/api/`)

FastAPI app (`api/app.py`) phơi bày:

- `GET /trends` — danh sách xu hướng đã phát hiện, có điểm.
- `GET /trends/{id}` — chi tiết + các tín hiệu nguồn.
- `GET /content` — nội dung đã sinh, lọc theo định dạng/xu hướng.
- `POST /pipeline/run` — kích hoạt một lần chạy pipeline (async/background).
- `GET /health` — health check.

API và CLI (`cli.py`) là **hai mặt tiền** cùng gọi vào `pipeline/orchestrator.py` — không nhân đôi logic.

## 8. Lập lịch & vận hành

Giai đoạn sau: chạy `orchestrator.run()` định kỳ (vd. mỗi 15 phút) bằng APScheduler hoặc cron/worker bên ngoài. Mỗi lần chạy bồi đắp lịch sử metric, làm điểm momentum ngày càng chính xác.

## 9. Quyết định kiến trúc tóm tắt

| Quyết định | Lý do |
|---|---|
| Domain model chung (`Signal`/`Trend`/`ContentPiece`) | Tách rời 3 giai đoạn; test & thay thế độc lập |
| Collector async + cô lập lỗi | Nhiều nguồn I/O; một nguồn hỏng không sập cả hệ |
| Chấm điểm theo gia tốc + độ mới, phạt bão hoà | Hiện thực hoá sứ mệnh "trước đám đông" |
| Lưu lịch sử metric | Điều kiện cần để tính velocity/acceleration |
| Generator theo interface | Thêm định dạng mới không đụng phần khác |
| Claude client tập trung | Một nơi quản model/thinking/streaming/chi phí |
| API & CLI cùng gọi orchestrator | Không nhân đôi logic nghiệp vụ |

---

## 10. Kiến trúc 9 AI Agent

Trên ba tầng chức năng (§3–§5), TrendOS được tổ chức thành một **dây chuyền 9 AI agent chuyên biệt** — một "nhà máy nội dung" chạy nối tiếp và có vòng học phản hồi. Tầng agent (`trendos/agents/`) **đứng trên** tầng capability: mỗi agent điều phối capability (collectors/detection/generation...) và thêm logic AI riêng.

```
① Trend Hunter → ② Research → ③ Content Strategist →┬→ ④ Copywriter ──┐
                                                     ├→ ⑤ Image Creator┤
                                                     └→ ⑥ Video Producer┘
                                                              ↓
              ⑨ Learning ← ⑧ Analyst ← ⑦ Publisher ←─────────┘
                   └──── vòng phản hồi: tinh chỉnh ①③④ ────┘
```

### 10.1 Vai trò, loại AI và đầu vào → đầu ra

| # | Agent (`agents/`) | Đầu vào → Đầu ra | Loại AI / công nghệ |
|---|---|---|---|
| ① | `trend_hunter.py` | Internet → `Trend[]` | Collectors + embedding/ML chấm điểm momentum |
| ② | `research.py` | `Trend` → `ResearchBrief` | Claude + web search/fetch |
| ③ | `strategist.py` | `ResearchBrief` → `ContentPlan` | Claude (planner/điều phối) |
| ④ | `copywriter.py` | `ContentPlan` → `ContentPiece[]` | Claude (qua tầng `generation/`) |
| ⑤ | `image_creator.py` | `ContentPiece` → `MediaAsset` (ảnh) | Text-to-image (provider ngoài) |
| ⑥ | `video_producer.py` | script + ảnh → `MediaAsset` (video) | TTS + dựng video (provider ngoài) |
| ⑦ | `publisher.py` | nội dung → `Publication` | API nền tảng + lên lịch |
| ⑧ | `analyst.py` | `Publication` → `PerformanceReport` | Thu metric + Claude diễn giải |
| ⑨ | `learning.py` | `PerformanceReport` → `LearningUpdate` | ML tối ưu + Claude (vòng phản hồi) |

Ba "chất liệu AI" khác nhau: **LLM/Claude** (②③④⑧⑨), **embedding/ML** (① và tối ưu ở ⑨), **provider/API ngoài** (⑤⑥⑦). LLM chạy chọn lọc trên top-N để kiểm soát chi phí; tầng phân tích (①) rẻ và chạy số lượng lớn.

### 10.2 Blackboard — `PipelineContext`

Các agent không gọi trực tiếp lẫn nhau; chúng trao đổi qua một **bảng đen** dùng chung (`agents/base.py:PipelineContext`) mang mọi artifact: `trends`, `briefs`, `plans`, `content`, `assets`, `publications`, `reports`. Mỗi agent đọc artifact của agent trước và ghi artifact của mình. Ưu điểm: pipeline nhiều bước với kiểu dữ liệu khác nhau vẫn ghép nối gọn, thêm agent không phá interface chung.

### 10.3 Interface & điều phối

```python
class BaseAgent(ABC):
    name: ClassVar[str]
    async def run(self, ctx: PipelineContext) -> None: ...   # đọc/ghi ctx
    def is_ready(self, settings) -> bool: ...                # check khoá/provider
```

`agents/__init__.py:AGENT_PIPELINE` giữ thứ tự ①→⑨. `pipeline/orchestrator.py` là **nhạc trưởng mỏng**: lặp danh sách này, bỏ qua agent `is_ready()==False`, gọi `run(ctx)` trong khối bắt lỗi (cô lập lỗi từng agent). `--dry-run` chỉ chạy `DRY_RUN_AGENTS` (Trend Hunter — không gọi Claude/provider).

### 10.4 Quan hệ với tầng capability

| Agent | Bọc capability nào |
|---|---|
| ① Trend Hunter | `collectors/` + `detection/` (toàn bộ logic collect→cluster→score→rank) |
| ④ Copywriter | `generation/` (chọn generator theo `ContentPlan.items[].format`) |
| ②③⑧⑨ | `generation/claude_client.py` (gọi Claude) |
| ⑤⑥⑦ | provider/API ngoài (chưa có capability nội bộ) |

### 10.5 Trạng thái

🟡 **① Trend Hunter** và **④ Copywriter** đã bọc code thật (momentum & sinh nội dung vẫn ở mức stub bên dưới). 🔴 **②③⑤⑥⑦⑧⑨** là stub có TODO. Dây chuyền chạy thông end-to-end ở `--dry-run`; agent thiếu cấu hình bị bỏ qua an toàn.
