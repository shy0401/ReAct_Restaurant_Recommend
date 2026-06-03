from __future__ import annotations

import re

from app.agent.schemas import ParsedRecommendationConditions
from app.services.location_resolver import resolve_location


FOOD_RULES = [
    ("양식", "파스타", ["파스타"]),
    ("양식", "피자", ["피자"]),
    ("양식", "스테이크", ["스테이크"]),
    ("양식", "리조또", ["리조또"]),
    ("양식", None, ["양식", "브런치"]),
    ("일식", "초밥", ["초밥", "스시"]),
    ("일식", "라멘", ["라멘"]),
    ("일식", "우동", ["우동"]),
    ("일식", "돈카츠", ["돈카츠", "돈까스"]),
    ("일식", None, ["일식", "회"]),
    ("중식", "짬뽕", ["짬뽕"]),
    ("중식", "짜장", ["짜장", "짜장면"]),
    ("중식", "마라탕", ["마라탕"]),
    ("중식", "탕수육", ["탕수육"]),
    ("중식", None, ["중식", "중국집"]),
    ("카페", "디저트", ["디저트"]),
    ("카페", None, ["카페", "커피"]),
    ("분식", None, ["분식", "김밥", "떡볶이"]),
    ("고기", None, ["고기", "삼겹살", "갈비", "구이"]),
    ("한식", "국밥", ["국밥"]),
    ("한식", "찌개", ["찌개"]),
    ("한식", "전골", ["전골"]),
    ("한식", "백반", ["백반"]),
    ("국물", None, ["국물", "탕"]),
    ("한식", None, ["한식"]),
]


def parse_recommendation_query(query: str) -> ParsedRecommendationConditions:
    text = (query or "").strip()
    location = resolve_location(text)
    food_type, menu_keyword = _parse_food(text)
    purpose = _parse_purpose(text)
    companion = _parse_companion(text)
    budget_level, max_price = _parse_budget(text)
    min_rating, min_review_count = _parse_review_condition(text)
    top_k = _parse_top_k(text)
    warnings = list(location.warnings)

    if "근처" in text and not location.area and not location.landmark:
        warnings.append("근처 표현은 있었지만 세부 위치를 찾지 못해 지역 전체에서 검색합니다.")
    if not purpose and ("맛집" in text or "추천" in text):
        warnings.append("방문 목적이 명확하지 않아 일반 식사 추천으로 처리합니다.")

    preference_parts: list[str] = []
    if food_type:
        preference_parts.append(food_type)
    if menu_keyword:
        preference_parts.append(menu_keyword)
    if companion:
        preference_parts.append(f"{companion}와 방문")
    if purpose:
        preference_parts.append(purpose)
    if budget_level == "budget":
        preference_parts.append("가성비")
    if min_rating:
        preference_parts.append("리뷰 좋은 곳")
    if not preference_parts:
        preference_parts.append("지역 맛집")

    return ParsedRecommendationConditions(
        region=location.region or "전주",
        city=location.city,
        district=location.district,
        area=location.area,
        landmark=location.landmark,
        latitude=location.latitude,
        longitude=location.longitude,
        location_source=location.source,
        location_confidence=location.confidence,
        food_type=food_type,
        menu_keyword=menu_keyword,
        preference=", ".join(dict.fromkeys(preference_parts)),
        purpose=purpose,
        companion=companion,
        budget_level=budget_level,
        max_price=max_price,
        min_rating=min_rating,
        min_review_count=min_review_count,
        top_k=top_k,
        warnings=warnings,
    )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _parse_food(text: str) -> tuple[str | None, str | None]:
    compact = _compact(text)
    for food_type, menu_keyword, keywords in FOOD_RULES:
        if any(keyword in compact for keyword in keywords):
            return food_type, menu_keyword
    return None, None


def _parse_purpose(text: str) -> str | None:
    if "저녁" in text or "저녁먹" in text:
        return "저녁"
    if "점심" in text:
        return "점심"
    if "데이트" in text:
        return "데이트"
    if "회식" in text:
        return "회식"
    return None


def _parse_companion(text: str) -> str | None:
    if "친구" in text:
        return "친구"
    if "가족" in text:
        return "가족"
    if "혼자" in text or "혼밥" in text:
        return "혼밥"
    if "연인" in text or "데이트" in text:
        return "연인"
    return None


def _parse_budget(text: str) -> tuple[str | None, int | None]:
    if any(keyword in text for keyword in ["너무 비싸지", "저렴", "가성비", "부담 없는", "부담없는", "가격 괜찮"]):
        return "budget", 15000
    match = re.search(r"(\d+)\s*(?:만원|천원|원)\s*(?:이하|안쪽|미만)", text)
    if match:
        value = int(match.group(1))
        unit = match.group(0)
        if "만원" in unit:
            value *= 10000
        elif "천원" in unit:
            value *= 1000
        return "custom", value
    return None, None


def _parse_review_condition(text: str) -> tuple[float | None, int | None]:
    if any(keyword in text for keyword in ["리뷰 좋은", "리뷰가 좋은", "평점 좋은", "후기 좋은", "후기 많은"]):
        return 4.0, 50
    return None, None


def _parse_top_k(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:곳|개|군데|식당)", text)
    if not match:
        return 3
    return max(1, min(10, int(match.group(1))))
