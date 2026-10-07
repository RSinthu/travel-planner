import { Wallet } from "lucide-react";

import { Card } from "@/components/ui";
import { money } from "@/lib/format";
import type { Cost } from "@/lib/types";

const PARTS: { key: keyof Cost["breakdown"]; label: string; color: string }[] = [
  { key: "hotel", label: "Hotel", color: "bg-accent" },
  { key: "food_and_local_transport", label: "Food and local transport", color: "bg-ok" },
  { key: "activities", label: "Tickets and activities", color: "bg-warn" },
  { key: "flights", label: "Flights", color: "bg-muted" },
];

export function BudgetView({ cost }: { cost: Cost | null | undefined }) {
  if (!cost) {
    return (
      <Card className="p-8 text-center text-sm text-muted">
        <Wallet className="mx-auto mb-2 size-6" aria-hidden />
        The cost estimate appears with your day-by-day plan.
      </Card>
    );
  }
  const total = cost.estimated_total || 1;
  const parts = PARTS.filter((p) => cost.breakdown[p.key] > 0);

  return (
    <Card className="space-y-4 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-sm text-muted">Estimated total</div>
          <div className="text-2xl font-semibold">{money(cost.estimated_total, cost.currency)}</div>
        </div>
        {cost.budget != null && (
          <div className="text-right">
            <div className="text-sm text-muted">Budget {money(cost.budget, cost.currency)}</div>
            <div className={`font-medium ${cost.within_budget ? "text-ok" : "text-danger"}`}>
              {cost.within_budget
                ? `${money(cost.remaining, cost.currency)} left`
                : `${money(-(cost.remaining ?? 0), cost.currency)} over`}
            </div>
          </div>
        )}
      </div>

      <div className="flex h-3 overflow-hidden rounded-full bg-surface-muted" aria-hidden>
        {parts.map((p) => (
          <div key={p.key} className={p.color} style={{ width: `${(cost.breakdown[p.key] / total) * 100}%` }} />
        ))}
      </div>

      <ul className="space-y-1 text-sm">
        {parts.map((p) => (
          <li key={p.key} className="flex items-center gap-2">
            <span className={`size-2.5 rounded-sm ${p.color}`} aria-hidden />
            <span className="flex-1">{p.label}</span>
            <span>{money(cost.breakdown[p.key], cost.currency)}</span>
          </li>
        ))}
      </ul>

      <p className="text-xs text-muted">
        {money(cost.per_person, cost.currency)} per person · {money(cost.per_day, cost.currency)} per day.
        {!cost.hotel_included && " The hotel isn't included: no hotel price was found."} Food and tickets are estimates.
      </p>
    </Card>
  );
}
