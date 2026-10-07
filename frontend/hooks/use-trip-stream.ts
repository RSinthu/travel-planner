"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, streamMessage } from "@/lib/api";
import type { ChatMessage, StepName, StreamEvent, TripDetail } from "@/lib/types";

import { tripKeys } from "./use-trips";

export type Step = { step: StepName; message: string; status: "started" | "done"; ok?: boolean };

/**
 * Sends a message and applies the streamed events to the cached trip as they
 * arrive: the reply goes into the chat, changed trip data onto the board.
 */
export function useTripStream(tripId: string) {
  const queryClient = useQueryClient();
  const [sending, setSending] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []); // leaving the page stops the turn

  const update = useCallback(
    (change: (trip: TripDetail) => TripDetail) =>
      queryClient.setQueryData<TripDetail>(tripKeys.detail(tripId), (old) => (old ? change(old) : old)),
    [queryClient, tripId],
  );

  const handle = useCallback(
    (event: StreamEvent) => {
      switch (event.type) {
        case "progress":
          setSteps((current) => {
            const others = current.filter((s) => s.step !== event.step);
            return [...others, { step: event.step, message: event.message, status: event.status, ok: event.ok }];
          });
          break;
        case "message":
          update((trip) => {
            const messages = trip.messages.map((m, i) =>
              i === trip.messages.length - 1 && m.role === "user" ? { ...m, answered: true } : m,
            );
            const reply: ChatMessage = { role: "assistant", text: event.text, at: Date.now() / 1000 };
            return { ...trip, messages: [...messages, reply] };
          });
          break;
        case "trip":
          update((trip) => ({ ...trip, trip: { ...trip.trip, ...event.data } }));
          break;
        case "error":
          setError(new ApiError(0, event.code, event.message));
          break;
      }
    },
    [update],
  );

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || sending) return;
      setError(null);
      setSteps([]);
      setSending(true);
      update((trip) => ({
        ...trip,
        messages: [...trip.messages, { role: "user", text: message, at: Date.now() / 1000, answered: null }],
      }));

      const abort = new AbortController();
      controller.current = abort;
      try {
        await streamMessage(tripId, message, handle, abort.signal);
      } catch (caught) {
        if ((caught as Error).name !== "AbortError") {
          setError(caught instanceof ApiError ? caught : new ApiError(0, "internal_error", "Something went wrong."));
        }
      } finally {
        controller.current = null;
        setSending(false);
        // Pick up the saved history (answered flags) and the new trip title.
        queryClient.invalidateQueries({ queryKey: tripKeys.detail(tripId) });
        queryClient.invalidateQueries({ queryKey: tripKeys.all, exact: true });
      }
    },
    [handle, queryClient, sending, tripId, update],
  );

  const stop = useCallback(() => controller.current?.abort(), []);

  return { send, stop, sending, steps, error, clearError: () => setError(null) };
}
