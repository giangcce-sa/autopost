# TrendOS

**Hệ điều hành phát hiện xu hướng và sản xuất nội dung tự động.**

> Phát hiện thứ đang được quan tâm trên Internet **trước đám đông** và tự động biến nó thành nội dung có khả năng lan truyền.

---

## TrendOS làm gì

```
   Nguồn dữ liệu          Phát hiện              Sản xuất
   ─────────────          ──────────             ─────────
   Google Trends  ─┐
   X / Reddit      ├─►  Tín hiệu (Signal)  ─►  Chấm điểm   ─►  Cụm xu hướng  ─►  Sinh nội dung đa định dạng
   YouTube/TikTok  │    chuẩn hoá              (momentum,      (Trend)           - Post MXH
   RSS / HN        │                            độ mới,                          - Bài blog/SEO
   GitHub         ─┘                            đa nguồn)                         - Kịch bản video
```

TrendOS chạy theo một **pipeline** ba giai đoạn:

1. **Collect** — Nhiều *collector* thu thập tín hiệu thô từ các nền tảng, chuẩn hoá về một dạng chung (`Signal`).
2. **Detect** — Engine gom cụm tín hiệu thành xu hướng (`Trend`) và **chấm điểm theo đà tăng (velocity/acceleration)**, không chỉ theo độ phổ biến — đó là cách phát hiện *trước* đám đông.
3. **Generate** — Với mỗi xu hướng điểm cao, sinh nội dung đa định dạng bằng Claude API.

### Dây chuyền 9 AI Agent

Trên ba giai đoạn đó, hệ thống được tổ chức thành **9 AI agent chuyên biệt** (tầng `agents/`):

```
① Trend Hunter → ② Research → ③ Content Strategist →┬→ ④ Copywriter
                                                     ├→ ⑤ Image Creator
                                                     └→ ⑥ Video Producer
              ⑨ Learning ← ⑧ Analyst ← ⑦ Publisher ←──┘   (⑨ đóng vòng phản hồi)
```

Các agent trao đổi qua một bảng đen dùng chung (`PipelineContext`); orchestrator tuần tự gọi từng agent, bỏ qua agent chưa cấu hình. Chi tiết: [ARCHITECTURE.md §10](./ARCHITECTURE.md#10-kiến-trúc-9-ai-agent).

## Triết lý "trước đám đông"

Một thứ đã viral thì ai cũng thấy. TrendOS ưu tiên **gia tốc** (tốc độ tăng đang nhanh dần) và **độ mới**, đồng thời thưởng điểm khi một chủ đề xuất hiện đồng thời trên nhiều nguồn. Chủ đề đã bão hoà (volume cao nhưng đà chững) bị giảm điểm. Logic này nằm ở `trendos/detection/scorer.py`.

## Trạng thái hiện tại

🚧 **Giai đoạn: Khung + kiến trúc.** Toàn bộ *interface*, domain model, pipeline và API đã được dựng. Các collector và generator hiện là **stub có TODO** — sẵn sàng để cài đặt chi tiết từng phần.

Xem [ARCHITECTURE.md](./ARCHITECTURE.md) để hiểu thiết kế đầy đủ.

## Bắt đầu nhanh

```bash
# 1. Cài đặt (Python 3.11+)
pip install -e ".[dev]"

# 2. Cấu hình
cp .env.example .env
# điền ANTHROPIC_API_KEY và các API key nguồn dữ liệu

# 3. Chạy pipeline thử (dùng collector stub trả dữ liệu mẫu)
python -m trendos.cli run --dry-run

# 4. Chạy API server
uvicorn trendos.api.app:app --reload
# mở http://localhost:8000/docs
```

## Cấu trúc thư mục

```
trendos/
├── config.py            # Cấu hình (pydantic-settings, đọc từ .env)
├── models.py            # Domain models: Signal, Trend, ContentPiece + artifact 9 agent
├── agents/              # ★ Tầng 9 AI agent (đứng trên các tầng capability)
│   ├── base.py          #   BaseAgent (interface) + PipelineContext (blackboard)
│   ├── trend_hunter.py  #   ① bọc collectors + detection
│   ├── research.py, strategist.py, copywriter.py,
│   │   image_creator.py, video_producer.py,
│   │   publisher.py, analyst.py, learning.py   # ②–⑨
├── collectors/          # Nguồn dữ liệu (mỗi nền tảng một file)
│   ├── base.py          #   BaseCollector (interface)
│   ├── google_trends.py, reddit.py, twitter.py, youtube.py,
│   │   tiktok.py, hackernews.py, rss.py, github.py
├── detection/           # Engine phát hiện xu hướng
│   ├── scorer.py        #   Chấm điểm momentum/độ mới/đa nguồn
│   ├── dedup.py         #   Gom cụm tín hiệu giống nhau
│   └── ranker.py        #   Xếp hạng & lọc top
├── generation/          # Sản xuất nội dung
│   ├── base.py          #   BaseGenerator (interface)
│   ├── claude_client.py #   Wrapper Anthropic SDK
│   ├── prompts.py       #   Prompt theo từng định dạng
│   ├── social_post.py, blog_article.py, video_script.py
├── pipeline/
│   └── orchestrator.py  # Nối collect → detect → generate
├── storage/
│   └── repository.py    # Lớp trừu tượng lưu trữ
├── api/
│   ├── app.py           # FastAPI app
│   └── routes/          # /trends, /content
└── cli.py               # Entry point dòng lệnh
```

## Lộ trình

- [x] Khung dự án + kiến trúc + interface
- [x] Khung dây chuyền 9 AI agent (interface `BaseAgent` + blackboard + orchestrator)
- [ ] Cài đặt collector thật (bắt đầu: Hacker News + RSS — không cần API key)
- [ ] Engine chấm điểm momentum với dữ liệu chuỗi thời gian
- [ ] Cài đặt thật các agent ②–⑨ (Research, Strategist, Image, Video, Publisher, Analyst, Learning)
- [ ] Lưu trữ bền (SQLite → Postgres)
- [ ] Lập lịch chạy định kỳ
- [ ] Dashboard web

## Giấy phép

TBD
