import { NextRequest, NextResponse } from "next/server";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ?? "http://localhost:8000";
const AI_SERVICE_API_KEY = process.env.AI_SERVICE_API_KEY ?? "";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const upstream = await fetch(`${AI_SERVICE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": AI_SERVICE_API_KEY,
      },
      body: JSON.stringify(body),
    });

    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { error: "AI service unreachable" },
      { status: 502 },
    );
  }
}
