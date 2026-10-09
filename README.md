# 🌍 Travel Planner

> An AI-powered, multi-agent travel planning application built with **Google ADK**, **FastAPI**, and **Next.js**.

---

## ✈️ What It Does

Travel Planner is a full-stack conversational travel assistant. You describe a trip — destination, dates, budget, and interests — and a coordinated team of AI agents researches real weather forecasts, live hotel availability, and local attractions, then builds a validated day-by-day itinerary.

| Part | Technology | Purpose |
|---|---|---|
| **Backend** | Python · Google ADK · FastAPI | AI agents + REST API |
| **Frontend** | Next.js 16 · React 19 · TypeScript | Web UI with auth, chat, map, hotels, budget |

---

## 🤖 Google ADK — What It Is and How It's Used Here

### What is Google ADK?

**Google Agent Development Kit (ADK)** is an open-source Python framework from Google DeepMind for building, running, and orchestrating AI agents powered by Gemini models. Key concepts:

| Concept | Description |
|---|---|
| **Agent** | An LLM with a name, instruction, and a set of tools or sub-agents it can call |
| **Sub-agent** | An agent invoked by a parent agent — ADK automatically wraps it as a callable tool |
| **`single_turn`** | A sub-agent that runs once per invocation, returns its result, and exits |
| **Tool** | A Python function the agent can call (API calls, code, structured workflows) |
| **Session state** | A key-value store shared across all agents in a conversation turn |
| **Callback** | A hook (`before_tool_callback`, `after_tool_callback`) to intercept tool calls |
| **`adk web`** | A built-in local dev UI for chatting with your agent during development |
| **`google-adk[db]`** | The `[db]` extra adds SQLite/PostgreSQL session persistence |

ADK handles routing between agents, tool-call serialisation, model fallback, and session management — you write plain Python with no custom prompt scaffolding required.

### How This Project Uses ADK

```
travel_coordinator          (root_agent · Gemini Flash · chats with the user)
 ├─ weather_agent           single_turn → get_weather_forecast          (Open-Meteo, free)
 ├─ hotel_agent             single_turn → search_hotels, find_hotels_near (LiteAPI + Geoapify)
 ├─ places_agent            single_turn → find_attractions              (Geoapify)
 └─ plan_itinerary          Python tool → itinerary_agent (structured JSON plan)
                                        → review.py (Python validator)
                                        → one AI fix pass if the plan has errors
```

**Step-by-step flow:**

1. The user sends a message to `travel_coordinator`.
2. As soon as the coordinator knows the destination and dates, it calls **all three specialist sub-agents in parallel** (same turn), each receiving a `TripRequest`.
3. Each specialist calls its external API tool(s) and stores results in **shared session state** (`weather`, `hotels`, `attractions`).
4. The coordinator calls `plan_itinerary` — a Python tool that invokes `itinerary_agent` to produce a structured JSON plan, then validates it with `review.py` (exact dates, only hotels/places from search results, budget). If there are errors, the itinerary agent gets one more fix pass.
5. The coordinator presents the validated plan (with warnings, hotel options, and budget) to the user.

**Key ADK features used:**

- `Agent` with `sub_agents=` — ADK auto-wraps each sub-agent as a tool for the coordinator
- `before_tool_callback` — enforces a per-message call limit to prevent runaway loops
- `after_tool_callback` — extracts the `TripRequest` from any specialist call and saves it to session state
- Instruction functions (not strings) — so each turn sees today's live date
- `google-adk[db]` — persists sessions to SQLite (dev) or PostgreSQL (production)
- `adk web` — interactive development UI to chat with the agent without any frontend

---

## 📁 Project Structure

