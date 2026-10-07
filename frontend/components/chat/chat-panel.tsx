"use client";

import { ArrowUp, Check, CircleAlert, Loader2, RotateCcw, Square } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Banner, Button } from "@/components/ui";
import type { Step } from "@/hooks/use-trip-stream";
import { ApiError } from "@/lib/api";
import { errorText } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

const EXAMPLES = [
  "4 days in Rome from next Friday, 2 adults, hotel under €200 a night, total budget €1,200. We love history and museums.",
  "A long weekend in Lisbon next month for 2, viewpoints and food, budget €900.",
  "3 days in Paris for 1 person, mid-range hotel, art museums.",
];
const MAX_CHARS = 2000;
const FAILED: Record<Step["step"], string> = {
  weather_agent: "Couldn't get the weather",
  hotel_agent: "Couldn't search hotels",
  places_agent: "Couldn't find things to do",
  plan_itinerary: "Couldn't build the day-by-day plan",
};

type Props = {
  messages: ChatMessage[];
  sending: boolean;
  steps: Step[];
  error: ApiError | null;
  onSend: (text: string) => void;
  onStop: () => void;
  onDismissError: () => void;
};

export function ChatPanel({ messages, sending, steps, error, onSend, onStop, onDismissError }: Props) {
  const [draft, setDraft] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, steps.length, sending]);

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!draft.trim() || sending) return;
    onSend(draft);
    setDraft("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) submit(event);
  }

  const lastIndex = messages.length - 1;

  return (
    <section aria-label="Chat" className="flex h-full min-h-0 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && !sending && (
          <div className="py-6">
            <h2 className="mb-1 font-semibold">Where are you going?</h2>
            <p className="mb-4 text-sm text-muted">
              Say where, when, who&apos;s travelling and your budget. Try one of these:
            </p>
            <div className="flex flex-col gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  onClick={() => onSend(example)}
                  className="rounded-lg border border-line bg-surface p-3 text-left text-sm hover:border-accent/50 hover:bg-surface-muted"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) =>
          message.role === "user" ? (
            <div key={index} className="flex flex-col items-end gap-1">
              <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-accent-soft px-3 py-2 text-sm text-accent">
                {message.text}
              </div>
              {message.answered === false && !(sending && index === lastIndex) && (
                <button
                  onClick={() => onSend(message.text)}
                  disabled={sending}
                  className="flex items-center gap-1 text-xs text-muted hover:text-foreground disabled:opacity-50"
                >
                  <RotateCcw className="size-3" aria-hidden /> No reply. Retry
                </button>
              )}
            </div>
          ) : (
            <div key={index} className="prose-reply max-w-full text-sm leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
            </div>
          ),
        )}

        {sending && <Progress steps={steps} />}

        {error && (
          <Banner
            tone={error.code === "ai_unavailable" || error.code === "rate_limited" ? "warn" : "danger"}
            action={
              <button onClick={onDismissError} className="text-xs underline">
                Dismiss
              </button>
            }
          >
            {errorText(error)}
          </Banner>
        )}
        <div ref={bottom} />
      </div>

      <form onSubmit={submit} className="border-t border-line bg-surface p-3">
        <div className="flex items-end gap-2">
          <label htmlFor="chat-input" className="sr-only">
            Message
          </label>
          <textarea
            id="chat-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value.slice(0, MAX_CHARS))}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="Find cheaper hotels, add a museum day…"
            className="max-h-40 min-h-10 flex-1 resize-none rounded-lg border border-line bg-surface px-3 py-2 text-sm
              placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          {sending ? (
            <Button type="button" onClick={onStop} aria-label="Stop" title="Stop">
              <Square className="size-4" aria-hidden />
            </Button>
          ) : (
            <Button type="submit" variant="primary" disabled={!draft.trim()} aria-label="Send" title="Send">
              <ArrowUp className="size-4" aria-hidden />
            </Button>
          )}
        </div>
      </form>
    </section>
  );
}

function Progress({ steps }: { steps: Step[] }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-3 text-sm" aria-live="polite">
      {steps.length === 0 && (
        <div className="flex items-center gap-2 text-muted">
          <Loader2 className="size-4 animate-spin" aria-hidden /> Thinking…
        </div>
      )}
      <ul className="space-y-1">
        {steps.map((step) => (
          <li
            key={step.step}
            className={`flex items-center gap-2 ${
              step.status === "started" ? "text-muted" : step.ok === false ? "text-warn" : "text-ok"
            }`}
          >
            {step.status === "started" ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : step.ok === false ? (
              <CircleAlert className="size-4" aria-hidden />
            ) : (
              <Check className="size-4" aria-hidden />
            )}
            {step.status === "started" ? `${step.message}…` : step.ok === false ? FAILED[step.step] : step.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
