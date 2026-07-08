import { NextResponse } from "next/server";

const COOKIE_NAME = "showei_session";

async function authToken() {
  const password = process.env.APP_PASSWORD || "Showei2429";
  const data = new TextEncoder().encode(`showei-sales:${password}`);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { password?: string };
  const password = process.env.APP_PASSWORD || "Showei2429";

  if (body.password !== password) {
    return NextResponse.json({ ok: false, message: "パスワードが違います。" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, await authToken(), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 12,
    path: "/",
  });
  return response;
}
