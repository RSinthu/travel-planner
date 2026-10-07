// Server-side Better Auth: email and password accounts, plus short-lived JWTs
// that the FastAPI backend verifies with this app's public keys (/api/auth/jwks).
// Server code only (it opens the database). No "server-only" import, because the
// Better Auth CLI loads this file outside Next.js to create the tables.
import { DatabaseSync } from "node:sqlite";
import path from "node:path";

import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { jwt } from "better-auth/plugins";

export const API_AUDIENCE = "travel-planner-api";

const baseURL = process.env.BETTER_AUTH_URL ?? "http://localhost:3000";
// turbopackIgnore: a runtime path, so the bundler must not trace the whole project from it.
const databasePath = path.resolve(/*turbopackIgnore: true*/ process.cwd(), process.env.AUTH_DATABASE_PATH ?? "auth.sqlite");

export const auth = betterAuth({
  baseURL,
  database: new DatabaseSync(databasePath),
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
    autoSignIn: true,
  },
  plugins: [
    jwt({
      jwt: {
        issuer: baseURL,
        audience: API_AUDIENCE,
        expirationTime: "15m",
        // Only what the API needs: sub (the user id) is added automatically.
        definePayload: ({ user }) => ({ email: user.email }),
      },
    }),
    nextCookies(), // must be last: lets server actions set auth cookies
  ],
});
