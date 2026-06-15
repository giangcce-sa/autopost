# AI Marketing Operating System (AI-MOS) cho Spa — Tài liệu thiết kế

> Phiên bản: 0.1 (bản nháp kiến trúc đầu tiên)
> Phạm vi: Nền tảng SaaS đa spa — cỗ máy marketing tự vận hành 24/7, ranh giới dừng ở **lead**.

---

## 1. Tầm nhìn & mục tiêu

Xây dựng một **"agency marketing AI" thu nhỏ** chạy 24/7 cho ngành spa, mô hình hóa như một sơ đồ tổ chức gồm các "nhân viên AI" (agent) có một CEO Agent điều phối. Hệ thống chạy trọn phễu marketing:

```
Nghiên cứu thị trường → Lên ý tưởng → Sản xuất nội dung → Đăng bài
   → Chạy ads → Tối ưu ads → Trả lời khách → Gom lead → [Bàn giao thủ công]
```

**Ranh giới hệ thống:** kết thúc ở **lead**. Việc đặt lịch, thu tiền, doanh thu thật nằm ở **phần mềm quản lý spa riêng** của từng khách hàng (ngoài phạm vi). Lead được bàn giao thủ công (Zalo/Telegram + dashboard + CSV).

**Mô hình kinh doanh:** SaaS đa spa (multi-tenant) — bán cho nhiều spa, mỗi spa là một tenant độc lập.

### Mục tiêu phi chức năng
- **Tự trị:** mặc định **Full-auto** trong guardrails; cổng phê duyệt qua Zalo/Telegram.
- **Chi phí kiểm soát được:** trần ngân sách ads + trần chi phí AI theo từng tenant.
- **An toàn:** cô lập dữ liệu theo tenant; lưu token kênh mã hóa; guardrails nội dung ngành làm đẹp.

---

## 2. Quyết định đã chốt

| Hạng mục | Quyết định |
|---|---|
| Mô hình | SaaS đa spa (multi-tenant) |
| Bản chất | Cỗ máy marketing tự vận hành 24/7, ranh giới dừng ở **lead** |
| Stack | Next.js 15 (App Router) + TypeScript + Prisma + PostgreSQL + Anthropic SDK |
| Kênh | Facebook Page, Instagram, TikTok, Zalo OA |
| Nhân sự AI | CEO Agent + 9 agent chuyên trách |
| Nhịp vận hành | Họp giao ban 8h sáng (CEO ra quyết định) + Optimizer mỗi 3h |
| Bộ não | Bộ nhớ chung (DB) + orchestrator viết bằng code (MCP cho tool) |
| Tự trị | Full-auto, cổng duyệt qua Zalo/Telegram |
| Guardrails | Trần ngân sách ads, duyệt content nhạy cảm, trần chi phí AI, phân tầng model |
| Bàn giao | Lead → Zalo/Telegram + dashboard + CSV → nhập tay vào phần mềm spa |
| Ngoài phạm vi | Đặt lịch/thu tiền/doanh thu thật (ở phần mềm spa) |

---

## 3. Kiến trúc tổng thể (3 tầng)

```
┌──────────────────────────────────────────────────────────────┐
│  TẦNG SẢN PHẨM (SaaS)                                          │
│  Onboarding · Billing/Subscription · Quản lý nhiều spa · Auth  │
├──────────────────────────────────────────────────────────────┤
│  TẦNG OS MARKETING                                             │
│  CEO Agent · Họp giao ban (orchestrator) · Bộ nhớ chung (DB)  │
│  · Job queue & scheduler · Guardrails · Approval gate         │
├──────────────────────────────────────────────────────────────┤
│  TẦNG NHÂN SỰ AI (10 agent)                                    │
│  Tình báo → Strategy → Content → Publisher → Ads → Optimizer  │
│  → Reply → Lead → (Sales follow-up) → Analytics               │
├──────────────────────────────────────────────────────────────┤
│  TẦNG TÍCH HỢP                                                 │
│  FB/IG Graph API · TikTok API · Zalo OA · Meta/TikTok Ads     │
│  · Zalo/Telegram Bot                                           │
└──────────────────────────────────────────────────────────────┘
```

### 3.1. Vòng lặp tự vận hành (heartbeat)

