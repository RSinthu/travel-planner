"use client";

import { useState } from "react";

import { Banner } from "@/components/ui";
import { day, money } from "@/lib/format";
import type { TripData } from "@/lib/types";

import { BudgetView } from "./budget-view";
import { HotelsView } from "./hotels-view";
import { MapView } from "./map-view";
import { PlanView } from "./plan-view";

const TABS = ["Plan", "Map", "Hotels", "Budget"] as const;
type Tab = (typeof TABS)[number];

export function TripBoard({ tripId, trip, busy }: { tripId: string; trip: TripData; busy: boolean }) {
  const [tab, setTab] = useState<Tab>("Plan");
  const request = trip.trip_request;
  const review = trip.itinerary_review;
  const cost = review?.cost;
  const currency = cost?.currency ?? request?.currency ?? "USD";
  const hotelPerNight = trip.itinerary?.hotel_details?.price_per_night;
  const usesGeoapify = Boolean(trip.attractions?.attractions?.length || trip.hotels_nearby?.hotels?.length);

  return (
    <section aria-label="Trip board" className="flex h-full min-h-0 flex-col">
      <div className="space-y-3 border-b border-line p-4">
        <div>
          <h2 className="font-semibold">{trip.itinerary?.title ?? (request ? `Trip to ${request.city}` : "Your trip")}</h2>
          {request && (
            <p className="text-sm text-muted">
              {day(request.start_date)} – {day(request.end_date)} · {request.adults} adult{request.adults === 1 ? "" : "s"}
              {request.total_budget ? ` · budget ${money(request.total_budget, currency)}` : ""}
            </p>
          )}
        </div>
        {cost && (
          <div className="grid grid-cols-3 gap-2">
            <Metric label="Estimated total" value={money(cost.estimated_total, currency)} />
            {cost.budget != null ? (
              <Metric
                label={cost.within_budget ? "Left in budget" : "Over budget"}
                value={money(Math.abs(cost.remaining ?? 0), currency)}
                tone={cost.within_budget ? "ok" : "danger"}
              />
            ) : (
              <Metric label="Per person" value={money(cost.per_person, currency)} />
            )}
            <Metric label="Hotel per night" value={hotelPerNight != null ? money(hotelPerNight, currency) : "–"} />
          </div>
        )}
        <div role="tablist" aria-label="Trip views" className="flex gap-4 text-sm">
          {TABS.map((name) => (
            <button
              key={name}
              role="tab"
              aria-selected={tab === name}
              onClick={() => setTab(name)}
              className={`border-b-2 pb-1 ${tab === name ? "border-foreground font-medium" : "border-transparent text-muted hover:text-foreground"}`}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {review?.errors.map((problem) => (
          <Banner key={problem} tone="danger">{problem}</Banner>
        ))}
        {tab === "Plan" && review?.warnings.map((warning) => (
          <Banner key={warning} tone="warn">{warning}</Banner>
        ))}

        {tab === "Plan" && <PlanView trip={trip} />}
        {tab === "Map" && <MapView trip={trip} />}
        {tab === "Hotels" && <HotelsView tripId={tripId} trip={trip} busy={busy} />}
        {tab === "Budget" && <BudgetView cost={cost} />}

        {usesGeoapify && <p className="pt-2 text-xs text-muted">Place data: Powered by Geoapify</p>}
      </div>
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "ok" | "danger" }) {
  return (
    <div className="rounded-lg bg-surface-muted px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className={`font-semibold ${tone === "ok" ? "text-ok" : tone === "danger" ? "text-danger" : ""}`}>{value}</div>
    </div>
  );
}
