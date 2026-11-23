import places from "@/data/places.json";

// 121곳의 코드와 이름. backend/scripts/build_seed.py가 시드와 함께 만든다.
// 백엔드가 꺼져 있어도 빌드 때 장소 페이지 주소와 제목을 알 수 있다.
export interface KnownPlace {
  code: string;
  name: string;
}

export const KNOWN_PLACES: KnownPlace[] = places;

const BY_CODE = new Map(KNOWN_PLACES.map((place) => [place.code, place]));

export function findKnownPlace(code: string): KnownPlace | undefined {
  return BY_CODE.get(code);
}
