from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


ALIAS_PATH = Path(__file__).resolve().parents[1] / "data" / "korea_location_aliases.json"


@dataclass
class LocationResolveResult:
    raw_location: str | None = None
    region: str | None = None
    city: str | None = None
    district: str | None = None
    area: str | None = None
    landmark: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: float = 0.0
    source: str = "fallback"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_location": self.raw_location,
            "region": self.region,
            "city": self.city,
            "district": self.district,
            "area": self.area,
            "landmark": self.landmark,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "confidence": self.confidence,
            "source": self.source,
            "warnings": self.warnings,
        }


def resolve_location(query: str) -> LocationResolveResult:
    text = query or ""
    local = _resolve_from_alias(text)
    if local.region and os.getenv("USE_REAL_PLACE_API", "false").lower() == "true" and os.getenv("KAKAO_REST_API_KEY"):
        kakao = _resolve_from_kakao(text, local)
        if kakao and kakao.confidence >= local.confidence:
            return kakao
    if not local.region:
        local.source = "unresolved"
        local.confidence = 0.0
        local.warnings.append("지역을 명확히 찾지 못했습니다. 추천을 위해 지역을 확인해야 합니다.")
    return local


def _load_aliases() -> dict[str, Any]:
    with ALIAS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _resolve_from_alias(query: str) -> LocationResolveResult:
    compact = _compact(query)
    aliases = _load_aliases()
    best: LocationResolveResult | None = None

    for region_key, config in aliases.items():
        canonical = config.get("canonical_region", region_key)
        region_hit = any(_compact(alias) in compact for alias in config.get("aliases", []))
        for area, area_aliases in config.get("areas", {}).items():
            area_hit_alias = next((alias for alias in area_aliases if _compact(alias) in compact), None)
            if not area_hit_alias:
                continue
            city = config.get("cities", {}).get(area) or config.get("city") or (area if canonical in {"경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남"} else canonical)
            coords = config.get("coordinates", {}).get(area) or [None, None]
            candidate = LocationResolveResult(
                raw_location=f"{canonical} {area}",
                region=city if canonical == "전북" and city == "전주" else canonical,
                city=city,
                district=config.get("districts", {}).get(area),
                area=area,
                landmark=area if area.endswith("역") or area in {"전북대", "홍대", "해운대", "애월"} else None,
                latitude=coords[0],
                longitude=coords[1],
                confidence=0.92 if region_hit else 0.86,
                source="local_alias",
            )
            is_more_specific = bool(best and best.area == best.city and candidate.area != candidate.city)
            if best is None or candidate.confidence > best.confidence or is_more_specific or len(area) > len(best.area or ""):
                best = candidate

        if region_hit and best is None:
            best = LocationResolveResult(
                raw_location=canonical,
                region=config.get("city") or canonical,
                city=config.get("city") or canonical,
                confidence=0.72,
                source="local_alias",
            )

    if best:
        return best
    return LocationResolveResult(warnings=["지역 alias에서 위치를 찾지 못했습니다."])


def _resolve_from_kakao(query: str, local: LocationResolveResult) -> LocationResolveResult | None:
    key = os.getenv("KAKAO_REST_API_KEY")
    if not key:
        return None
    search_query = local.raw_location or query
    try:
        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": search_query, "size": 1},
            timeout=4,
        )
        response.raise_for_status()
        docs = response.json().get("documents", [])
    except Exception as exc:
        local.warnings.append(f"Kakao Local 위치 해석 실패: {exc}")
        return None
    if not docs:
        return None
    doc = docs[0]
    address = f"{doc.get('address_name', '')} {doc.get('road_address_name', '')}"
    if local.region and local.region not in address and (local.city or "") not in address:
        return None
    return LocationResolveResult(
        raw_location=local.raw_location or doc.get("place_name"),
        region=local.region,
        city=local.city or local.region,
        district=local.district,
        area=local.area,
        landmark=local.landmark or doc.get("place_name"),
        latitude=_to_float(doc.get("y")),
        longitude=_to_float(doc.get("x")),
        confidence=0.95,
        source="kakao_local",
        warnings=local.warnings,
    )


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