```
   08:00 mỗi ngày (cron, theo timezone từng tenant)
        │
   ┌────▼─────────────────────────────────────┐
   │ Mỗi agent nộp "báo cáo" vào bộ nhớ chung  │
   │ (Tình báo / Content / Ads / Lead ...)     │
   └────┬─────────────────────────────────────┘
        ▼
   CEO Agent đọc toàn bộ → ra QUYẾT ĐỊNH hôm nay
        ▼
   Gửi "Bản tin giao ban + Quyết định" qua Zalo/Telegram
        ▼
   [Cổng duyệt] chủ spa: Duyệt / Sửa / Nâng mục tiêu (timeout → tự chạy)
        ▼
   CEO giao việc (KPI/task) cho từng agent → các agent thực thi trong ngày
        ▼
   Optimizer chạy lại mỗi 3h (nhịp nhanh hơn)
```

---

## 4. Mô hình dữ liệu multi-tenant (phác thảo Prisma)

Mọi bảng nghiệp vụ đều mang `tenantId`. Áp dụng cô lập theo tenant ở tầng truy vấn (và cân nhắc Postgres Row-Level Security).

```prisma
model Tenant {            // 1 spa = 1 tenant
  id            String   @id @default(cuid())
  name          String
  timezone      String   @default("Asia/Ho_Chi_Minh")
  autonomyLevel AutonomyLevel @default(FULL_AUTO)
  plan          Plan     @default(BASIC)
  createdAt     DateTime @default(now())
  // quan hệ
  users         User[]
  channels      Channel[]
  services      Service[]
  goals         Goal[]
  // ... các bảng khác
}

enum AutonomyLevel { MANUAL SEMI_AUTO FULL_AUTO }
enum Plan { BASIC PRO ENTERPRISE }

model User {              // chủ spa / nhân viên
  id        String @id @default(cuid())
  tenantId  String
  email     String
  role      Role   @default(OWNER)
  // kênh nhận thông báo CEO
  zaloUserId     String?
  telegramChatId String?
}
enum Role { OWNER MANAGER STAFF }

model Channel {           // kết nối kênh của từng spa (OAuth)
  id           String   @id @default(cuid())
  tenantId     String
  type         ChannelType
  externalId   String   // page id / oa id / ad account id
  accessToken  String   // LƯU MÃ HÓA (xem mục Bảo mật)
  refreshToken String?
  expiresAt    DateTime?
  status       String   @default("active")
}
enum ChannelType { FACEBOOK_PAGE INSTAGRAM TIKTOK ZALO_OA META_ADS TIKTOK_ADS }

model Service {           // danh mục dịch vụ spa (triệt lông, trị mụn...)
  id        String @id @default(cuid())
  tenantId  String
  name      String
  category  String?
  priceFrom Int?
  active    Boolean @default(true)
}

model Goal {              // mục tiêu tháng do CEO Agent đặt / user duyệt
  id         String   @id @default(cuid())
  tenantId   String
  period     String   // "2026-07"
  serviceId  String?
  targetLeads    Int?
  targetCpaVnd   Int?
  targetRevenue  Int?   // tham chiếu, không phải doanh thu thật
  status     GoalStatus @default(PROPOSED)
}
enum GoalStatus { PROPOSED APPROVED ACTIVE DONE }

model IntelReport {       // báo cáo Phòng Tình Báo
  id        String   @id @default(cuid())
  tenantId  String
  date      DateTime @default(now())
  payload   Json     // đối thủ, trend, đề xuất
}

model Idea {              // Big Idea / Angle / Hook từ Strategy
  id        String @id @default(cuid())
  tenantId  String
  bigIdea   String
  angle     String?
  hook      String?
  serviceId String?
  status    String @default("draft")
}

model Content {           // bài viết do Content Agent sinh
  id         String   @id @default(cuid())
  tenantId   String
  ideaId     String?
  kind       ContentKind
  channel    ChannelType
  body       String
  mediaUrls  String[]
  status     ContentStatus @default(DRAFT)  // DRAFT→PENDING_APPROVAL→APPROVED→SCHEDULED→PUBLISHED→FAILED
  createdAt  DateTime @default(now())
}
enum ContentKind { EDUCATION CASE_STUDY FEEDBACK PROMOTION TREND }
enum ContentStatus { DRAFT PENDING_APPROVAL APPROVED SCHEDULED PUBLISHED FAILED }

model ScheduledPost {     // hàng đợi & lịch đăng
  id          String   @id @default(cuid())
  tenantId    String
  contentId   String
  channelId   String
  scheduledAt DateTime
  status      String   @default("pending") // pending/published/failed
  externalPostId String?
  error       String?
}

model AdCampaign {        // Media Buyer tạo
  id         String @id @default(cuid())
  tenantId   String
  platform   ChannelType  // META_ADS / TIKTOK_ADS
  serviceId  String?
  externalId String?
  dailyBudgetVnd Int
  status     String @default("draft")
}

model AdMetricSnapshot {  // Optimizer đọc mỗi 3h
  id         String   @id @default(cuid())
  tenantId   String
  campaignId String
  at         DateTime @default(now())
  ctr        Float?
  cpl        Int?
  cpm        Int?
  frequency  Float?
  roas       Float?
}

model Lead {              // Lead Collector gom
  id         String   @id @default(cuid())
  tenantId   String
  name       String?
  phone      String?
  need       String?      // "triệt lông", "trị mụn"...
  source     String?      // ad/post/kênh nào → để quy nguồn
  score      Int?
  status     LeadStatus @default(NEW)
  // doanh thu phản hồi TÙY CHỌN (để cải thiện tối ưu, không bắt buộc)
  closedRevenueVnd Int?
  handedOffAt DateTime?
  createdAt  DateTime @default(now())
}
enum LeadStatus { NEW CONTACTED QUALIFIED HANDED_OFF LOST }

model Conversation {      // hội thoại Social Care
  id        String @id @default(cuid())
  tenantId  String
  channel   ChannelType
  externalUserId String
  messages  Json     // lịch sử
  leadId    String?
}

model AgentRun {          // log mỗi lần agent chạy (quan sát + chi phí)
  id         String   @id @default(cuid())
  tenantId   String
  agent      String   // "ceo", "intel", "content"...
  model      String   // claude-... đã dùng
  inputTokens  Int @default(0)
  outputTokens Int @default(0)
  cacheReadTokens Int @default(0)
  costUsd    Float @default(0)
  startedAt  DateTime @default(now())
  finishedAt DateTime?
  status     String @default("ok")
}

model ApprovalRequest {   // cổng duyệt Full-auto qua Zalo/Telegram
  id         String   @id @default(cuid())
  tenantId   String
  kind       String   // "daily_decision" / "ad_spend" / "content"
  payload    Json
  decision   String?  // approve/edit/reject
  expiresAt  DateTime
  resolvedAt DateTime?
}
```

