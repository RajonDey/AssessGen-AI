"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Nav } from "@/components/nav";
import { ApiError, fetchMe } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    fetchMe()
      .then((user) => setEmail(user.email))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load session");
      });
  }, [router]);

  if (!email) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 text-sm text-zinc-600">
        {error ?? "Loading…"}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <Nav email={email} />
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
