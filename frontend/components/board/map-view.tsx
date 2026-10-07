"use client";

import dynamic from "next/dynamic";

import type { TripData } from "@/lib/types";

const TripMap = dynamic(() => import("./trip-map"), {
  ssr: false,
  loading: () => <div className="flex h-full items-center justify-center text-sm text-muted">Loading map…</div>,
});

export function MapView({ trip }: { trip: TripData }) {
  return (
    <div className="h-[28rem] overflow-hidden rounded-xl border border-line lg:h-[calc(100dvh-15rem)]">
      <TripMap trip={trip} />
    </div>
  );
}
