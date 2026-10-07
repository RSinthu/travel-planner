"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOut, Plane } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Button } from "@/components/ui";
import { forgetToken } from "@/lib/api";
import { authClient } from "@/lib/auth-client";

export function AppHeader({ userName, children }: { userName: string; children?: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  async function signOut() {
    await authClient.signOut();
    forgetToken();
    queryClient.clear(); // never show one user's trips to the next
    router.replace("/sign-in");
    router.refresh();
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface px-4">
      <Link href="/trips" className="flex items-center gap-2 font-semibold">
        <Plane className="size-5 text-accent" aria-hidden />
        <span className="hidden sm:inline">Travel planner</span>
      </Link>
      <div className="min-w-0 flex-1">{children}</div>
      <span className="hidden text-sm text-muted sm:inline">{userName}</span>
      <Button variant="ghost" onClick={signOut} aria-label="Sign out" title="Sign out">
        <LogOut className="size-4" aria-hidden />
      </Button>
    </header>
  );
}
