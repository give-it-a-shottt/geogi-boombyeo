import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/backend";
import { KNOWN_PLACES } from "@/lib/places";

/** 검색엔진용 주소 목록: 홈 · 검색 · 정보 + 장소 121곳 */
export default function sitemap(): MetadataRoute.Sitemap {
  const fixed: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "always", priority: 1 },
    { url: `${SITE_URL}/search`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/about`, changeFrequency: "monthly", priority: 0.3 },
  ];
  const places: MetadataRoute.Sitemap = KNOWN_PLACES.map((place) => ({
    url: `${SITE_URL}/place/${place.code}`,
    changeFrequency: "always",
    priority: 0.8,
  }));
  return [...fixed, ...places];
}
