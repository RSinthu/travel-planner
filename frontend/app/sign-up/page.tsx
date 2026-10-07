import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth/auth-form";
import { auth } from "@/lib/auth";

export default async function SignUpPage() {
  if (await auth.api.getSession({ headers: await headers() })) redirect("/trips");
  return <AuthForm mode="sign-up" />;
}