> Lưu ý: `Goal.targetRevenue` và `Lead.closedRevenueVnd` chỉ là **tham chiếu/tùy chọn** — nguồn sự thật doanh thu nằm ở phần mềm spa.

---

## 5. Đặc tả các Agent

Mỗi agent = một lời gọi Claude với **tool-use** (đọc/ghi DB qua các tool có kiểm soát), prompt hệ thống theo vai trò + brand voice tenant, và quyền hạn (tool) giới hạn theo chức năng. Model chọn theo nguyên tắc phân tầng (mục 7).

| # | Agent | Vai trò | Input (đọc) | Output (ghi) | Model | Nhịp |
|---|-------|---------|-------------|--------------|-------|------|
| 0 | **CEO Agent** | Đặt mục tiêu tháng, đọc báo cáo, ra quyết định ngày, giao KPI | tất cả báo cáo, Goal, metrics | Goal, task cho agent, ApprovalRequest | `claude-opus-4-8` | 8h sáng + khi cần |
| 1 | **Tình báo (Intel)** | Theo dõi đối thủ, trend, Ads Library | web (degrade gracefully) | IntelReport | `claude-sonnet-4-6` | hằng ngày |
| 2 | **Strategy** | Big Idea / Angle / Hook từ tình báo | IntelReport, Goal | Idea | `claude-opus-4-8` | hằng ngày |
| 3 | **Content** | Sinh bài đa kênh theo brand voice | Idea, Service | Content | `claude-sonnet-4-6` | theo lịch |
| 4 | **Publisher** | Lên lịch & đăng đa kênh | Content (APPROVED) | ScheduledPost, gọi API kênh | — (logic) | cron |
| 5 | **Media Buyer (Ads)** | Tạo campaign/adset/ads | Idea, Content, Goal | AdCampaign + gọi Ads API | `claude-sonnet-4-6` | theo quyết định CEO |
| 6 | **Optimizer** | Đọc metrics → tắt/tăng/nhân bản ads | AdMetricSnapshot | điều chỉnh AdCampaign (trong guardrail) | `claude-opus-4-8` | mỗi 3h |
| 7 | **Social Care (Reply)** | Trả lời inbox/comment | Conversation, RAG kiến thức spa | trả lời + cập nhật Conversation | `claude-haiku-4-5` | realtime (webhook) |
| 8 | **Lead Collector** | Phát hiện ý định, gom lead, chấm điểm | Conversation | Lead | `claude-haiku-4-5` | realtime |
| 9 | **Analytics** | Tổng hợp hiệu suất + insight cho dashboard & CEO | metrics, Lead, ScheduledPost | báo cáo (Json) | `claude-sonnet-4-6` | hằng ngày |

