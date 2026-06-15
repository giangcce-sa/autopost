# autopost — AI Marketing Operating System (AI-MOS) cho Spa

Nền tảng **SaaS đa spa**: một "agency marketing AI" tự vận hành 24/7 chạy trọn phễu
từ nghiên cứu thị trường → ý tưởng → nội dung → đăng bài → ads → tối ưu → trả lời
khách → gom lead. Ranh giới hệ thống dừng ở **lead**; đặt lịch/doanh thu thật nằm ở
phần mềm quản lý spa riêng của khách hàng.

> Tài liệu thiết kế đầy đủ: [docs/AI-MOS-DESIGN.md](docs/AI-MOS-DESIGN.md)

## Tech stack

Next.js 15 (App Router) + TypeScript · Prisma + PostgreSQL · Anthropic SDK (Claude) ·
cron scheduler (Vercel Cron) · connector kênh/ads (mock + interface cho live) ·
notifier Zalo/Telegram.

## Cấu trúc

```
prisma/schema.prisma        Mô hình dữ liệu multi-tenant (10 agent, compliance, ads)
prisma/seed.ts              Tạo spa demo + dịch vụ + kênh + campaign mẫu
src/lib/anthropic.ts        Client Claude + phân tầng model + trần chi phí AI
src/lib/agents/             10 agent: ceo, intel, strategy, content, ads, optimizer, reply, analytics
src/lib/compliance/         Guardrail pháp lý quảng cáo làm đẹp VN
src/lib/connectors/         Kênh (FB/IG/TikTok/Zalo) + Ads (Meta/TikTok) — mock + interface
src/lib/notify/             Notifier Zalo/Telegram (mock console / Telegram thật)
src/lib/orchestrator/       standup (giao ban 8h), optimize (3h), publisher
src/app/                    Dashboard (Tổng quan/Nội dung/Lead/Ads/Mục tiêu) + API routes
vercel.json                 Lịch cron 24/7
```

## Chạy local

```bash
cp .env.example .env          # điền DATABASE_URL, ANTHROPIC_API_KEY, CHANNEL_TOKEN_SECRET
#   sinh secret: openssl rand -hex 32
npm install
npm run prisma:migrate        # tạo bảng (cần PostgreSQL)
npm run db:seed               # tạo spa demo
npm run dev                   # mở http://localhost:3000

# Chạy thủ công các nhịp agent (cần ANTHROPIC_API_KEY):
npm run agent:standup         # họp giao ban: intel→strategy→content→CEO→cổng duyệt
npm run agent:optimize        # tối ưu ads cấp danh mục
npm run agent:publish         # đăng các bài tới hạn
```

API: `POST /api/cron/standup`, `/api/cron/optimize`, `/api/cron/publish`
(bảo vệ bằng header `x-cron-secret` hoặc `Authorization: Bearer <CRON_SECRET>`),
webhook inbox `POST /api/webhooks/reply`, cổng duyệt `POST /api/approvals`,
`GET /api/health`.

## Ánh xạ Phase (đã triển khai khung)

| Phase | Trạng thái trong code |
|---|---|
| **0 — Nền tảng** | ✅ Next.js + Prisma multi-tenant + orchestrator + scheduler + guardrail/AgentRun |
| **1 — Lõi nội dung** | ✅ CEO + Intel + Strategy + Content + Publisher (4 kênh, mock) + dashboard + bản tin |
| **2 — Tương tác & lead** | ✅ Social Care (reply) + Lead Collector + webhook + trang Lead |
| **3 — Ads loop** | ✅ Media Buyer + Optimizer + guardrail ngân sách (connector mock) |
| **4 — Đóng vòng** | ✅ Analytics + dashboard + cổng duyệt Zalo/Telegram; doanh thu phản hồi tùy chọn |

## Chế độ connector

`CONNECTOR_MODE=mock` (mặc định) — sandbox, không gọi API thật (chờ app review
FB/IG/TikTok/Zalo/Ads). Cắm connector `live` qua `registerChannelConnector` /
`registerAdsConnector` khi có token hợp lệ.

> ⚠️ Kênh/Ads thật cần app review + token + ngân sách. Phần pháp lý là định hướng
> kỹ thuật, **không thay tư vấn luật** — xem docs/AI-MOS-DESIGN.md mục 13.
