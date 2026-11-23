// 기준 시각 문구. 인구 데이터는 약 25분 늦게 들어오므로 "몇 분 전 기준"을 숨기지 않는다.

const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function period(hour: number): string {
  if (hour === 0) return "자정";
  if (hour < 6) return "새벽";
  if (hour < 12) return "오전";
  if (hour === 12) return "낮";
  if (hour < 21) return "오후";
  return "밤";
}

/** "오후 3시 5분" — 한국 시간. 서버와 브라우저에서 같은 글자가 나온다. */
export function clockText(iso: string): string {
  const observed = new Date(iso).getTime();
  if (Number.isNaN(observed)) return "시각 확인 중";
  const kst = new Date(observed + KST_OFFSET_MS);
  const hour = kst.getUTCHours();
  const minute = kst.getUTCMinutes();
  const hourText = hour === 0 ? "밤 12시" : `${period(hour)} ${hour > 12 ? hour - 12 : hour}시`;
  return minute === 0 ? hourText : `${hourText} ${minute}분`;
}

/** "25분 전 기준", "2시간 전 기준" */
export function agoText(iso: string, now: Date): string {
  const observed = new Date(iso).getTime();
  // 시각을 읽을 수 없으면 "NaN분 전"이 아니라 모른다고 말한다.
  if (Number.isNaN(observed)) return "기준 시각 확인 중";
  const minutes = Math.max(0, Math.round((now.getTime() - observed) / 60000));
  if (minutes < 1) return "방금 기준";
  if (minutes < 60) return `${minutes}분 전 기준`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전 기준`;
  return `${Math.floor(hours / 24)}일 전 기준`;
}

/** "0.8km", "350m" */
export function distanceText(km: number): string {
  return km < 1 ? `${Math.max(100, Math.round(km * 10) * 100)}m` : `${km.toFixed(1)}km`;
}
