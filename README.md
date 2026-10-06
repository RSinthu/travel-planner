# Travel Planner

Multi-agent travel planner built with Google ADK, FastAPI and Next.js.

- `backend/travel_agent/` - ADK agents (run `adk web` from `backend/` to test)
- `backend/tools/` - API tools (Open-Meteo, LiteAPI, Geoapify)
- `backend/app/` - FastAPI server
- `frontend/` - Next.js 16 app: sign-in, trip chat with live progress, plan, map, hotels, budget

Place and attraction data comes from Geoapify: any page that shows it must display "Powered by Geoapify" (free-plan terms).

## Run the agent (development)

From `backend/`, with `backend/.env` filled in (see `.env.example`):

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest -q
.venv/Scripts/adk web --port 8000 .
```

Then open http://localhost:8000 and pick `travel_agent`. `adk web` is for development only.
On Windows it does not auto-reload: restart it after changing code.

## Run the API (FastAPI)

From `backend/`:

```bash
.venv/Scripts/uvicorn app.main:app --port 8080
```

- Sessions are stored in the database from `DATABASE_URL`: empty = SQLite file `backend/travel_planner.db`.
  For PostgreSQL: `docker compose up -d db` (from the project root), then
  `DATABASE_URL=postgresql+asyncpg://travel:travel@localhost:5432/travel_planner`.
  The server checks the database at startup and stops with a clear message if it cannot connect.
- Interactive docs: http://localhost:8080/docs (development only).

| Method | Path | |
|---|---|---|
| GET | `/api/health`, `/api/health/ready` | liveness / database check |
| POST | `/api/auth/dev-token` | `{"user_id": "alice"}` → token (development only) |
| POST | `/api/trips` | start a trip (conversation) |
| GET | `/api/trips` | your trips, newest first |
| GET | `/api/trips/{id}` | messages + saved trip data (itinerary, hotels, weather, ...) |
| DELETE | `/api/trips/{id}` | delete a trip |
| POST | `/api/trips/{id}/messages` | `{"text": "..."}` → Server-Sent Events stream |

All `/api/trips` calls need `Authorization: Bearer <token>`; the token's `sub` is the user id.
The message stream sends `progress` (a specialist or the planner started), `message` (the reply),
`trip` (trip data that changed), then `done` or `error` (`ai_unavailable`, `ai_quota_exceeded`, ...).
Errors elsewhere are JSON: `{"error": {"code": "...", "message": "..."}}`.

Limits (see `.env.example`): 5 messages per user per minute and 40 per day, 2000 characters per message,
one message at a time per trip (409 otherwise), 30 model calls per message.
If a Gemini model is overloaded (503) or out of quota (429), the agents fall back to the next model
(`TRAVEL_AGENT_FALLBACK_MODELS`, `TRAVEL_SPECIALIST_FALLBACK_MODELS`).

## Run the whole app

1. Backend: in `backend/.env` set `AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks` (see `.env.example`), then
   from `backend/`: `.venv/Scripts/uvicorn app.main:app --port 8080`
2. Frontend, from `frontend/` (first time: `npm install`, copy `.env.example` to `.env.local` and set
   `BETTER_AUTH_SECRET`, then create the accounts tables with `npx auth@latest migrate --config lib/auth.ts -y`):

```bash
npm run dev
```

3. Open http://localhost:3000, create an account and start a trip.

How sign-in works: Better Auth (in the Next.js app) keeps email and password accounts in `frontend/auth.sqlite`
and issues 15-minute EdDSA tokens. The browser sends them to FastAPI, which checks them against the
frontend's public keys at `/api/auth/jwks` (issuer `http://localhost:3000`, audience `travel-planner-api`).

Frontend notes:
- Map: MapLibre with free OpenFreeMap tiles. `npm run dev` / `npm run build` first copy MapLibre's web worker into
  `public/maplibre/` (Turbopack does not emit it).
- Choosing another hotel in the Hotels tab calls `PATCH /api/trips/{id}/itinerary`: the cost is recalculated in code,
  with no AI requests.

## Agents

```
travel_coordinator  (chats with the user, gemini-3.5-flash)
 ├─ weather_agent   single_turn → get_weather_forecast             (Open-Meteo)
 ├─ hotel_agent     single_turn → search_hotels, find_hotels_near  (LiteAPI, Geoapify)
 ├─ places_agent    single_turn → find_attractions                 (Geoapify)
 └─ plan_itinerary  tool → itinerary_agent (structured plan) → review (code) → one fix if needed
```

1. The coordinator calls the three specialists in parallel, each with the same `TripRequest`.
2. Their raw tool data is kept in session state: `trip_request`, `weather`, `hotels`, `hotels_nearby`, `attractions`.
3. `plan_itinerary` runs the itinerary agent on that data and checks the plan in Python
   (`travel_agent/review.py`): exact dates, only searched places and hotels, total budget.
   Errors go back to the agent once; rainy-day and repeat warnings are passed to the user.
   The result is saved as `itinerary` and `itinerary_review`.

One full planning message uses about 10 Gemini requests; the free tier allows only ~20 per model per day.
