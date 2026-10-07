"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AppHeader } from "@/components/app-header";
import { TripBoard } from "@/components/board/trip-board";
import { ChatPanel } from "@/components/chat/chat-panel";
import { Banner } from "@/components/ui";
import { useTripStream } from "@/hooks/use-trip-stream";
import { useTrip } from "@/hooks/use-trips";
import { errorText } from "@/lib/format";

export function TripWorkspace({ tripId, userName }: { tripId: string; userName: string }) {
  const trip = useTrip(tripId);
  const stream = useTripStream(tripId);
  const [mobileView, setMobileView] = useState<"chat" | "plan">("chat");

  const header = (
    <AppHeader userName={userName}>
      <div className="flex min-w-0 items-center gap-2">
        <Link href="/trips" className="text-muted hover:text-foreground" aria-label="All trips" title="All trips">
          <ArrowLeft className="size-4" aria-hidden />
        </Link>
        <span className="truncate text-sm font-medium">{trip.data?.title ?? "Trip"}</span>
      </div>
    </AppHeader>
  );

  if (trip.isPending) {
    return (
      <>
        {header}
        <p className="p-6 text-sm text-muted">Loading your trip…</p>
      </>
    );
  }
  if (trip.error || !trip.data) {
    return (
      <>
        {header}
        <div className="mx-auto w-full max-w-xl p-6">
          <Banner tone="danger" action={<Link href="/trips" className="text-xs underline">Back to trips</Link>}>
            {errorText(trip.error)}
          </Banner>
        </div>
      </>
    );
  }

  const busy = stream.sending || trip.data.busy;

  return (
    <div className="flex h-dvh flex-col">
      {header}

      <div role="tablist" aria-label="View" className="flex border-b border-line bg-surface lg:hidden">
        {(["chat", "plan"] as const).map((view) => (
          <button
            key={view}
            role="tab"
            aria-selected={mobileView === view}
            onClick={() => setMobileView(view)}
            className={`flex-1 py-2 text-sm ${mobileView === view ? "border-b-2 border-foreground font-medium" : "text-muted"}`}
          >
            {view === "chat" ? "Chat" : "Plan"}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(22rem,2fr)_3fr]">
        <div className={`min-h-0 border-line lg:block lg:border-r ${mobileView === "chat" ? "block" : "hidden"}`}>
          <ChatPanel
            messages={trip.data.messages}
            sending={stream.sending}
            steps={stream.steps}
            error={stream.error}
            onSend={stream.send}
            onStop={stream.stop}
            onDismissError={stream.clearError}
          />
        </div>
        <div className={`min-h-0 bg-background lg:block ${mobileView === "plan" ? "block" : "hidden"}`}>
          <TripBoard tripId={tripId} trip={trip.data.trip} busy={busy} />
        </div>
      </div>
    </div>
  );
}
