// Thông báo CEO + cổng phê duyệt qua Zalo/Telegram (2 chiều).
// Mặc định: mock console. Nếu có TELEGRAM_BOT_TOKEN → gửi Telegram thật.

export interface Notifier {
  send(chatId: string | null | undefined, text: string): Promise<void>;
}

class ConsoleNotifier implements Notifier {
  async send(chatId: string | null | undefined, text: string): Promise<void> {
    console.log(`[notify→${chatId ?? "console"}]\n${text}\n`);
  }
}

class TelegramNotifier implements Notifier {
  constructor(private token: string) {}
  async send(chatId: string | null | undefined, text: string): Promise<void> {
    if (!chatId) {
      console.log(`[notify:telegram] (no chatId) ${text.slice(0, 80)}...`);
      return;
    }
    const res = await fetch(`https://api.telegram.org/bot${this.token}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    if (!res.ok) console.error(`[notify:telegram] lỗi ${res.status}: ${await res.text()}`);
  }
}

export function getNotifier(): Notifier {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  return token ? new TelegramNotifier(token) : new ConsoleNotifier();
}
