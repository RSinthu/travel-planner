"use client";

// Client for the FastAPI backend. Every call carries a short-lived Better Auth
// JWT (cached until a minute before it expires). The messages endpoint streams
// Server-Sent Events, read with fetch because EventSource can't POST or send headers.

import { EventSourceParserStream } from "eventsource-parser/stream";

import { authClient } from "./auth-client";
import type { Itinerary, Review, StreamEvent, TripDetail, TripSummary } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public retryAfter?: number,
  ) {
    super(message);
  }
}

let cachedToken: { value: string; expiresAt: number } | null = null;

function tokenExpiry(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp : 0;
  } catch {
    return 0;
  }
}

export function forgetToken() {
  cachedToken = null;
}

async function getToken(): Promise<string> {
  const now = Date.now() / 1000;
  if (cachedToken && cachedToken.expiresAt - now > 60) return cachedToken.value;
  const { data, error } = await authClient.token();
  if (error || !data?.token) {
    throw new ApiError(401, "not_authenticated", "Your session has ended. Sign in again.");
  }
  cachedToken = { value: data.token, expiresAt: tokenExpiry(data.token) };
  return data.token;
}

async function toApiError(response: Response): Promise<ApiError> {
  const retryAfter = Number(response.headers.get("Retry-After")) || undefined;
  try {
    const body = await response.json();
    return new ApiError(response.status, body.error.code, body.error.message, retryAfter);
  } catch {
    return new ApiError(response.status, "http_error", `The server answered ${response.status}.`, retryAfter);
  }
}

async function call(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getToken();
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "network", "Can't reach the travel planner. Check your connection and try again.");
  }
  if (response.status === 401) forgetToken();
  if (!response.ok) throw await toApiError(response);
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await call(path, init);
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const api = {
  listTrips: () => json<TripSummary[]>("/api/trips"),
  createTrip: () => json<TripSummary>("/api/trips", { method: "POST" }),
  getTrip: (id: string) => json<TripDetail>(`/api/trips/${encodeURIComponent(id)}`),
  deleteTrip: (id: string) => json<void>(`/api/trips/${encodeURIComponent(id)}`, { method: "DELETE" }),
  chooseHotel: (id: string, hotel: string) =>
    json<{ itinerary: Itinerary; itinerary_review: Review }>(`/api/trips/${encodeURIComponent(id)}/itinerary`, {
      method: "PATCH",
      body: JSON.stringify({ hotel }),
    }),
};

/** Send a message and call onEvent for each streamed event. Resolves when the stream ends. */
export async function streamMessage(
  tripId: string,
  text: string,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await call(`/api/trips/${encodeURIComponent(tripId)}/messages`, {
    method: "POST",
    body: JSON.stringify({ text }),
    signal,
  });
  if (!response.body) throw new ApiError(0, "network", "The reply stream could not be opened.");

  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .pipeThrough(new EventSourceParserStream())
    .getReader();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value.event) continue; // keep-alive comments have no event name
      const data = JSON.parse(value.data);
      onEvent(value.event === "trip" ? { type: "trip", data } : ({ type: value.event, ...data } as StreamEvent));
    }
  } finally {
    reader.releaseLock();
  }
}
