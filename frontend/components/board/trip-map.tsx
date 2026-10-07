"use client";

// MapLibre with OpenFreeMap tiles: free, no key, no request limits.
// Loaded only in the browser (see map-view.tsx): MapLibre needs `window`.
import "maplibre-gl/dist/maplibre-gl.css";

import { BedDouble } from "lucide-react";
import { setWorkerUrl } from "maplibre-gl";
import { useMemo, useState } from "react";
import Map, { Marker, NavigationControl, Popup } from "react-map-gl/maplibre";

import type { TripData } from "@/lib/types";

// Turbopack doesn't emit MapLibre's worker; scripts/copy-maplibre-worker.mjs serves it from public/.
setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const DAY_COLORS = ["#1f5fae", "#0f6e56", "#993c1d", "#534ab7", "#993556", "#854f0b"];

type Point = { key: string; lat: number; lon: number; label: string; detail: string; day?: number; hotel?: boolean };

function points(trip: TripData): Point[] {
  const result: Point[] = [];
  const itinerary = trip.itinerary;
  if (itinerary) {
    itinerary.days.forEach((plan, dayIndex) =>
      plan.activities.forEach((activity, i) => {
        const d = activity.details;
        if (d?.latitude != null && d?.longitude != null) {
          result.push({
            key: `${dayIndex}-${i}`,
            lat: d.latitude,
            lon: d.longitude,
            label: d.name,
            detail: `Day ${dayIndex + 1}, ${activity.time_of_day}`,
            day: dayIndex,
          });
        }
      }),
    );
    const h = itinerary.hotel_details;
    if (h?.latitude != null && h?.longitude != null) {
      result.push({ key: "hotel", lat: h.latitude, lon: h.longitude, label: h.name, detail: "Your hotel", hotel: true });
    }
    return result;
  }
  // No plan yet: show the research.
  for (const a of trip.attractions?.attractions ?? []) {
    if (a.latitude != null && a.longitude != null) {
      result.push({ key: `a-${a.name}`, lat: a.latitude, lon: a.longitude, label: a.name, detail: a.types.join(", ") });
    }
  }
  for (const h of trip.hotels?.hotels ?? []) {
    if (h.latitude != null && h.longitude != null) {
      result.push({ key: `h-${h.name}`, lat: h.latitude, lon: h.longitude, label: h.name, detail: "Hotel", hotel: true });
    }
  }
  return result;
}

export default function TripMap({ trip }: { trip: TripData }) {
  const pins = useMemo(() => points(trip), [trip]);
  const [selected, setSelected] = useState<Point | null>(null);

  if (!pins.length) {
    return <div className="flex h-full items-center justify-center text-sm text-muted">No places to show yet.</div>;
  }

  const lats = pins.map((p) => p.lat);
  const lons = pins.map((p) => p.lon);
  const pad = 0.005;
  const bounds: [[number, number], [number, number]] = [
    [Math.min(...lons) - pad, Math.min(...lats) - pad],
    [Math.max(...lons) + pad, Math.max(...lats) + pad],
  ];
  const dayNumbers = new globalThis.Map<number, number>();

  return (
    <Map
      key={pins.map((p) => p.key).join("|")} // refit when the places change
      initialViewState={{ bounds, fitBoundsOptions: { padding: 40, maxZoom: 15 } }}
      mapStyle={STYLE_URL}
      style={{ width: "100%", height: "100%" }}
      attributionControl={{ compact: true }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      {pins.map((pin) => {
        if (pin.hotel) {
          return (
            <Marker key={pin.key} latitude={pin.lat} longitude={pin.lon} anchor="center"
              onClick={(e) => { e.originalEvent.stopPropagation(); setSelected(pin); }}>
              <span className="flex size-8 cursor-pointer items-center justify-center rounded-full border-2 border-white bg-foreground text-background shadow" aria-label={pin.label}>
                <BedDouble className="size-4" aria-hidden />
              </span>
            </Marker>
          );
        }
        const color = pin.day != null ? DAY_COLORS[pin.day % DAY_COLORS.length] : "#5f5e5a";
        const number = pin.day != null ? (dayNumbers.get(pin.day) ?? 0) + 1 : undefined;
        if (pin.day != null) dayNumbers.set(pin.day, number!);
        return (
          <Marker key={pin.key} latitude={pin.lat} longitude={pin.lon} anchor="center"
            onClick={(e) => { e.originalEvent.stopPropagation(); setSelected(pin); }}>
            <span
              className="flex size-7 cursor-pointer items-center justify-center rounded-full border-2 border-white text-xs font-semibold text-white shadow"
              style={{ background: color }}
              aria-label={pin.label}
            >
              {pin.day != null ? `${pin.day + 1}.${number}` : ""}
            </span>
          </Marker>
        );
      })}
      {selected && (
        <Popup latitude={selected.lat} longitude={selected.lon} anchor="bottom" offset={18}
          onClose={() => setSelected(null)} closeOnClick={false}>
          <div className="text-sm text-[#1f1e1c]">
            <div className="font-semibold">{selected.label}</div>
            <div className="text-xs text-[#6b6963]">{selected.detail}</div>
          </div>
        </Popup>
      )}
    </Map>
  );
}
