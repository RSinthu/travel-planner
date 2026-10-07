import { CloudRain, Home, Landmark, Lightbulb, Sun } from "lucide-react";

import { Badge, Card } from "@/components/ui";
import { day } from "@/lib/format";
import type { Activity, TripData, WeatherDay } from "@/lib/types";

const TIME_LABEL = { morning: "Morning", afternoon: "Afternoon", evening: "Evening" } as const;

export function PlanView({ trip }: { trip: TripData }) {
  const itinerary = trip.itinerary;
  const weather = new Map((trip.weather?.days ?? []).map((d) => [d.date, d]));

  if (!itinerary) return <ResearchSoFar trip={trip} weather={[...weather.values()]} />;

  return (
    <div className="space-y-3">
      {itinerary.days.map((plan, index) => {
        const forecast = weather.get(plan.date);
        return (
          <Card key={plan.date} className={`p-4 ${forecast?.rain_likely ? "border-warn/50" : ""}`}>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <h3 className="font-semibold">
                Day {index + 1} · {day(plan.date)}
              </h3>
              <span className="ml-auto">
                {forecast?.rain_likely ? (
                  <Badge tone="warn">
                    <CloudRain className="size-3.5" aria-hidden /> Rain likely
                  </Badge>
                ) : (
                  <Badge>
                    <Sun className="size-3.5" aria-hidden /> {plan.weather}
                  </Badge>
                )}
              </span>
            </div>
            {forecast?.rain_likely && <p className="mb-2 text-xs text-muted">{plan.weather}</p>}
            <ul className="space-y-2">
              {plan.activities.map((activity, i) => (
                <ActivityRow key={i} activity={activity} />
              ))}
            </ul>
          </Card>
        );
      })}

      {itinerary.tips.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <Lightbulb className="size-4 text-accent" aria-hidden /> Tips
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {itinerary.tips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function ActivityRow({ activity }: { activity: Activity }) {
  const details = activity.details;
  return (
    <li className="flex gap-3 text-sm">
      <span className="w-20 shrink-0 text-muted">{TIME_LABEL[activity.time_of_day]}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <span>{activity.title}</span>
          {details?.unesco && <Badge tone="accent">UNESCO</Badge>}
          {activity.place && (
            <span className="text-xs text-muted">{activity.indoor ? "· indoors" : "· outdoors"}</span>
          )}
        </div>
        {details?.opening_hours && <div className="text-xs text-muted">Open {details.opening_hours}</div>}
      </div>
    </li>
  );
}

function ResearchSoFar({ trip, weather }: { trip: TripData; weather: WeatherDay[] }) {
  const attractions = trip.attractions?.attractions ?? [];
  if (!weather.length && !attractions.length) {
    return (
      <Card className="p-8 text-center text-sm text-muted">
        <Home className="mx-auto mb-2 size-6" aria-hidden />
        Your day-by-day plan appears here once the planner has researched your trip.
      </Card>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">No day-by-day plan yet. Here&apos;s the research so far.</p>
      {weather.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 font-semibold">Weather</h3>
          <ul className="space-y-1 text-sm">
            {weather.map((d) => (
              <li key={d.date} className="flex gap-3">
                <span className="w-28 text-muted">{day(d.date)}</span>
                <span className="flex-1">{d.condition}</span>
                <span>
                  {Math.round(d.temp_min_c ?? 0)}–{Math.round(d.temp_max_c ?? 0)}°C
                </span>
                {d.rain_likely && <Badge tone="warn">Rain</Badge>}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {attractions.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 flex items-center gap-2 font-semibold">
            <Landmark className="size-4 text-accent" aria-hidden /> Things to do
          </h3>
          <ul className="space-y-1 text-sm">
            {attractions.slice(0, 10).map((a) => (
              <li key={a.name} className="flex flex-wrap items-center gap-2">
                {a.name}
                {a.unesco && <Badge tone="accent">UNESCO</Badge>}
                <span className="text-xs text-muted">{a.types.join(", ")}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
