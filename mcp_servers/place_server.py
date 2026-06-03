from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from app.services.google_places_service import get_google_photos_for_place

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "app" / "data" / "restaurants.json"
CACHE_PATH = ROOT / "app" / "data" / "place_cache.json"
DEFAULT_PHOTO = "/placeholders/default-restaurant.jpg"

CATEGORY_PHOTOS = {
    "한식": "/placeholders/korean.jpg",
    "중식": "/placeholders/chinese.jpg",
    "일식": "/placeholders/japanese.jpg",
    "양식": "/placeholders/western.jpg",
    "분식": "/placeholders/snack.jpg",
    "카페": "/placeholders/cafe.jpg",
    "국물": "/placeholders/soup.jpg",
    "고기": "/placeholders/meat.jpg",
    "면": "/placeholders/noodle.jpg",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().isoformat()


def _load_restaurants() -> list[dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _read_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def _write_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def _cache_key(place_id: str | None, name: str | None, region: str | None, city: str | None = None, area: str | None = None) -> str:
    return ":".join(part for part in [region or "", city or "", area or "", place_id or name or ""] if part)


def _cache_get(key: str, *, region: str | None = None, city: str | None = None) -> dict[str, Any] | None:
    cache = _read_cache()
    cached = cache.get(key)
    if not cached:
        return None
    ttl_hours = int(os.getenv("PLACE_CACHE_TTL_HOURS", "24"))
    try:
        fetched_at = datetime.fromisoformat(cached["fetched_at"])
    except Exception:
        return None
    if _now() - fetched_at > timedelta(hours=ttl_hours):
        return None
    place = cached["place"]
    if region and place.get("region") and place.get("region") != region and place.get("city") != region:
        return None
    if city and place.get("city") and place.get("city") != city and place.get("region") != city:
        return None
    return place


def _cache_set(key: str, place: dict[str, Any]) -> None:
    cache = _read_cache()
    cache[key] = {"fetched_at": _iso_now(), "place": place}
    _write_cache(cache)


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _osm_url(latitude: Any, longitude: Any) -> str | None:
    lat = _to_float(latitude)
    lng = _to_float(longitude)
    if lat is None or lng is None:
        return None
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"


def _directions_url(latitude: Any, longitude: Any) -> str | None:
    lat = _to_float(latitude)
    lng = _to_float(longitude)
    if lat is None or lng is None:
        return None
    return f"https://www.openstreetmap.org/directions?from=&to={lat}%2C{lng}"


def _fallback_photo(category: str | None, tags: list[str] | None = None) -> str:
    tags = tags or []
    if "국물" in tags:
        return CATEGORY_PHOTOS["국물"]
    if "고기" in tags:
        return CATEGORY_PHOTOS["고기"]
    if "면" in tags:
        return CATEGORY_PHOTOS["면"]
    return CATEGORY_PHOTOS.get(category or "", DEFAULT_PHOTO)


def _photo_payload(url: str, alt: str, source: str = "fallback", is_fallback: bool | None = None) -> dict[str, Any]:
    fallback = source == "fallback" if is_fallback is None else is_fallback
    return {
        "url": url,
        "alt": alt,
        "source": source,
        "is_fallback": fallback,
        "attributions": [],
    }


def _menu_objects(restaurant: dict[str, Any]) -> list[dict[str, Any]]:
    menus = restaurant.get("menus") or []
    if menus:
        return menus
    simple = restaurant.get("menu") or []
    return [
        {
            "name": name,
            "price": "가격 정보 없음",
            "description": "추천 조건과 잘 맞는 대표 메뉴입니다.",
            "is_recommended": index == 0,
        }
        for index, name in enumerate(simple)
    ]


def _seed_photos(restaurant: dict[str, Any]) -> list[dict[str, Any]]:
    raw_photos = restaurant.get("photos") or []
    photos = []
    for photo in raw_photos:
        url = photo.get("url") or _fallback_photo(restaurant.get("category"), restaurant.get("tags"))
        source = photo.get("source") or ("fallback" if url.startswith("/placeholders/") else "seed")
        photos.append(
            {
                "url": url,
                "alt": photo.get("alt") or f"{restaurant.get('name', '맛집')} 대표 이미지",
                "source": source,
                "is_fallback": photo.get("is_fallback", url.startswith("/placeholders/") or source == "fallback"),
                "attributions": photo.get("attributions", []),
            }
        )
    if photos:
        return photos
    return [_photo_payload(_fallback_photo(restaurant.get("category"), restaurant.get("tags")), f"{restaurant.get('name', '맛집')} 기본 이미지")]


def _ensure_photo_status(place: dict[str, Any]) -> dict[str, Any]:
    photos = place.get("photos") or []
    normalized = []
    for photo in photos:
        url = photo.get("url") or DEFAULT_PHOTO
        source = photo.get("source") or ("fallback" if url.startswith("/placeholders/") else "seed")
        normalized.append(
            {
                "url": url,
                "alt": photo.get("alt") or f"{place.get('name', '맛집')} 대표 이미지",
                "source": source,
                "is_fallback": photo.get("is_fallback", url.startswith("/placeholders/") or source == "fallback"),
                "attributions": photo.get("attributions", []),
            }
        )
    if not normalized:
        normalized = [_photo_payload(_fallback_photo(place.get("category"), place.get("tags")), f"{place.get('name', '맛집')} 기본 이미지")]
    place["photos"] = normalized
    return place


def _normalize_fallback(restaurant: dict[str, Any]) -> dict[str, Any]:
    latitude = _to_float(restaurant.get("latitude"))
    longitude = _to_float(restaurant.get("longitude"))
    photos = _seed_photos(restaurant)
    fallback_messages = []
    if not restaurant.get("photos") or all(photo.get("is_fallback", True) for photo in photos):
        fallback_messages.append("실제 음식점 사진 API 키가 없거나 사진 결과가 없어 기본 이미지를 표시합니다.")
    if not restaurant.get("menus"):
        fallback_messages.append("메뉴 정보가 부족해 대표 메뉴 기반으로 표시합니다.")
    if latitude is None or longitude is None:
        fallback_messages.append("지도 좌표가 없어 주소 링크만 제공합니다.")

    return {
        "id": restaurant.get("id"),
        "name": restaurant.get("name"),
        "category": restaurant.get("category"),
        "region": restaurant.get("region"),
        "city": restaurant.get("city"),
        "district": restaurant.get("district"),
        "area": restaurant.get("area"),
        "address": restaurant.get("address"),
        "road_address": restaurant.get("road_address") or restaurant.get("address"),
        "phone": restaurant.get("phone") or "전화번호 정보 없음",
        "rating": restaurant.get("rating"),
        "review_count": restaurant.get("review_count", 0),
        "price_range": restaurant.get("price_range"),
        "opening_hours": restaurant.get("opening_hours") or "영업시간 정보 없음",
        "latitude": latitude,
        "longitude": longitude,
        "distance": restaurant.get("distance") or "거리 정보 없음",
        "place_url": restaurant.get("place_url") or "",
        "map_url": restaurant.get("map_url") or _osm_url(latitude, longitude),
        "static_map_url": None,
        "menus": _menu_objects(restaurant),
        "photos": photos,
        "tags": restaurant.get("tags", []),
        "source": restaurant.get("source") or "fallback_sample",
        "fallback_messages": fallback_messages,
    }


def _find_fallback(place_id: str | None = None, name: str | None = None, region: str | None = None) -> dict[str, Any] | None:
    for item in _load_restaurants():
        if place_id and item.get("id") == place_id:
            return _normalize_fallback(item)
        if name and item.get("name") == name and (not region or item.get("region") == region):
            return _normalize_fallback(item)
    return None


def _strip_html(value: str | None) -> str:
    return re.sub(r"<[^>]+>", "", value or "").replace("&amp;", "&")


def _kakao_search(region: str, keyword: str, category: str | None = None) -> list[dict[str, Any]]:
    key = os.getenv("KAKAO_REST_API_KEY")
    if not key:
        return []
    try:
        response = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": f"{region} {keyword}".strip(), "category_group_code": "FD6", "size": 5},
            timeout=5,
        )
        response.raise_for_status()
        documents = response.json().get("documents", [])
    except Exception:
        return []

    results = []
    for doc in documents:
        latitude = _to_float(doc.get("y"))
        longitude = _to_float(doc.get("x"))
        name = doc.get("place_name")
        results.append(
            {
                "id": f"kakao_{doc.get('id')}",
                "name": name,
                "category": category or doc.get("category_name"),
                "region": region,
                "address": doc.get("address_name"),
                "road_address": doc.get("road_address_name") or doc.get("address_name"),
                "phone": doc.get("phone") or "전화번호 정보 없음",
                "rating": None,
                "review_count": 0,
                "price_range": None,
                "opening_hours": "영업시간 정보 없음",
                "latitude": latitude,
                "longitude": longitude,
                "distance": f"{int(doc['distance']) / 1000:.1f}km" if doc.get("distance") else "거리 정보 없음",
                "place_url": doc.get("place_url"),
                "map_url": doc.get("place_url") or _osm_url(latitude, longitude),
                "static_map_url": None,
                "menus": [],
                "photos": [_photo_payload(_fallback_photo(category), f"{name} 기본 이미지")],
                "tags": [category] if category else [],
                "source": "kakao_api",
                "fallback_messages": ["Kakao Local API는 실제 음식점 사진과 메뉴를 제공하지 않아 fallback 이미지를 함께 사용합니다."],
            }
        )
    return results


def _naver_search(region: str, keyword: str, category: str | None = None) -> list[dict[str, Any]]:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return []
    try:
        response = requests.get(
            "https://openapi.naver.com/v1/search/local.json",
            headers={"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret},
            params={"query": f"{region} {keyword}".strip(), "display": 5},
            timeout=5,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception:
        return []

    results = []
    for item in items:
        name = _strip_html(item.get("title"))
        results.append(
            {
                "id": f"naver_{item.get('mapx', '')}_{item.get('mapy', '')}_{name}",
                "name": name,
                "category": category or _strip_html(item.get("category")),
                "region": region,
                "address": item.get("address") or item.get("roadAddress"),
                "road_address": item.get("roadAddress") or item.get("address"),
                "phone": item.get("telephone") or "전화번호 정보 없음",
                "rating": None,
                "review_count": 0,
                "price_range": None,
                "opening_hours": "영업시간 정보 없음",
                "latitude": None,
                "longitude": None,
                "distance": "거리 정보 없음",
                "place_url": item.get("link") or "",
                "map_url": item.get("link") or "",
                "static_map_url": None,
                "menus": [],
                "photos": [_photo_payload(_fallback_photo(category), f"{name} 기본 이미지")],
                "tags": [category] if category else [],
                "source": "naver_api",
                "fallback_messages": ["Naver Local Search API는 사진과 메뉴를 안정적으로 제공하지 않아 fallback 이미지를 함께 사용합니다."],
            }
        )
    return results


def _google_search(region: str, keyword: str, category: str | None = None) -> list[dict[str, Any]]:
    key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not key:
        return []
    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": f"{region} {keyword}".strip(), "key": key, "language": "ko"},
            timeout=5,
        )
        response.raise_for_status()
        items = response.json().get("results", [])
    except Exception:
        return []

    results = []
    for item in items[:5]:
        location = item.get("geometry", {}).get("location", {})
        latitude = _to_float(location.get("lat"))
        longitude = _to_float(location.get("lng"))
        name = item.get("name")
        photos = []
        for photo in (item.get("photos") or [])[:5]:
            photos.append(
                {
                    "url": f"{os.getenv('BACKEND_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/places/photo?photo_reference={photo.get('photo_reference')}&max_width=800",
                    "alt": f"{name} Google Places 사진",
                    "source": "google_places",
                    "is_fallback": False,
                    "attributions": photo.get("html_attributions") or [],
                }
            )
        results.append(
            {
                "id": f"google_{item.get('place_id')}",
                "name": name,
                "category": category or "음식점",
                "region": region,
                "address": item.get("formatted_address"),
                "road_address": item.get("formatted_address"),
                "phone": "전화번호 정보 없음",
                "rating": item.get("rating"),
                "review_count": item.get("user_ratings_total", 0),
                "price_range": None,
                "opening_hours": "영업시간 정보 없음",
                "latitude": latitude,
                "longitude": longitude,
                "distance": "거리 정보 없음",
                "place_url": "",
                "map_url": _osm_url(latitude, longitude),
                "static_map_url": None,
                "menus": [],
                "photos": photos or [_photo_payload(_fallback_photo(category), f"{name} 기본 이미지")],
                "tags": [category] if category else [],
                "source": "google_api",
                "fallback_messages": [] if photos else ["Google Places 사진 결과가 없어 기본 이미지를 표시합니다."],
            }
        )
    return results


def _attach_google_photos(place: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("USE_REAL_PLACE_API", "false").lower() != "true":
        return _ensure_photo_status(place)
    if not os.getenv("GOOGLE_PLACES_API_KEY"):
        place = _ensure_photo_status(place)
        if all(photo.get("is_fallback", True) for photo in place.get("photos", [])):
            place.setdefault("fallback_messages", []).append("Google Places API 키가 없어 실제 사진 대신 기본 이미지를 표시합니다.")
        return place
    photos = get_google_photos_for_place(place.get("name", ""), place.get("region", ""), place.get("address"))
    if photos:
        place["photos"] = photos
        place["fallback_messages"] = [msg for msg in place.get("fallback_messages", []) if "사진" not in msg]
    else:
        place = _ensure_photo_status(place)
        if all(photo.get("is_fallback", True) for photo in place.get("photos", [])):
            place.setdefault("fallback_messages", []).append("실제 사진 API 결과 없음, 기본 이미지를 표시합니다.")
    return _ensure_photo_status(place)


def search_real_places(region: str, keyword: str, category: str | None = None) -> list[dict[str, Any]]:
    if os.getenv("USE_REAL_PLACE_API", "false").lower() == "true":
        real_results = _kakao_search(region, keyword, category) or _naver_search(region, keyword, category) or _google_search(region, keyword, category)
        if real_results:
            return [_attach_google_photos(place) for place in real_results]

    keyword_n = (keyword or "").replace(" ", "").lower()
    results = []
    for item in _load_restaurants():
        haystack = " ".join([item.get("name", ""), item.get("category", ""), " ".join(item.get("menu", []))]).replace(" ", "").lower()
        if item.get("region") == region and (not keyword_n or keyword_n in haystack):
            results.append(_normalize_fallback(item))
    return results


def get_place_detail(place_id: str, name: str | None = None, region: str | None = None) -> dict[str, Any]:
    key = _cache_key(place_id, name, region)
    cached = _cache_get(key, region=region)
    if cached:
        return _ensure_photo_status(cached)

    fallback = _find_fallback(place_id, name, region)
    place = fallback

    if os.getenv("USE_REAL_PLACE_API", "false").lower() == "true" and name and region:
        category = fallback.get("category") if fallback else None
        real_results = _kakao_search(region, name, category) or _naver_search(region, name, category) or _google_search(region, name, category)
        if real_results:
            place = {**(fallback or {}), **real_results[0]}
            place["menus"] = (fallback or {}).get("menus") or _menu_objects({})
            place["fallback_messages"] = list(
                dict.fromkeys(real_results[0].get("fallback_messages", []) + (fallback or {}).get("fallback_messages", []))
            )

    if not place:
        place = _normalize_fallback(
            {
                "id": place_id,
                "name": name or "상세 정보 없음",
                "region": region,
                "category": "기타",
                "menu": [],
                "tags": [],
                "address": "주소 정보 없음",
                "source": "fallback",
            }
        )
        place["fallback_messages"].append("외부 장소 정보를 가져오지 못해 fallback 데이터를 사용합니다.")

    place = _attach_google_photos(place)
    _cache_set(key, place)
    return place


def get_place_photos(place_id: str, name: str, region: str) -> list[dict[str, Any]]:
    return get_place_detail(place_id, name, region).get("photos", [])


def get_place_menu(place_id: str, name: str, region: str) -> list[dict[str, Any]]:
    return get_place_detail(place_id, name, region).get("menus", [])


def get_static_map(latitude: float, longitude: float, name: str) -> dict[str, Any]:
    lat = _to_float(latitude)
    lng = _to_float(longitude)
    provider = "kakao" if os.getenv("MAP_PROVIDER", "leaflet").lower() == "kakao" else "leaflet"
    return {
        "name": name,
        "latitude": lat,
        "longitude": lng,
        "map_url": _osm_url(lat, lng),
        "directions_url": _directions_url(lat, lng),
        "provider": provider,
        "has_coordinates": lat is not None and lng is not None,
        "source": "openstreetmap_leaflet",
    }


if FastMCP:
    mcp = FastMCP("Place MCP Server")
    mcp.tool()(search_real_places)
    mcp.tool()(get_place_detail)
    mcp.tool()(get_place_photos)
    mcp.tool()(get_place_menu)
    mcp.tool()(get_static_map)


if __name__ == "__main__":
    if not FastMCP:
        print("mcp package is not installed. Run: pip install -r requirements.txt")
    else:
        mcp.run()
