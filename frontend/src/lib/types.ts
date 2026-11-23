// 백엔드 응답 모양. backend/app/schemas.py, Admin_Docs/overview/api-list.md와 같아야 한다.

export type Level = 1 | 2 | 3 | 4;

export interface PlaceCard {
  code: string;
  name: string;
  category: string;
  category_label: string;
  level: Level | null;
  level_label: string | null;
  observed_at: string | null;
  stale: boolean;
  calm_text: string | null;
  distance_km: number | null;
}

export interface HomeResponse {
  answer: { label: string; place: PlaceCard } | null;
  top: PlaceCard[];
  place_count: number;
}

export interface CategoryCount {
  value: string;
  label: string;
  count: number;
}

export interface PlaceListResponse {
  places: PlaceCard[];
  categories: CategoryCount[];
}

export interface TimelinePoint {
  time: string;
  level: Level;
  level_label: string;
  is_now: boolean;
  axis_label: string;
  full_label: string;
}

export interface Recommend {
  start_index: number;
  end_index: number;
  tag: string;
}

export interface PlaceDetailResponse {
  place: {
    code: string;
    name: string;
    eng_name: string;
    category: string;
    category_label: string;
    lat: number;
    lng: number;
  };
  status: {
    level: Level;
    level_label: string;
    observed_at: string;
    stale: boolean;
    ppltn_min: number | null;
    ppltn_max: number | null;
  } | null;
  answer: { kind: string; label: string; lines: string[]; detail: string | null } | null;
  timeline: TimelinePoint[];
  recommend: Recommend | null;
  nearby_top: PlaceCard | null;
  primary_action: "directions" | "nearby";
  directions_url: string;
}

export interface NearbyResponse {
  origin: "place" | "location";
  base: PlaceCard | null;
  alternatives: PlaceCard[];
}

export interface SearchResponse {
  query: string;
  results: PlaceCard[];
  suggestions: PlaceCard[];
}
