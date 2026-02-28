import { NextRequest, NextResponse } from "next/server";
import { StreamClient } from "@stream-io/node-sdk";

const API_KEY = process.env.NEXT_PUBLIC_STREAM_API_KEY!;
const API_SECRET = process.env.STREAM_API_SECRET;

export async function GET(req: NextRequest) {
  if (!API_SECRET) {
    return NextResponse.json(
      { error: "STREAM_API_SECRET is not set" },
      { status: 500 }
    );
  }

  const userId =
    req.nextUrl.searchParams.get("user_id") ??
    process.env.NEXT_PUBLIC_STREAM_USER_ID ??
    "demo-user";

  const client = new StreamClient(API_KEY, API_SECRET);
  const token = client.generateUserToken({
    user_id: userId,
    validity_in_seconds: 3600, // 1 hour; SDK auto-includes iss, sub, iat, exp
  });

  return NextResponse.json({ token, userId });
}
