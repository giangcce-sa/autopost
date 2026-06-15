import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    ok: true,
    service: "autopost-ai-mos",
    connectorMode: process.env.CONNECTOR_MODE ?? "mock",
    ts: new Date().toISOString(),
  });
}
