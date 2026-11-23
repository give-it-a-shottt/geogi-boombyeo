"""서울시 공식 파일 2개로 장소 시드(app/seed/places.json)를 만든다.

입력 (backend/data/raw, 출처: 서울 열린데이터광장 OA-21285, 공공누리 1유형)
- seoul-121-places.xlsx : 분류, 장소 코드, 이름, 영문 이름
- seoul-121-areas.zip   : 장소 영역(shapefile, WGS84)

API는 장소 좌표를 주지 않아서, 영역 다각형의 무게중심을 장소 좌표로 쓴다.
실행: uv run --with openpyxl --with pyshp python scripts/build_seed.py
"""

from __future__ import annotations

import io
import json
import warnings
import zipfile
from pathlib import Path

import openpyxl
import shapefile

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "app" / "seed" / "places.json"
# 프론트가 빌드할 때(백엔드 없이도) 121개 장소 페이지 주소와 제목을 알 수 있게 같이 만든다.
FRONT_OUT = ROOT.parent / "frontend" / "src" / "data" / "places.json"


def ring_centroid(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """다각형 고리 하나의 (넓이, 무게중심 x, 무게중심 y). 신발끈 공식."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    if area == 0:
        xs, ys = zip(*points, strict=True)
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return area, cx / (6 * area), cy / (6 * area)


def shape_centroid(shape: shapefile.Shape) -> tuple[float, float]:
    """여러 고리로 된 영역의 넓이 가중 무게중심 (경도, 위도)."""
    parts = list(shape.parts) + [len(shape.points)]
    total = sx = sy = 0.0
    for start, end in zip(parts, parts[1:], strict=False):
        area, cx, cy = ring_centroid(shape.points[start:end])
        weight = abs(area)
        total += weight
        sx += cx * weight
        sy += cy * weight
    if total == 0:
        xmin, ymin, xmax, ymax = shape.bbox
        return (xmin + xmax) / 2, (ymin + ymax) / 2
    return sx / total, sy / total


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sheet = openpyxl.load_workbook(RAW / "seoul-121-places.xlsx").active
    rows = [r[:5] for r in sheet.iter_rows(min_row=2, values_only=True) if r[2]]

    archive = zipfile.ZipFile(RAW / "seoul-121-areas.zip")
    member = {name.rsplit(".", 1)[-1]: name for name in archive.namelist() if "." in name}
    reader = shapefile.Reader(
        shp=io.BytesIO(archive.read(member["shp"])),
        dbf=io.BytesIO(archive.read(member["dbf"])),
        shx=io.BytesIO(archive.read(member["shx"])),
        encoding="utf-8",
    )
    centroids = {
        rec["AREA_CD"]: shape_centroid(shape)
        for rec, shape in zip(reader.records(), reader.shapes(), strict=True)
    }

    places = []
    for category, _no, code, name, eng_name in rows:
        lng, lat = centroids[code]
        places.append(
            {
                "code": code,
                "name": name.strip(),
                "category": category.strip(),
                "eng_name": (eng_name or "").strip(),
                "lat": round(lat, 6),
                "lng": round(lng, 6),
            }
        )
    places.sort(key=lambda p: p["code"])
    OUT.write_text(json.dumps(places, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(places)} places -> {OUT}")

    if FRONT_OUT.parent.is_dir():
        front = [{"code": p["code"], "name": p["name"]} for p in places]
        FRONT_OUT.write_text(
            json.dumps(front, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8"
        )
        print(f"{len(front)} places -> {FRONT_OUT}")


if __name__ == "__main__":
    main()
