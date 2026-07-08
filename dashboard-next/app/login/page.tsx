"use client";

import { FormEvent, useState } from "react";
import { LockKeyhole, Truck } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!response.ok) {
        setError("パスワードが違います。");
        return;
      }
      const params = new URLSearchParams(window.location.search);
      window.location.href = params.get("next") || "/";
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <section className="w-full max-w-md rounded-lg border border-border bg-card/70 p-6 shadow-glow">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-md bg-primary/16 text-primary ring-1 ring-primary/25">
            <Truck className="size-5" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">翔栄 営業管理</h1>
            <p className="mt-1 text-sm text-muted-foreground">管理画面に入るにはパスワードを入力してください。</p>
          </div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">アクセスパスワード</span>
            <div className="flex items-center gap-2 rounded-md border border-border bg-background px-3">
              <LockKeyhole className="size-4 text-muted-foreground" />
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoFocus
                className="h-10 min-w-0 flex-1 bg-transparent text-sm outline-none"
              />
            </div>
          </label>
          {error ? <div className="rounded-md border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</div> : null}
          <Button className="w-full" disabled={loading || !password}>
            {loading ? "確認中..." : "ログイン"}
          </Button>
        </form>
      </section>
    </main>
  );
}
