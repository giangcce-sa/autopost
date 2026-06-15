import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

// Mã hóa token kênh bằng AES-256-GCM. Khóa lấy từ CHANNEL_TOKEN_SECRET (hex 64 ký tự).
// Định dạng lưu: base64(iv).base64(tag).base64(ciphertext)

function getKey(): Buffer {
  const hex = process.env.CHANNEL_TOKEN_SECRET ?? "";
  if (hex.length !== 64) {
    throw new Error(
      "CHANNEL_TOKEN_SECRET phải là 32 bytes hex (64 ký tự). Sinh: openssl rand -hex 32",
    );
  }
  return Buffer.from(hex, "hex");
}

export function encryptToken(plain: string): string {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", getKey(), iv);
  const enc = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [iv.toString("base64"), tag.toString("base64"), enc.toString("base64")].join(".");
}

export function decryptToken(stored: string): string {
  const [ivB64, tagB64, dataB64] = stored.split(".");
  if (!ivB64 || !tagB64 || !dataB64) throw new Error("Token lưu trữ không hợp lệ");
  const decipher = createDecipheriv("aes-256-gcm", getKey(), Buffer.from(ivB64, "base64"));
  decipher.setAuthTag(Buffer.from(tagB64, "base64"));
  return Buffer.concat([
    decipher.update(Buffer.from(dataB64, "base64")),
    decipher.final(),
  ]).toString("utf8");
}
