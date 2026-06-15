import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const tenant = await prisma.tenant.create({
    data: {
      name: "Spa Demo Hà Nội",
      businessType: "SPA_NON_INVASIVE",
      autonomyLevel: "FULL_AUTO",
      plan: "PRO",
      brandVoice: "Thân thiện, gần gũi, tập trung vào sự tự tin của khách hàng nữ 18-35.",
      aiBudgetUsdDaily: 5,
      users: {
        create: {
          email: "owner@spademo.vn",
          name: "Chủ spa",
          role: "OWNER",
          telegramChatId: process.env.TELEGRAM_CHAT_ID ?? null,
        },
      },
      services: {
        create: [
          { name: "Triệt lông nách", category: "triệt lông", priceFrom: 499000 },
          { name: "Triệt lông bikini", category: "triệt lông", priceFrom: 1290000 },
          { name: "Chăm sóc da mụn", category: "chăm sóc da", priceFrom: 350000 },
        ],
      },
      channels: {
        create: [
          { type: "FACEBOOK_PAGE", externalId: "demo_fb_page", accessToken: "mock-token-fb" },
          { type: "ZALO_OA", externalId: "demo_zalo_oa", accessToken: "mock-token-zalo" },
          { type: "TIKTOK", externalId: "demo_tiktok", accessToken: "mock-token-tiktok" },
        ],
      },
    },
  });

  // Một campaign + metrics mẫu để Optimizer có dữ liệu chạy thử.
  const camp = await prisma.adCampaign.create({
    data: {
      tenantId: tenant.id,
      platform: "META_ADS",
      objective: "LEADS",
      dailyBudgetVnd: 200000,
      status: "active",
    },
  });
  await prisma.adMetricSnapshot.create({
    data: {
      tenantId: tenant.id,
      campaignId: camp.id,
      spendVnd: 200000,
      ctr: 1.8,
      cpl: 95000,
      cpm: 45000,
      frequency: 1.4,
      roas: 2.3,
      leads: 2,
    },
  });

  console.log(`Seed xong. Tenant: ${tenant.id} (${tenant.name})`);
}

main()
  .then(() => prisma.$disconnect())
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });
