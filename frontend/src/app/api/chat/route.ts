import { NextResponse } from "next/server";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ?? "http://localhost:8000";

export async function POST() {
  try {
    const upstream = await fetch(`${AI_SERVICE_URL}/health`);
    const backend = await upstream.json();

    return NextResponse.json({ gateway: "ok", backend });
  } catch {
    return NextResponse.json(
      { gateway: "error", message: "AI service unreachable" },
      { status: 502 },
    );
  }
}
