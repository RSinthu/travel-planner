"use client";

import { MapPin, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Banner, Button, Card } from "@/components/ui";
import { useCreateTrip, useDeleteTrip, useTrips } from "@/hooks/use-trips";
import { errorText, timeAgo } from "@/lib/format";

export function TripList() {
  const router = useRouter();
  const trips = useTrips();
  const createTrip = useCreateTrip();
  const deleteTrip = useDeleteTrip();

  async function startTrip() {
    const trip = await createTrip.mutateAsync();
    router.push(`/trips/${trip.id}`);
  }

  async function remove(id: string, title: string) {
    if (window.confirm(`Delete "${title}"? This can't be undone.`)) await deleteTrip.mutateAsync(id);
  }

  const error = trips.error ?? createTrip.error ?? deleteTrip.error;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Your trips</h1>
        <Button variant="primary" onClick={startTrip} disabled={createTrip.isPending}>
          <Plus className="size-4" aria-hidden /> New trip
        </Button>
      </div>

      {error && (
        <div className="mb-4">
          <Banner tone="danger">{errorText(error)}</Banner>
        </div>
      )}

      {trips.isPending && <p className="text-sm text-muted">Loading your trips…</p>}

      {trips.data?.length === 0 && (
        <Card className="p-8 text-center">
          <MapPin className="mx-auto mb-3 size-8 text-accent" aria-hidden />
          <h2 className="mb-1 font-semibold">Plan your first trip</h2>
          <p className="mb-4 text-sm text-muted">
            Tell the planner where and when. It checks the weather, finds hotels and builds a day-by-day plan.
          </p>
          <Button variant="primary" onClick={startTrip} disabled={createTrip.isPending}>
            Start planning
          </Button>
        </Card>
      )}

      <ul className="flex flex-col gap-2">
        {trips.data?.map((trip) => (
          <li key={trip.id}>
            <Card className="flex items-center gap-3 p-3 transition hover:border-accent/50">
              <Link href={`/trips/${trip.id}`} className="min-w-0 flex-1">
                <div className="truncate font-medium">{trip.title}</div>
                <div className="text-xs text-muted">Updated {timeAgo(trip.updated_at)}</div>
              </Link>
              <Button
                variant="ghost"
                onClick={() => remove(trip.id, trip.title)}
                aria-label={`Delete ${trip.title}`}
                title="Delete trip"
              >
                <Trash2 className="size-4 text-muted" aria-hidden />
              </Button>
            </Card>
          </li>
        ))}
      </ul>
    </main>
  );
}
