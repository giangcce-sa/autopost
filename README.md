# autopost — AI Marketing Operating System (AI-MOS) cho Spa

Nền tảng **SaaS đa spa**: một "agency marketing AI" tự vận hành 24/7 chạy trọn phễu
từ nghiên cứu thị trường → ý tưởng → nội dung → đăng bài → ads → tối ưu → trả lời
khách → gom lead. Ranh giới hệ thống dừng ở **lead**; đặt lịch/doanh thu thật nằm ở
phần mềm quản lý spa riêng của khách hàng.

## Tài liệu

- [Thiết kế kiến trúc (AI-MOS Design)](docs/AI-MOS-DESIGN.md) — kiến trúc 3 tầng,
  10 agent (CEO + 9 chuyên trách), mô hình dữ liệu multi-tenant, orchestrator &
  lịch họp giao ban, phân tầng model & chi phí, guardrails, lộ trình theo phase.

## Tech stack (dự kiến)

Next.js 15 + TypeScript · Prisma + PostgreSQL · Anthropic SDK (Claude) ·
Job queue/scheduler · Tích hợp Facebook/Instagram/TikTok/Zalo + Meta/TikTok Ads ·
Bot Zalo/Telegram.

> Trạng thái: giai đoạn thiết kế. Xem design doc trước khi triển khai.
