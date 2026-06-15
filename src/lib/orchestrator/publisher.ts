import { prisma } from "../prisma";
import { channelToken } from "../tenant";
import { getChannelConnector } from "../connectors/channel";
import { ensureMockChannelConnectors } from "../connectors/mock-channel";

// Publisher: quét ScheduledPost đến hạn và đăng qua connector kênh.
export async function runPublisher(): Promise<{ published: number; failed: number }> {
  if (process.env.CONNECTOR_MODE !== "live") ensureMockChannelConnectors();

  const due = await prisma.scheduledPost.findMany({
    where: { status: "pending", scheduledAt: { lte: new Date() } },
    include: { content: true },
    take: 50,
  });

  let published = 0;
  let failed = 0;
  for (const post of due) {
    try {
      const channel = await prisma.channel.findUnique({ where: { id: post.channelId } });
      if (!channel) throw new Error("Kênh không tồn tại");
      const connector = getChannelConnector(channel.type);
      const result = await connector.publish({
        channelType: channel.type,
        externalId: channel.externalId,
        accessToken: channelToken(channel),
        body: post.content.body,
        mediaUrls: post.content.mediaUrls,
      });
      await prisma.scheduledPost.update({
        where: { id: post.id },
        data: { status: "published", externalPostId: result.externalPostId },
      });
      await prisma.content.update({ where: { id: post.contentId }, data: { status: "PUBLISHED" } });
      published++;
    } catch (err) {
      await prisma.scheduledPost.update({
        where: { id: post.id },
        data: { status: "failed", error: err instanceof Error ? err.message : String(err) },
      });
      failed++;
    }
  }
  return { published, failed };
}
