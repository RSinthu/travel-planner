"use client";

import { BedDouble, Star } from "lucide-react";

import { Badge, Banner, Button, Card } from "@/components/ui";
import { useChooseHotel } from "@/hooks/use-trips";
import { errorText, money } from "@/lib/format";
import type { TripData } from "@/lib/types";

export function HotelsView({ tripId, trip, busy }: { tripId: string; trip: TripData; busy: boolean }) {
  const choose = useChooseHotel(tripId);
  const hotels = trip.hotels?.hotels ?? [];
  const currency = trip.hotels?.currency ?? trip.trip_request?.currency ?? "USD";
  const chosen = trip.itinerary?.hotel?.toLowerCase();
  const nearby = trip.hotels_nearby?.hotels ?? [];

  if (!hotels.length) {
    return (
      <div className="space-y-3">
        {trip.hotels?.error && <Banner tone="warn">Hotel prices aren&apos;t available: {trip.hotels.error}</Banner>}
        {nearby.length > 0 ? (
          <Card className="p-4">
            <h3 className="mb-2 font-semibold">Hotels in the area (no prices)</h3>
            <ul className="space-y-1 text-sm">
              {nearby.map((h) => (
                <li key={h.name}>
                  {h.name} <span className="text-xs text-muted">{h.address}</span>
                </li>
              ))}
            </ul>
          </Card>
        ) : (
          <Card className="p-8 text-center text-sm text-muted">
            <BedDouble className="mx-auto mb-2 size-6" aria-hidden />
            Hotels appear here once the planner has searched.
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {trip.hotels?.note && <Banner tone="accent">{trip.hotels.note}</Banner>}
      {choose.error && <Banner tone="danger">{errorText(choose.error)}</Banner>}
      {hotels.map((hotel) => {
        const isChosen = hotel.name.toLowerCase() === chosen;
        return (
          <Card key={hotel.hotel_id ?? hotel.name} className={`flex gap-3 p-3 ${isChosen ? "border-accent" : ""}`}>
            {hotel.thumbnail_url || hotel.photo_url ? (
              // Hotel photos come from LiteAPI's CDN; a plain img avoids configuring remote image hosts.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={hotel.thumbnail_url || hotel.photo_url}
                alt=""
                className="size-20 shrink-0 rounded-lg object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex size-20 shrink-0 items-center justify-center rounded-lg bg-surface-muted">
                <BedDouble className="size-6 text-muted" aria-hidden />
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{hotel.name}</span>
                {isChosen && <Badge tone="accent">In your plan</Badge>}
              </div>
              <div className="flex flex-wrap items-center gap-x-2 text-xs text-muted">
                {hotel.stars != null && (
                  <span className="flex items-center gap-0.5">
                    {hotel.stars} <Star className="size-3" aria-label="stars" />
                  </span>
                )}
                {hotel.rating != null && (
                  <span>
                    Rating {hotel.rating}
                    {hotel.review_count ? ` (${hotel.review_count} reviews)` : ""}
                  </span>
                )}
                <span className="truncate">{hotel.address}</span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium">{money(hotel.price_per_night, currency)} / night</span>
                <span className="text-muted">{money(hotel.total_price, currency)} total</span>
                <Badge tone={hotel.refundable ? "ok" : "neutral"}>
                  {hotel.refundable ? "Free cancellation" : "Non-refundable"}
                </Badge>
              </div>
            </div>
            {trip.itinerary && !isChosen && (
              <Button
                className="self-center"
                onClick={() => choose.mutate(hotel.name)}
                disabled={busy || choose.isPending}
                title="Use this hotel in your plan. Recalculates the cost instantly."
              >
                {choose.isPending && choose.variables === hotel.name ? "Saving…" : "Choose"}
              </Button>
            )}
          </Card>
        );
      })}
    </div>
  );
}