```
Travel_Planner/
├── backend/
│   ├── travel_agent/          # ADK agent definitions
│   │   ├── agent.py           # root_agent (travel_coordinator)
│   │   ├── prompts.py         # instruction functions for all agents
│   │   ├── models.py          # Gemini model selection + fallback logic
│   │   ├── callbacks.py       # before/after tool callbacks
│   │   ├── workflows.py       # plan_itinerary tool (orchestrates itinerary agent + review)
│   │   ├── review.py          # Python itinerary validator
│   │   ├── schemas.py         # Pydantic models (TripRequest, ItineraryDay, …)
│   │   ├── plan_updates.py    # SSE progress event helpers
│   │   └── sub_agents/
│   │       ├── weather_agent.py
│   │       ├── hotel_agent.py
│   │       ├── places_agent.py
│   │       └── itinerary_agent.py
│   ├── tools/                 # External API wrappers
│   │   ├── weather.py         # Open-Meteo (no key required)
│   │   ├── hotels.py          # LiteAPI hotel search
│   │   ├── places.py          # Geoapify attractions
│   │   └── budget.py          # Budget calculation helpers
│   ├── app/                   # FastAPI server
│   │   ├── main.py            # App factory, CORS, startup checks
│   │   ├── auth.py            # JWT verification (Better Auth EdDSA tokens)
│   │   ├── config.py          # Settings (pydantic-settings, .env)
│   │   ├── routes/            # /api/trips, /api/auth, /api/health
│   │   └── services/          # ADK session runner, trip persistence
│   ├── evals/                 # Agent evaluation scripts
│   ├── tests/                 # Pytest test suite
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/                   # Next.js App Router pages
│   ├── components/
│   │   ├── auth/              # Sign-in / sign-up forms (Better Auth)
│   │   ├── chat/              # Trip chat with live SSE progress stream
│   │   ├── plan/              # Day-by-day itinerary view
│   │   ├── map/               # MapLibre GL interactive map
│   │   ├── hotels/            # Hotel picker (PATCH itinerary)
│   │   └── budget/            # Budget breakdown
│   ├── lib/                   # Auth client, API client, utilities
│   ├── hooks/                 # React Query hooks
│   └── .env.example
└── docker-compose.yml         # Local PostgreSQL (optional)
```

---

## 🛠️ Tech Stack

### Backend

| Library | Version | Role |
|---|---|---|
| `google-adk[db]` | ≥ 2.11 | Agent orchestration, session management |
| `fastapi` + `uvicorn` | latest | REST API server |
| `pydantic-settings` | ≥ 2.15 | Config from `.env` |
| `PyJWT` | ≥ 2.15 | JWT token verification |
| `httpx` | ≥ 0.28 | Async HTTP client for external APIs |
| `asyncpg` | ≥ 0.31 | Async PostgreSQL driver |
| SQLite (built-in) | — | Default local session store |

### Frontend

| Library | Role |
|---|---|
| Next.js 16 + React 19 + TypeScript | App framework |
| Better Auth | Email/password auth, EdDSA JWT tokens |
| TanStack Query v5 | Server state, caching |
| MapLibre GL + react-map-gl | Interactive map (OpenFreeMap tiles, free) |
| Tailwind CSS v4 | Styling |
| `eventsource-parser` | Streaming SSE from the API |

### External APIs

| API | What It Provides | Key Required |
|---|---|---|
| Google Gemini (via ADK) | LLM for all agents | `GOOGLE_API_KEY` |
| Open-Meteo | 7-day weather forecast | ❌ Free, no key |
| LiteAPI | Live hotel search & pricing | `LITEAPI_KEY` |
| Geoapify | Attractions, POI data, geocoding | `GEOAPIFY_API_KEY` |

> **Attribution**: Any page displaying place or attraction data from Geoapify **must** show "Powered by Geoapify" (free-plan terms).

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

```env
# Gemini
GOOGLE_API_KEY=your_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Optional model overrides (defaults: gemini-3.5-flash / gemini-3.5-flash-lite)
TRAVEL_AGENT_MODEL=
TRAVEL_SPECIALIST_MODEL=
# Fallback models tried in order on 503/429 (comma-separated)
TRAVEL_AGENT_FALLBACK_MODELS=
TRAVEL_SPECIALIST_FALLBACK_MODELS=

# Travel APIs
LITEAPI_KEY=your_key_here
GEOAPIFY_API_KEY=your_key_here

# API server
APP_ENV=development          # enables /docs and POST /api/auth/dev-token
DATABASE_URL=                # empty = SQLite; or postgresql+asyncpg://...
AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks
AUTH_ISSUER=http://localhost:3000
AUTH_AUDIENCE=travel-planner-api
JWT_SECRET=                  # ≥32 chars; empty in dev uses a temporary secret
CORS_ORIGINS=http://localhost:3000

# Rate limits (per user)
RATE_LIMIT_PER_MINUTE=5
RATE_LIMIT_PER_DAY=40
```

### Frontend (`frontend/.env.local`)

