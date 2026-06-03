from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


FOOD_TYPE_KEYWORDS = {
    "양식": ["양식", "파스타", "피자", "스테이크", "리조또", "브런치"],
    "일식": ["일식", "초밥", "스시", "라멘", "우동", "돈카츠", "돈까스", "회"],
    "중식": ["중식", "짜장", "짬뽕", "마라탕", "탕수육"],
    "카페": ["카페", "커피", "디저트", "브런치", "케이크"],
    "한식": ["한식", "백반", "비빔밥", "국밥", "찌개", "전골", "삼계탕"],
    "국물": ["국물", "국밥", "찌개", "전골", "탕", "라멘", "우동"],
    "분식": ["분식", "김밥", "떡볶이", "튀김"],
    "고기": ["고기", "삼겹살", "갈비", "구이", "불고기"],
}

MENU_KEYWORD_TO_TYPE = {
    "파스타": "양식",
    "피자": "양식",
    "스테이크": "양식",
    "리조또": "양식",
    "초밥": "일식",
    "스시": "일식",
    "라멘": "일식",
    "우동": "일식",
    "돈카츠": "일식",
    "돈까스": "일식",
    "디저트": "카페",
}

SOUP_WORDS = ["국밥", "전골", "삼계탕", "찌개", "탕", "해장국", "순대국밥"]


def normalize(text: str | None) -> str:
    return (text or "").replace(" ", "").lower()


def split_preference(preference: str | None) -> list[str]:
    raw = (preference or "").replace("/", ",").replace("·", ",").replace(" ", ",")
    return [token.strip() for token in raw.split(",") if token.strip() and token.strip() not in {"음식", "메뉴"}]


def restaurant_text(restaurant: dict[str, Any]) -> str:
    menu_objects = restaurant.get("menus") or []
    menu_object_text = " ".join(
        " ".join(str(menu.get(key, "")) for key in ["name", "description"]) for menu in menu_objects if isinstance(menu, dict)
    )
    return " ".join(
        [
            str(restaurant.get("name", "")),
            str(restaurant.get("region", "")),
            str(restaurant.get("city", "")),
            str(restaurant.get("district", "")),
            str(restaurant.get("area", "")),
            str(restaurant.get("category", "")),
            str(restaurant.get("reason", "")),
            str(restaurant.get("address", "")),
            str(restaurant.get("road_address", "")),
            " ".join(restaurant.get("menu", []) or []),
            " ".join(restaurant.get("tags", []) or []),
            menu_object_text,
        ]
    )


def contains_keyword(restaurant: dict[str, Any], keyword: str | None) -> bool:
    return not keyword or normalize(keyword) in normalize(restaurant_text(restaurant))


def food_type_matches(restaurant: dict[str, Any], food_type: str | None) -> bool:
    if not food_type:
        return True
    haystack = normalize(restaurant_text(restaurant))
    category = normalize(str(restaurant.get("category", "")))
    if normalize(food_type) in category:
        return True
    return any(normalize(keyword) in haystack for keyword in FOOD_TYPE_KEYWORDS.get(food_type, [food_type]))


def region_matches(restaurant: dict[str, Any], region: str | None, city: str | None = None) -> bool:
    if not region:
        return True
    if city:
        return restaurant.get("city") == city or restaurant.get("region") == city
    return restaurant.get("region") == region or restaurant.get("city") == region


def is_similar_menu(menu: str, recent_meals: Iterable[str]) -> bool:
    menu_n = normalize(menu)
    if not menu_n:
        return False
    groups = [
        ["면", "라면", "우동", "파스타", "짬뽕", "짜장", "냉면", "칼국수", "국수"],
        ["치킨", "닭", "닭강정"],
        ["초밥", "스시", "회"],
        ["카페", "커피", "디저트"],
    ]
    for recent in recent_meals:
        recent_n = normalize(recent)
        if not recent_n or recent_n in {"입력없음", "없음"}:
            continue
        if recent_n in menu_n or menu_n in recent_n:
            return True
        for group in groups:
            if any(token in recent_n for token in group) and any(token in menu_n for token in group):
                return True
    return False


def restaurant_has_preference(restaurant: dict[str, Any], preference: str | None) -> bool:
    tokens = [normalize(token) for token in split_preference(preference)]
    if not tokens:
        return True
    haystack = normalize(restaurant_text(restaurant))
    soft_tokens = {"친구와방문", "친구", "저녁", "점심", "가성비", "리뷰좋은곳", "리뷰"}
    return any(token and (token in haystack or token in soft_tokens) for token in tokens)


def price_max(price_range: str | None) -> int | None:
    numbers = [int(value) for value in re.findall(r"\d+", price_range or "")]
    return max(numbers) if numbers else None


def area_matches(restaurant: dict[str, Any], area: str | None, landmark: str | None = None) -> bool:
    target = area or landmark
    if not target:
        return True
    target_n = normalize(target)
    haystack = normalize(restaurant_text(restaurant))
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
    return any(normalize(alias) in haystack for alias in aliases.get(target, []))


def is_forbidden_for_keyword(restaurant: dict[str, Any], menu_keyword: str | None, food_type: str | None = None) -> bool:
    haystack = normalize(restaurant_text(restaurant))
    keyword = normalize(menu_keyword)
    type_n = normalize(food_type)
    if keyword == "파스타" or type_n == "양식":
        return any(normalize(word) in haystack for word in SOUP_WORDS) and keyword not in haystack
    if keyword in {"초밥", "스시"}:
        return any(normalize(word) in haystack for word in [*SOUP_WORDS, "파스타", "피자"])
    if type_n == "카페" or keyword == "디저트":
        return any(normalize(word) in haystack for word in SOUP_WORDS)
    return False