> "Sales follow-up" (nhắc lịch, chăm khách cũ) trong ngữ cảnh ranh-giới-tại-lead chủ yếu là **nhắc lead chưa bàn giao** + nhắn lại lead cũ chưa chuyển đổi; chăm sóc khách đã đến spa thuộc phần mềm spa.

### Tool-use cho agent (ví dụ)
- Tool đọc: `get_goals`, `get_recent_metrics`, `get_pending_leads`, `search_competitors`...
- Tool ghi (rủi ro cao → guardrail/duyệt): `publish_post`, `create_ad_campaign`, `increase_ad_budget`, `send_customer_message`.
- Triển khai qua **Anthropic SDK tool runner** (vòng lặp tự động) hoặc **manual agentic loop** khi cần chèn cổng phê duyệt human-in-the-loop trước hành động rủi ro.

---

## 6. Orchestrator & lập lịch

- **Orchestrator viết bằng code** trong Next.js (route handlers + module `lib/orchestrator`).
- **Scheduler:** cron (Vercel Cron hoặc worker `node-cron`/BullMQ). Mỗi tenant có job 8h sáng (theo timezone) và job Optimizer mỗi 3h.
- **Job queue:** hàng đợi (BullMQ/Redis) để chạy agent bất đồng bộ, retry, và giới hạn đồng thời (kiểm soát tải + chi phí).
- **Bộ nhớ chung = PostgreSQL.** Mọi agent đọc/ghi để quyết định nhất quán. Không có "trí nhớ" nào nằm ngoài DB (trừ cache prompt).
- **MCP:** chuẩn hóa tool cho agent; cho phép cắm thêm tool/tích hợp sau này.

> Phương án thay thế cần cân nhắc về sau: **Anthropic Managed Agents + Scheduled Deployments** (Anthropic chạy vòng lặp agent + cron). Phù hợp với bản chất 24/7, nhưng giai đoạn đầu ưu tiên **code-first** để kiểm soát guardrails & chi phí; có thể di trú một phần sang Managed Agents khi quy mô lớn.

---

## 7. Phân tầng model & kinh tế chi phí (sống còn cho SaaS)

Giá tham chiếu (mỗi 1M token, input/output):

| Model | ID | Input | Output | Dùng cho |
|---|---|---|---|---|
| Opus 4.8 | `claude-opus-4-8` | $5 | $25 | CEO, Strategy, Optimizer (quyết định khó) |
| Sonnet 4.6 | `claude-sonnet-4-6` | $3 | $15 | Content, Ads, Analytics, Intel (mặc định) |
| Haiku 4.5 | `claude-haiku-4-5` | $1 | $5 | Reply, Lead (khối lượng lớn, rẻ) |

**Kỹ thuật giảm chi phí:**
- **Prompt caching:** cache brand voice + danh mục dịch vụ + system prompt (phần ổn định đặt đầu prefix). Đọc cache ~0.1× giá input.
- **Batches API (giảm 50%):** dùng cho tác vụ không cần realtime (vd sinh hàng loạt content, tổng hợp Analytics đêm).
- **Adaptive thinking + effort hợp lý:** effort `high` cho CEO/Optimizer; thấp hơn cho tác vụ thường.
- **Trần chi phí AI/tenant/ngày:** ghi log `AgentRun.costUsd`, chặn khi vượt hạn mức theo gói.

**Gợi ý gói SaaS:** Basic (semi-auto, 1–2 kênh, hạn mức AI thấp) · Pro (full-auto, đa kênh + ads) · Enterprise (hạn mức cao, ưu tiên hỗ trợ). Gói = (mức tự trị) × (số kênh) × (hạn mức AI/ads).

