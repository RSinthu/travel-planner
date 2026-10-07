// Shapes of the FastAPI responses (see backend/app/schemas.py and the tools).

export type TripSummary = { id: string; title: string; updated_at: number };

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  at: number;
  /** User messages only: false when the turn failed and got no reply. */
  answered?: boolean | null;
};

export type TripRequest = {
  city: string;
  country_code: string;
  start_date: string;
  end_date: string;
  adults: number;
  currency: string;
  max_price_per_night: number;
  total_budget?: number;
  interests: string;
};

export type WeatherDay = {
  date: string;
  condition: string;
  temp_max_c: number | null;
  temp_min_c: number | null;
  precipitation_mm: number | null;
  rain_probability_pct: number | null;
  rain_likely: boolean;
};

export type Hotel = {
  hotel_id: string;
  name: string;
  address: string;
  stars: number | null;
  rating: number | null;
  review_count?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  photo_url?: string;
  thumbnail_url?: string;
  room_name: string;
  board: string;
  refundable: boolean;
  total_price: number;
  price_per_night: number;
};

export type Attraction = {
  name: string;
  local_name?: string;
  types: string[];
  unesco: boolean;
  address: string;
  latitude: number | null;
  longitude: number | null;
  opening_hours?: string;
  website?: string;
};

export type PlaceDetails = {
  name: string;
  latitude: number | null;
  longitude: number | null;
  address: string;
  opening_hours?: string;
  types?: string[];
  unesco?: boolean;
  website?: string;
};

export type Activity = {
  time_of_day: "morning" | "afternoon" | "evening";
  title: string;
  place: string;
  indoor: boolean;
  details?: PlaceDetails | null;
};

export type DayPlan = { date: string; weather: string; activities: Activity[] };

export type Itinerary = {
  title: string;
  hotel: string;
  days: DayPlan[];
  daily_spend_per_person: number;
  activities_total: number;
  tips: string[];
  hotel_details?: (Partial<Hotel> & { name: string }) | null;
};

export type Cost = {
  currency: string;
  breakdown: { hotel: number; flights: number; activities: number; food_and_local_transport: number };
  estimated_total: number;
  per_person: number;
  per_day: number;
  hotel_included: boolean;
  budget?: number;
  remaining?: number;
  within_budget?: boolean;
};

export type Review = { errors: string[]; warnings: string[]; cost: Cost | null };

export type TripData = {
  trip_request?: TripRequest;
  weather?: { days?: WeatherDay[]; error?: string };
  hotels?: { nights?: number; currency?: string; hotels?: Hotel[]; note?: string; error?: string };
  hotels_nearby?: { hotels?: { name: string; address: string; latitude: number; longitude: number }[]; error?: string };
  attractions?: { attractions?: Attraction[]; error?: string };
  itinerary?: Itinerary;
  itinerary_review?: Review;
};

export type TripDetail = TripSummary & { busy: boolean; messages: ChatMessage[]; trip: TripData };

export type StepName = "weather_agent" | "hotel_agent" | "places_agent" | "plan_itinerary";

export type StreamEvent =
  | { type: "progress"; step: StepName; status: "started" | "done"; message: string; ok?: boolean }
  | { type: "message"; role: "assistant"; text: string }
  | { type: "trip"; data: Partial<TripData> }
  | { type: "done"; trip_id: string }
  | { type: "error"; code: string; message: string };
