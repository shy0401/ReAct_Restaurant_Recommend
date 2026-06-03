from __future__ import annotations

import os
from typing import Any

import requests


def search_kakao_places(
    *,
    query: str,
    region: str,
    city: str | None = None,
    district: str | None = None,
    area: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    food_type: str | None = None,
    menu_keyword: str | None = None,
    size: int = 10,
) -> list[dict[str, Any]]:
    key = os.getenv("KAKAO_REST_API_KEY")
    if not key or os.getenv("USE_REAL_PLACE_API", "false").lower() != "true":
        return []
    params: dict[str, Any] = {"query": query, "category_group_code": "FD6", "size": min(size, 15)}
    if latitude is not None and longitude is not None:
        params.update({"y": latitude, "x": longitude, "radius": 5000, "sort": "distance"})
    try:
        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params=params,
            timeout=5,
        )
        response.raise_for_status()
    except Exception:
        return []
    places = []
    for doc in response.json().get("documents", []):
        place = normalize_kakao_place(doc, region=region, city=city, food_type=food_type, menu_keyword=menu_keyword)
        if validate_place_region(place, requested_region=region, requested_city=city, requested_district=district, requested_area=area):
            places.append(place)
    return places


def build_kakao_query(region: str, city: str | None, district: str | None, area: str | None, food_type: str | None, menu_keyword: str | None) -> str:
    location = " ".join(part for part in [city or region, area or district] if part)
    target = menu_keyword or food_type or ""
    return f"{location} {target} 맛집".strip()


def normalize_kakao_place(doc: dict[str, Any], *, region: str, city: str | None, food_type: str | None, menu_keyword: str | None) -> dict[str, Any]:
    lat = _to_float(doc.get("y"))
    lng = _to_float(doc.get("x"))
    name = doc.get("place_name", "")
    category = food_type or doc.get("category_name") or "음식점"
    address = doc.get("address_name") or doc.get("road_address_name") or ""
    road_address = doc.get("road_address_name") or address
    tags = [token for token in [city, food_type, menu_keyword] if token]
    return {
        "id": f"kakao_{doc.get('id')}",
        "name": name,
        "region": region,
        "city": city or region,
        "district": None,
        "area": None,
        "category": category,
        "menu": [menu_keyword] if menu_keyword else ([food_type] if food_type else []),
        "menus": [
            {
                "name": menu_keyword or food_type or "대표 메뉴 정보 없음",
                "price": "가격 정보 없음",
                "description": "Kakao Local API는 메뉴 가격을 제공하지 않아 검색 키워드 기반으로 표시합니다.",
                "is_recommended": True,
            }
        ],
        "tags": tags,
        "weather_match": ["맑음", "비", "흐림", "추움", "더움"],
        "price_range": "가격 정보 없음",
        "rating": 0,
        "review_count": 0,
        "address": address,
        "road_address": road_address,
        "latitude": lat,
        "longitude": lng,
        "phone": doc.get("phone") or "전화번호 정보 없음",
        "opening_hours": "영업시간 정보 없음",
        "distance": f"{int(doc['distance']) / 1000:.1f}km" if doc.get("distance") else "거리 정보 없음",
        "reason": f"{region} {menu_keyword or food_type or '맛집'} 검색 결과이며, Kakao Local API에서 주소와 좌표를 확인했습니다.",
        "photos": [{"url": "/placeholders/default-restaurant.jpg", "alt": f"{name} 기본 이미지", "source": "fallback", "is_fallback": True}],
        "map_url": doc.get("place_url") or _osm_url(lat, lng),
        "place_url": doc.get("place_url") or "",
        "source": "kakao_api",
    }


def validate_place_region(
    place: dict[str, Any],
    *,
    requested_region: str,
    requested_city: str | None = None,
    requested_district: str | None = None,
    requested_area: str | None = None,
) -> bool:
    haystack = " ".join([place.get("name", ""), place.get("address", ""), place.get("road_address", "")])
    if requested_city and requested_city not in haystack and requested_region not in haystack:
        return False
    if requested_region and requested_city is None and requested_region not in haystack:
        return False
    if requested_district and requested_district not in haystack:
        return False
    return True


def validate_place_food(place: dict[str, Any], *, food_type: str | None, menu_keyword: str | None) -> bool:
    text = " ".join([place.get("name", ""), place.get("category", ""), " ".join(place.get("menu", [])), " ".join(place.get("tags", []))])
    if menu_keyword and menu_keyword not in text:
        return False
    if food_type and food_type not in text:
        return False
    return True


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _osm_url(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=17/{latitude}/{longitude}"