---

## 8. Guardrails & an toàn vận hành

1. **Trần ngân sách ads/ngày** theo tenant + **kill-switch** (dừng toàn bộ ads ngay).
2. **Cổng phê duyệt (Full-auto):** Bản tin 8h sáng gửi Zalo/Telegram; hành động rủi ro cao (đăng nội dung nhạy cảm, tăng ngân sách vượt ngưỡng) yêu cầu xác nhận; **timeout → tự chạy** trong guardrails.
3. **Duyệt nội dung ngành làm đẹp:** bộ lọc từ ngữ/khẳng định y tế bị cấm; Content gắn cờ `PENDING_APPROVAL` khi chạm chủ đề nhạy cảm.
4. **Trần chi phí AI/tenant** (mục 7).
5. **Xử lý `stop_reason: "refusal"`** từ model; ghi log, không retry mù.

---

## 9. Tích hợp kênh (lưu ý khả thi)

| Kênh | API | Lưu ý |
|---|---|---|
| Facebook Page / Instagram | Graph API | Cần app review + quyền đăng; OAuth/token dài hạn |
| TikTok | Content Posting API + Ads API | Cần đăng ký app; một số dữ liệu đối thủ không có API |
| Zalo OA | Zalo OA Open API | CSKH + broadcast; quota tin nhắn |
| Meta Ads / TikTok Ads | Marketing API | Cần tài khoản quảng cáo + tiền + app review |
| Tình báo | Ads Library / Google Trends / TikTok | **Degrade gracefully**: phần lấy tự động được vs phần AI suy luận từ dữ liệu hạn chế |
| Thông báo | Zalo / Telegram Bot | 2 chiều: gửi bản tin + nhận lệnh Duyệt/Sửa |

> **Chế độ sandbox/mock**: trong khi chờ duyệt app, dựng connector theo chuẩn API thật + mock để cả vòng lặp chạy được mà không đốt tiền/không bị chặn.

---

## 10. Bảo mật

- **Cô lập tenant:** `tenantId` xuyên suốt + kiểm tra ở mọi truy vấn; cân nhắc Postgres RLS.
- **Token kênh mã hóa khi lưu** (vd AES-GCM với khóa từ KMS/secret manager); không bao giờ log token.
- **Phân quyền** theo `Role` (OWNER/MANAGER/STAFF).
- **Audit:** `AgentRun`, `ApprovalRequest` ghi lại mọi hành động tự trị.
- **Tuân thủ:** lưu ý dữ liệu khách hàng (lead) — chính sách giữ/xóa theo yêu cầu.

---

## 11. Lộ trình triển khai (phase)

- **Phase 0 — Nền tảng:** scaffold Next.js + Prisma + schema multi-tenant, auth, onboarding cơ bản, orchestrator + scheduler khung, `AgentRun`/guardrail khung.
- **Phase 1 — Lõi nội dung tự động:** CEO + Intel + Strategy + Content + Publisher (4 kênh, có mock) + dashboard duyệt + bản tin Zalo/Telegram. *(chạy được & có giá trị ngay)*
- **Phase 2 — Tương tác & lead:** Social Care (Reply) + Lead Collector + bàn giao lead (Zalo/Telegram/CSV) + CRM nhẹ.
- **Phase 3 — Ads loop:** Media Buyer + Optimizer + guardrails ngân sách.
- **Phase 4 — Đóng vòng:** Analytics/dashboard tổng thể, feedback doanh thu tùy chọn về Intel/CEO, bật Full-auto đầy đủ.

---

## 12. Rủi ro & câu hỏi mở

- **Duyệt app các nền tảng** (FB/IG/TikTok/Zalo/Ads) là rào cản hành chính lớn → cần bắt đầu sớm; dùng mock trong lúc chờ.
- **Tình báo đối thủ** phụ thuộc nguồn không chính thống (Trends/TikTok scrape) → rủi ro kỹ thuật/pháp lý; thiết kế degrade gracefully.
- **Chi phí LLM khi scale** nhiều tenant → bám sát phân tầng model + caching + batches + trần chi phí.
- **Quy nguồn doanh thu** chỉ ở mức marketing-attributed (lead/CPL/ROAS ước tính); doanh thu thật ở phần mềm spa.

---

*Tài liệu này là bản nháp để thống nhất trước khi code. Mọi mục có thể điều chỉnh theo phản hồi.*
