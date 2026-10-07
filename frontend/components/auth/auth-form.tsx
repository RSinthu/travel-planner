"use client";

import { Plane } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Banner, Button, Card, Input } from "@/components/ui";
import { forgetToken } from "@/lib/api";
import { authClient } from "@/lib/auth-client";

const MIN_PASSWORD = 8;

export function AuthForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signingUp = mode === "sign-up";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (signingUp && !name.trim()) return setError("Enter your name.");
    if (!email.includes("@")) return setError("Enter a valid email address.");
    if (password.length < MIN_PASSWORD) return setError(`Passwords have at least ${MIN_PASSWORD} characters.`);

    setBusy(true);
    const result = signingUp
      ? await authClient.signUp.email({ name: name.trim(), email: email.trim(), password })
      : await authClient.signIn.email({ email: email.trim(), password });
    setBusy(false);

    if (result.error) {
      setError(
        result.error.status === 401 || result.error.code === "INVALID_EMAIL_OR_PASSWORD"
          ? "That email and password don't match."
          : result.error.message ?? "Something went wrong. Try again.",
      );
      return;
    }
    forgetToken();
    router.replace("/trips");
    router.refresh();
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm p-6">
        <div className="mb-6 flex items-center gap-2">
          <Plane className="size-5 text-accent" aria-hidden />
          <span className="font-semibold">Travel planner</span>
        </div>
        <h1 className="mb-1 text-xl font-semibold">{signingUp ? "Create your account" : "Sign in"}</h1>
        <p className="mb-6 text-sm text-muted">
          {signingUp ? "Plan trips with weather, hotels and a day-by-day itinerary." : "Welcome back."}
        </p>

        <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
          {signingUp && (
            <label className="flex flex-col gap-1 text-sm">
              Name
              <Input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="Alex Doe" />
            </label>
          )}
          <label className="flex flex-col gap-1 text-sm">
            Email
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="alex@example.com"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Password
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={signingUp ? "new-password" : "current-password"}
              placeholder={signingUp ? `At least ${MIN_PASSWORD} characters` : ""}
            />
          </label>
          {error && <Banner tone="danger">{error}</Banner>}
          <Button type="submit" variant="primary" disabled={busy} className="mt-2 h-10">
            {busy ? "Please wait…" : signingUp ? "Create account" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          {signingUp ? "Already have an account? " : "New here? "}
          <Link href={signingUp ? "/sign-in" : "/sign-up"} className="font-medium text-accent hover:underline">
            {signingUp ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </Card>
    </main>
  );
}
