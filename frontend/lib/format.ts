import { ApiError } from "./api";

export function money(amount: number | null | undefined, currency = "USD"): string {
  if (amount == null) return "–";
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

export function day(date: string): string {
  const parsed = new Date(`${date}T12:00:00`);
  return Number.isNaN(parsed.getTime())
    ? date
    : parsed.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

export function timeAgo(unixSeconds: number): string {
  const minutes = Math.round((Date.now() / 1000 - unixSeconds) / 60);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return new Date(unixSeconds * 1000).toLocaleDateString();
}

/** What to tell the user for an API or stream error code. */
export function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return "Something went wrong. Try again.";
  switch (error.code) {
    case "ai_unavailable":
      return "The AI service is busy right now. Try again in a minute.";
    case "ai_quota_exceeded":
      return "The AI service's daily limit has been reached. Try again later.";
    case "rate_limited":
      return error.retryAfter
        ? `You're sending messages quickly. Try again in ${error.retryAfter} seconds.`
        : "You're sending messages quickly. Wait a moment.";
    case "trip_busy":
      return "This trip is still answering the previous message.";
    case "not_authenticated":
    case "invalid_token":
    case "token_expired":
      return "Your session has ended. Sign in again.";
    default:
      return error.message || "Something went wrong. Try again.";
  }
}
