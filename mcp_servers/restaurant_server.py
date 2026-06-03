from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.services.geo_utils import format_distance, haversine_distance_km
from app.services.kakao_local_service import build_kakao_query, get_last_kakao_status, search_kakao_places

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None

DATA_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "restaurants.json"

FOOD_TYPE_KEYWORDS = {
    "양식": ["양식", "파스타", "피자", "스테이크", "리조또", "브런치"],
    "일식": ["일식", "초밥", "스시", "라멘", "우동", "돈카츠", "돈까스", "회"],
    "중식": ["중식", "짜장", "짬뽕", "마라탕", "탕수육"],
    "카페": ["카페", "커피", "디저트", "브런치", "케이크"],
    "한식": ["한식", "백반", "비빔밥", "국밥", "찌개", "전골", "삼계탕"],
    "국물": ["국물", "국밥", "찌개", "전골", "탕"],
    "분식": ["분식", "김밥", "떡볶이", "튀김"],
    "고기": ["고기", "삼겹살", "갈비", "구이", "불고기"],
}
SOUP_WORDS = ["국밥", "전골", "삼계탕", "찌개", "해장국", "순대국밥"]


def _load_restaurants() -> list[dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize(text: str | None) -> str:
    return (text or "").replace(" ", "").lower()


def _restaurant_text(item: dict[str, Any]) -> str:
    menus = item.get("menus") or []
    menu_text = " ".join(
        " ".join(str(menu.get(key, "")) for key in ["name", "description"]) for menu in menus if isinstance(menu, dict)
    )
    return " ".join(
        [
            item.get("id", ""),
            item.get("name", ""),
            item.get("region", ""),
            item.get("city", ""),
            item.get("district", ""),
            item.get("area", ""),
            item.get("category", ""),
            item.get("reason", ""),
            item.get("address", ""),
            item.get("road_address", ""),
            " ".join(item.get("menu", []) or []),
            " ".join(item.get("tags", []) or []),
            menu_text,
        ]
    )


def _contains(item: dict[str, Any], value: str | None) -> bool:
    return not value or _normalize(value) in _normalize(_restaurant_text(item))


def _region_matches(item: dict[str, Any], region: str, city: str | None) -> bool:
    item_region = item.get("region")
    item_city = item.get("city")
    if city:
        return item_city == city or item_region == city
    return item_region == region or item_city == region


def _district_matches(item: dict[str, Any], district: str | None) -> bool:
    return not district or district in _restaurant_text(item)


def _area_matches(item: dict[str, Any], area: str | None, landmark: str | None) -> bool:
    target = area or landmark
    if not target:
        return True
    haystack = _normalize(_restaurant_text(item))
    target_n = _normalize(target)
    if target_n in haystack:
        return True
    aliases = {
        "객사": ["전주객사", "객리단길"],
        "전북대": ["전북대학교", "덕진", "전북대앞"],
        "구암역": ["구암", "유성구"],
        "홍대": ["홍익대", "홍대입구"],
        "해운대": ["해운대구"],
        "애월": ["애월읍"],
        "수원": ["수원역"],
    }
    return any(_normalize(alias) in haystack for alias in aliases.get(target, []))


def _food_type_matches(item: dict[str, Any], food_type: str | None) -> bool:
    if not food_type:
        return True
    category = _normalize(item.get("category", ""))
    if _normalize(food_type) in category:
        return True
    haystack = _normalize(_restaurant_text(item))
    return any(_normalize(keyword) in haystack for keyword in FOOD_TYPE_KEYWORDS.get(food_type, [food_type]))


def _forbidden_by_keyword(item: dict[str, Any], menu_keyword: str | None, food_type: str | None) -> bool:
    haystack = _normalize(_restaurant_text(item))
    keyword = _normalize(menu_keyword)
    type_n = _normalize(food_type)
    if keyword == "파스타" or type_n == "양식":
        return any(_normalize(word) in haystack for word in SOUP_WORDS) and keyword not in haystack
    if keyword in {"초밥", "스시"}:
        return any(_normalize(word) in haystack for word in [*SOUP_WORDS, "파스타", "피자"])
    if type_n == "카페" or keyword == "디저트":
        return any(_normalize(word) in haystack for word in SOUP_WORDS)
    return False


def _price_max(price_range: str | None) -> int | None:
    numbers = [int(value) for value in re.findall(r"\d+", price_range or "")]
    return max(numbers) if numbers else None


def _distance_km(item: dict[str, Any], latitude: float | None, longitude: float | None) -> float | None:
    if latitude is None or longitude is None or item.get("latitude") is None or item.get("longitude") is None:
        return None
    try:
        return haversine_distance_km(float(latitude), float(longitude), float(item["latitude"]), float(item["longitude"]))
    except (TypeError, ValueError):
        return None


def _sort_key(item: dict[str, Any], area: str | None, landmark: str | None, menu_keyword: str | None, max_price: int | None, latitude: float | None, longitude: float | None) -> tuple:
    area_score = 1 if _area_matches(item, area, landmark) else 0
    menu_score = 1 if _contains(item, menu_keyword) else 0
    price_score = 1
    if max_price is not None:
        seen = _price_max(item.get("price_range"))
        price_score = 1 if seen is not None and seen <= max_price else 0
    distance = _distance_km(item, latitude, longitude)
    distance_score = 9999 if distance is None else -distance
    return (
        area_score,
        menu_score,
        price_score,
        1 if item.get("source") in {"kakao_api", "google_places"} else 0,
        distance_score,
        float(item.get("rating", 0) or 0),
        int(item.get("review_count", 0) or 0),
    )


def search_restaurants(
    region: str,
    city: str | None = None,
    district: str | None = None,
    area: str | None = None,
    landmark: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    food_type: str | None = None,
    menu_keyword: str | None = None,
    preference: str | None = None,
    max_price: int | None = None,
    min_rating: float | None = None,
    min_review_count: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    requested_region = (region or "").strip() or "전주"
    warnings: list[str] = []
    relaxed_fields: set[str] = set()

    query = build_kakao_query(requested_region, city, district, area or landmark, food_type, menu_keyword)
    api_items = search_kakao_places(
        query=query,
        region=requested_region,
        city=city,
        district=district,
        area=area or landmark,
        latitude=latitude,
        longitude=longitude,
        food_type=food_type,
        menu_keyword=menu_keyword,
        size=limit,
    )
    api_status = get_last_kakao_status()

    all_items = [*api_items, *_load_restaurants()]
    region_items = [item for item in all_items if _region_matches(item, requested_region, city)]
    if not region_items:
        return [
            {
                "error": "region_not_found",
                "message": f"{requested_region} 지역 후보가 없습니다. 다른 지역으로 대체하지 않았습니다.",
                "fallback_strategy": "지역명을 확인하거나 실제 장소 API 키를 설정한 뒤 다시 검색합니다.",
                "user_message": "요청 지역의 샘플/실제 후보가 없어 추천을 만들 수 없습니다.",
                "not_done": "다른 지역 후보로 임의 대체하지 않음",
                "external_api": api_status,
                "requested_region": requested_region,
                "requested_city": city,
            }
        ]

    if not api_items:
        warnings.append("외부 장소 API 실패 또는 미설정으로 fallback_sample 데이터셋을 사용했습니다.")

    def filter_items(
        *,
        use_district: bool,
        use_area: bool,
        use_menu: bool,
        use_food_type: bool,
        use_price: bool,
        rating_floor: float | None,
        review_floor: int | None,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for item in region_items:
            if use_district and not _district_matches(item, district):
                continue
            if use_area and not _area_matches(item, area, landmark):
                continue
            if use_menu and menu_keyword and not _contains(item, menu_keyword):
                continue
            if use_food_type and food_type and not _food_type_matches(item, food_type):
                continue
            if _forbidden_by_keyword(item, menu_keyword, food_type):
                continue
            if use_price and max_price is not None:
                seen = _price_max(item.get("price_range"))
                if seen is not None and seen > max_price:
                    continue
            if rating_floor is not None and float(item.get("rating", 0) or 0) < rating_floor:
                continue
            if review_floor is not None and int(item.get("review_count", 0) or 0) < review_floor:
                continue
            distance = _distance_km(item, latitude, longitude)
            if distance is not None:
                item = {**item, "distance_km": round(distance, 3), "distance": f"{area or landmark}에서 {format_distance(distance)}"}
            filtered.append(item)
        return filtered

    stages = [
        ("strict", {"use_district": True, "use_area": True, "use_menu": True, "use_food_type": True, "use_price": True, "rating_floor": min_rating, "review_floor": min_review_count}),
        ("relax_price_review", {"use_district": True, "use_area": True, "use_menu": True, "use_food_type": True, "use_price": False, "rating_floor": None, "review_floor": None}),
        ("relax_area", {"use_district": False, "use_area": False, "use_menu": True, "use_food_type": True, "use_price": False, "rating_floor": None, "review_floor": None}),
        ("relax_menu_to_food_type", {"use_district": False, "use_area": False, "use_menu": False, "use_food_type": True, "use_price": False, "rating_floor": None, "review_floor": None}),
    ]

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for stage_name, options in stages:
        stage_items = filter_items(**options)
        if stage_name != "strict" and stage_items:
            if stage_name == "relax_price_review":
                if max_price is not None:
                    relaxed_fields.add("price")
                if min_rating is not None:
                    relaxed_fields.add("rating")
                if min_review_count is not None:
                    relaxed_fields.add("review_count")
                warnings.append("가격/리뷰 조건만 완화했습니다. 지역, 세부 위치, 메뉴/음식 종류는 유지했습니다.")
            elif stage_name == "relax_area":
                if area or landmark or district:
                    relaxed_fields.add("area")
                warnings.append(f"{area or landmark} 근처 후보가 부족해 같은 {city or requested_region} 지역 안에서만 확장했습니다.")
            elif stage_name == "relax_menu_to_food_type":
                if menu_keyword:
                    relaxed_fields.add("menu_keyword")
                warnings.append(f"{menu_keyword} 후보가 부족해 같은 {city or requested_region} 지역의 {food_type} 후보까지만 확장했습니다.")
        for item in sorted(stage_items, key=lambda value: _sort_key(value, area, landmark, menu_keyword, max_price, latitude, longitude), reverse=True):
            item_id = item.get("id") or item.get("name")
            if item_id not in seen:
                results.append(item)
                seen.add(item_id)
        if len(results) >= limit or len(results) >= 3:
            break

    if not results:
        return [
            {
                "warning": "no_search_results",
                "legacy_warning": "not_enough_strict_candidates",
                "message": "요청 조건에 맞는 후보가 없습니다.",
                "relaxation_options": ["가격 조건 완화", "리뷰 수 조건 완화", "세부 위치 확장"],
                "not_done": "다른 지역 후보로 임의 대체하지 않음",
                "fallback_strategy": "지역과 메뉴/음식 종류는 유지하고 가격, 리뷰 수, 세부 위치 조건을 완화해 다시 시도할 수 있습니다.",
                "user_message": f"{requested_region} {area or landmark or ''} {menu_keyword or food_type or ''} 조건을 만족하는 후보가 부족합니다.",
                "external_api": api_status,
                "requested_region": requested_region,
                "requested_city": city,
                "requested_district": district,
                "requested_area": area,
                "requested_landmark": landmark,
                "requested_food_type": food_type,
                "requested_menu_keyword": menu_keyword,
            }
        ]

    sorted_items = sorted(results, key=lambda value: _sort_key(value, area, landmark, menu_keyword, max_price, latitude, longitude), reverse=True)[: max(1, limit)]
    if warnings:
        return [
            {
                "warning": "relaxed_conditions",
                "messages": list(dict.fromkeys(warnings)),
                "relaxed_fields": sorted(relaxed_fields),
                "not_done": "다른 지역 후보로 임의 대체하지 않음",
                "external_api": api_status,
                "fallback_used": api_status.get("fallback_used"),
                "requested_region": requested_region,
                "requested_city": city,
                "requested_district": district,
                "requested_area": area,
                "requested_landmark": landmark,
                "requested_food_type": food_type,
                "requested_menu_keyword": menu_keyword,
            },
            *sorted_items,
        ]
    return sorted_items


def get_restaurant_detail(restaurant_id: str) -> dict[str, Any]:
    for item in _load_restaurants():
        if item.get("id") == restaurant_id:
            return item
    return {"error": "restaurant_not_found", "restaurant_id": restaurant_id}


if FastMCP:
    mcp = FastMCP("Restaurant MCP Server")
    mcp.tool()(search_restaurants)
    mcp.tool()(get_restaurant_detail)


if __name__ == "__main__":
    if not FastMCP:
        print("mcp package is not installed. Run: pip install -r requirements.txt")
    else:
        mcp.run()
