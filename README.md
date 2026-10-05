# Travel Planner

Multi-agent travel planner built with Google ADK, FastAPI and Next.js.

- `backend/travel_agent/` - ADK agents (run `adk web` from `backend/` to test)
- `backend/tools/` - API tools (Open-Meteo, LiteAPI, Geoapify)
- `backend/app/` - FastAPI server
- `frontend/` - Next.js + CopilotKit UI

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