def is_hard_mismatch(restaurant: dict[str, Any], request: Any) -> bool:
    region = getattr(request, "region", None)
    city = getattr(request, "city", None)
    food_type = getattr(request, "food_type", None)
    menu_keyword = getattr(request, "menu_keyword", None)
    if region and not region_matches(restaurant, region, city):
        return True
    if menu_keyword and not contains_keyword(restaurant, menu_keyword):
        return True
    if food_type and not food_type_matches(restaurant, food_type):
        return True
    if is_forbidden_for_keyword(restaurant, menu_keyword, food_type):
        return True
    return False


def score_restaurant(
    restaurant: dict,
    *,
    region: str,
    weather_condition: str,
    recent_meals: list[str],
    preference: str | None,
    city: str | None = None,
    landmark: str | None = None,
    max_price: int | None = None,
    min_rating: float | None = None,
    min_review_count: int | None = None,
    area: str | None = None,
    food_type: str | None = None,
    menu_keyword: str | None = None,
) -> float:
    score = 0.0
    score += 150 if region_matches(restaurant, region, city) else -1000
    score += 70 if area_matches(restaurant, area, landmark) else (-80 if area or landmark else 0)
    score += 90 if contains_keyword(restaurant, menu_keyword) else (-300 if menu_keyword else 0)
    score += 80 if food_type_matches(restaurant, food_type) else (-200 if food_type else 0)

    if max_price is not None:
        max_seen = price_max(restaurant.get("price_range"))
        score += 25 if max_seen is not None and max_seen <= max_price else -15
    score += float(restaurant.get("rating", 0) or 0) * 5
    score += min(int(restaurant.get("review_count", 0) or 0) / 10, 20)

    distance_km = restaurant.get("distance_km")
    if isinstance(distance_km, (int, float)):
        score += max(0, 20 - float(distance_km) * 4)
    if weather_condition in restaurant.get("weather_match", []):
        score += 10
    duplicate = any(is_similar_menu(menu, recent_meals) for menu in restaurant.get("menu", []))
    score += -30 if duplicate else 10
    if not restaurant_has_preference(restaurant, preference):
        score -= 5
    if min_rating is not None and float(restaurant.get("rating", 0) or 0) < min_rating:
        score -= 20
    if min_review_count is not None and int(restaurant.get("review_count", 0) or 0) < min_review_count:
        score -= 15
    if is_forbidden_for_keyword(restaurant, menu_keyword, food_type):
        score -= 500
    return round(score, 1)


def enrich_recommendation(
    restaurant: dict,
    *,
    score: float,
    weather_condition: str,
    recent_meals: list[str],
    preference: str,
    max_price: int | None = None,
    min_rating: float | None = None,
    min_review_count: int | None = None,
    purpose: str | None = None,
    companion: str | None = None,
) -> dict:
    duplicate = any(is_similar_menu(menu, recent_meals) for menu in restaurant.get("menu", []))
    preference_ok = restaurant_has_preference(restaurant, preference)
    weather_ok = weather_condition in restaurant.get("weather_match", [])
    photos = restaurant.get("photos") or []
    thumbnail = photos[0] if photos else {}
    max_seen = price_max(restaurant.get("price_range"))

    if max_price is None:
        price_note = "별도 가격 제한 없이 추천했습니다."
    elif max_seen is not None and max_seen <= max_price:
        price_note = f"예상 가격대 {restaurant.get('price_range')}가 {max_price:,}원 조건에 대체로 맞습니다."
    else:
        price_note = f"일부 메뉴가 {max_price:,}원을 넘을 수 있어 점수에 보수적으로 반영했습니다."
    review_note = f"평점 {restaurant.get('rating')}점, 리뷰 {restaurant.get('review_count', 0)}개를 반영했습니다."
    purpose_note = ""
    if purpose or companion:
        purpose_note = f" {companion or '동행'}와 {purpose or '식사'}하기 좋은 분위기와 메뉴 구성을 함께 봤습니다."

    return {
        **restaurant,
        "place_id": restaurant.get("id"),
        "thumbnail_url": thumbnail.get("url"),
        "thumbnail_source": thumbnail.get("source", "fallback") if thumbnail else "fallback",
        "thumbnail_is_fallback": thumbnail.get("is_fallback", True) if thumbnail else True,
        "quick_view_available": True,
        "score": score,
        "weather_relation": (
            f"{weather_condition} 날씨와 어울리는 태그({', '.join(restaurant.get('tags', []))})가 있습니다."
            if weather_ok
            else f"{weather_condition} 날씨는 보조 조건으로만 반영했고, 명시한 메뉴/지역 조건을 우선했습니다."
        ),
        "recent_menu_relation": (
            "어제/오늘 먹은 메뉴와 직접 겹치지 않아 중복감을 줄였습니다."
            if not duplicate
            else "최근 먹은 메뉴와 일부 비슷해 감점했지만 다른 강한 조건을 확인했습니다."
        ),
        "preference_relation": (
            f"입력 선호도({preference})가 카테고리, 메뉴, 태그, 방문 목적과 맞습니다.{purpose_note}"
            if preference_ok
            else f"입력 선호도({preference})와 직접 일치하지 않는 요소가 있어 감점했습니다.{purpose_note}"
        ),
        "reason": f"{restaurant.get('reason', '요청 조건에 맞는 지역 맛집입니다.')} {price_note} {review_note}",
    }
