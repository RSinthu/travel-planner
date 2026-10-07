import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { TripWorkspace } from "@/components/workspace/trip-workspace";
import { auth } from "@/lib/auth";

export default async function TripPage(props: PageProps<"/trips/[id]">) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect("/sign-in");
  const { id } = await props.params;

  return <TripWorkspace tripId={id} userName={session.user.name || session.user.email} />;
}