```env
BETTER_AUTH_SECRET=your_secret_here      # ≥32 random chars
BETTER_AUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8080
```

---

## 🚀 Running Locally

### Option A — Agent Only (ADK Dev UI)

Use this to test the agent without the frontend.

```bash
cd backend
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt

copy .env.example .env   # fill in GOOGLE_API_KEY, LITEAPI_KEY, GEOAPIFY_API_KEY

.venv\Scripts\python -m pytest -q
.venv\Scripts\adk web --port 8000 .
```

Open http://localhost:8000, select **travel_agent**, and start chatting.

> **Windows note:** `adk web` does not auto-reload on file changes — restart it after editing code.

---

### Option B — Full Stack (Backend + Frontend)

#### 1. Backend

```bash
cd backend
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env    # fill in API keys + set AUTH_JWKS_URL=http://localhost:3000/api/auth/jwks

.venv\Scripts\uvicorn app.main:app --port 8080
```

Interactive API docs: http://localhost:8080/docs (development only).

#### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local   # set BETTER_AUTH_SECRET

# Create auth database tables (first time only)
npx auth@latest migrate --config lib/auth.ts -y

npm run dev
```

Open http://localhost:3000, create an account, and start planning a trip.

---

### Option C — PostgreSQL via Docker

```bash
# From the project root:
docker compose up -d db
```

Then set in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://travel:travel@localhost:5432/travel_planner
```

---

## 🔌 REST API Reference

All `/api/trips` endpoints require `Authorization: Bearer <token>`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/health/ready` | Database connectivity check |
| `POST` | `/api/auth/dev-token` | `{"user_id": "alice"}` → token (dev only) |
| `POST` | `/api/trips` | Start a new trip (conversation) |
| `GET` | `/api/trips` | List your trips, newest first |
| `GET` | `/api/trips/{id}` | Messages + saved trip data (itinerary, hotels, weather) |
| `DELETE` | `/api/trips/{id}` | Delete a trip |
| `POST` | `/api/trips/{id}/messages` | `{"text": "..."}` → **Server-Sent Events** stream |
| `PATCH` | `/api/trips/{id}/itinerary` | Change the chosen hotel (no AI call; cost recalculated in code) |

### SSE Message Stream Events

| Event | Payload | Meaning |
|---|---|---|
| `progress` | `{"agent": "hotel_agent"}` | A specialist or the planner started work |
| `message` | `{"text": "..."}` | The coordinator's reply to the user |
| `trip` | `{itinerary, hotels, weather, ...}` | Updated trip data |
| `done` | — | Stream complete |
| `error` | `{"code": "ai_unavailable"}` | Error during generation |

Error codes: `ai_unavailable`, `ai_quota_exceeded`. Non-stream errors are JSON: `{"error": {"code": "...", "message": "..."}}`.

### Rate Limits

- 5 messages per user per minute, 40 per day
- 2 000 characters per message
- 1 concurrent message per trip (409 if another is in progress)
- 30 model calls per message (enforced by `before_tool_callback`)

---

## 🔐 Authentication

The frontend uses **Better Auth** (email + password) running inside the Next.js app. It issues short-lived **15-minute EdDSA JWT tokens** stored in the browser. The FastAPI backend verifies these tokens against the frontend's public keys at `/api/auth/jwks` (configured via `AUTH_JWKS_URL`). No token is stored server-side.

In development, you can skip the frontend and obtain a token directly:

```bash
curl -X POST http://localhost:8080/api/auth/dev-token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice"}'
```

---

## 📊 Cost & Quota Notes

| Fact | Detail |
|---|---|
| One full planning message | ~10 Gemini API requests |
| Gemini free tier | ~20 requests/model/day |
| Model fallback | Coordinator and specialists each have configurable fallback model lists tried in order on 503/429 |
| Open-Meteo | Free, unlimited, no key needed |
| LiteAPI sandbox | Returns test prices; a note is surfaced to the user |

---

## 🗺️ Map

The interactive map uses **MapLibre GL** with **OpenFreeMap** tiles (free, no key required). The `predev` / `prebuild` npm scripts copy MapLibre's web worker into `public/maplibre/` because Turbopack does not emit it automatically.

---

## 📄 License & Attribution

Place and attraction data is provided by **Geoapify**. Any page displaying this data must include the attribution: **Powered by Geoapify**.
