import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { TripList } from "@/components/trips/trip-list";
import { auth } from "@/lib/auth";

export default async function TripsPage() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect("/sign-in");

  return (
    <>
      <AppHeader userName={session.user.name || session.user.email} />
      <TripList />
    </>
  );
}
