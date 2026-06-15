import type { BusinessType } from "@prisma/client";

// Guardrail tuân thủ pháp lý quảng cáo làm đẹp VN (xem docs/AI-MOS-DESIGN.md mục 13).
// LƯU Ý: đây là rào kỹ thuật, KHÔNG thay thế tư vấn pháp lý.

// Từ/cụm bị cấm (thổi phồng, khẳng định chữa bệnh).
const FORBIDDEN_PATTERNS: { re: RegExp; reason: string }[] = [
  { re: /\b(cam kết|đảm bảo)\s*100\s*%/i, reason: "Khẳng định tuyệt đối 100%" },
  { re: /khỏi\s*(hẳn|hoàn toàn)/i, reason: "Khẳng định khỏi hẳn" },
  { re: /(điều trị|chữa)\s*dứt\s*điểm/i, reason: "Khẳng định điều trị dứt điểm" },
  { re: /không\s*tái\s*phát/i, reason: "Khẳng định không tái phát" },
  { re: /\bchữa\s*(khỏi|bệnh)\b/i, reason: "Quảng cáo như chữa bệnh" },
  { re: /\b(thay thế|tốt hơn)\s*thuốc\b/i, reason: "Quảng cáo như thuốc" },
  { re: /hiệu quả\s*(ngay\s*)?(lập tức|tức thì)\s*100/i, reason: "Hiệu quả tức thì tuyệt đối" },
];

// Với cơ sở không xâm lấn: không được dùng ngôn ngữ y khoa/điều trị.
const MEDICAL_CLAIM_PATTERNS: { re: RegExp; reason: string }[] = [
  { re: /\b(điều trị|phác đồ|bác sĩ|y khoa|đặc trị)\b/i, reason: "Ngôn ngữ y tế ở cơ sở không xâm lấn" },
];

export interface ComplianceResult {
  ok: boolean;
  flags: string[];
  /** true nếu cần người duyệt trước khi đăng (PENDING_APPROVAL) */
  needsHumanReview: boolean;
}

export function checkContent(
  body: string,
  opts: { businessType: BusinessType; isCosmetic?: boolean },
): ComplianceResult {
  const flags: string[] = [];

  for (const p of FORBIDDEN_PATTERNS) {
    if (p.re.test(body)) flags.push(`forbidden:${p.reason}`);
  }

  if (opts.businessType === "SPA_NON_INVASIVE") {
    for (const p of MEDICAL_CLAIM_PATTERNS) {
      if (p.re.test(body)) flags.push(`medical_claim:${p.reason}`);
    }
  }

  // Mỹ phẩm phải có thông tin bắt buộc (đơn giản hoá: kiểm tra có nêu công dụng + đơn vị chịu trách nhiệm).
  if (opts.isCosmetic) {
    const hasResponsible = /(công bố|chịu trách nhiệm|phân phối bởi|sản xuất bởi)/i.test(body);
    if (!hasResponsible) flags.push("cosmetic_missing:Thiếu thông tin đơn vị chịu trách nhiệm");
  }

  // Cơ sở y tế: mọi content đều cần duyệt (cần xác nhận nội dung quảng cáo).
  const medicalBusiness =
    opts.businessType === "AESTHETIC_MEDICAL" || opts.businessType === "CLINIC";

  const hasForbidden = flags.some((f) => f.startsWith("forbidden:"));
  const needsHumanReview = hasForbidden || flags.length > 0 || medicalBusiness;

  return { ok: !hasForbidden, flags, needsHumanReview };
}

/** Hướng dẫn tuân thủ chèn vào system prompt của Content/Ads Agent. */
export function complianceInstructions(businessType: BusinessType): string {
  const base = [
    "QUY TẮC TUÂN THỦ (luật quảng cáo làm đẹp VN):",
    "- TUYỆT ĐỐI không thổi phồng: không dùng 'cam kết 100%', 'khỏi hẳn', 'điều trị dứt điểm', 'không tái phát'.",
    "- Không quảng cáo mỹ phẩm/dịch vụ như thuốc hay có tác dụng chữa bệnh.",
    "- Không bịa lời chứng thực cá nhân ('tôi đã dùng và khỏi').",
    "- Không dùng ảnh before/after gây hiểu nhầm; không mạo danh bác sĩ/cơ sở y tế.",
  ];
  if (businessType === "SPA_NON_INVASIVE") {
    base.push(
      "- Đây là spa KHÔNG xâm lấn: không dùng ngôn ngữ y khoa ('điều trị', 'phác đồ', 'bác sĩ', 'đặc trị').",
    );
  } else {
    base.push(
      "- Đây là cơ sở có yếu tố y tế: nội dung cần được người phụ trách duyệt và phải có xác nhận nội dung quảng cáo trước khi đăng.",
    );
  }
  return base.join("\n");
}
