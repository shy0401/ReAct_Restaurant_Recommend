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

DEFAULT_SUGGESTED_QUERIES = [
    "전주 객사 근처에서 가성비 좋은 맛집 3곳 추천해줘",
    "서울 홍대 근처 초밥 리뷰 좋은 곳 추천해줘",
    "대전 구암역 근처 파스타 맛집 추천해줘",
]

VAGUE_FOOD_KEYWORDS = ["아무거나", "맛있는 거", "맛있는거", "밥집", "맛집", "추천해줘", "추천"]


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
    needs_clarification = False
    clarification_reason: str | None = None
    error_code: str | None = None
    suggested_queries: list[str] = []

    if "근처" in text and not location.area and not location.landmark:
        warnings.append("근처 표현은 있었지만 세부 위치를 찾지 못해 지역 전체에서 검색합니다.")
    if not purpose and ("맛집" in text or "추천" in text):
        warnings.append("방문 목적이 명확하지 않아 일반 식사 추천으로 처리합니다.")
    if not location.region:
        needs_clarification = True
        error_code = "unknown_region"
        clarification_reason = "지역을 해석하지 못했습니다. 추천을 시작하려면 지역이나 세부 위치를 알려주세요."
        suggested_queries = DEFAULT_SUGGESTED_QUERIES
        warnings.append("지역이 확인되지 않아 실제 맛집 추천을 중단하고 지역 확인을 요청합니다.")
    elif _is_vague_food_request(text, food_type, menu_keyword):
        clarification_reason = "음식 종류가 모호해 평점, 거리, 가격 중심으로 추천합니다."
        warnings.append("음식 종류가 모호해 평점/거리/가격 중심으로 추천합니다. 한식, 파스타, 초밥, 카페처럼 음식 종류를 추가하면 정확도가 올라갑니다.")
        suggested_queries = [
            f"{location.area or location.city or location.region} 근처 파스타 가성비 좋은 곳 추천해줘",
            f"{location.area or location.city or location.region} 근처 초밥 리뷰 좋은 곳 추천해줘",
            f"{location.area or location.city or location.region} 근처 카페 디저트 추천해줘",
        ]
    if location.region and not any([food_type, menu_keyword, budget_level, min_rating, min_review_count, purpose, companion]):
        warnings.append("지역 외 조건이 부족해 평점과 거리 중심으로 추천합니다. 음식 종류, 가격대, 동행, 목적을 추가하면 더 정확합니다.")

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
        region=location.region or "미확인",
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
        needs_clarification=needs_clarification,
        clarification_reason=clarification_reason,
        error_code=error_code,
        suggested_queries=suggested_queries,
    )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _parse_food(text: str) -> tuple[str | None, str | None]:
    compact = _compact(text)
    for food_type, menu_keyword, keywords in FOOD_RULES:
        if any(keyword in compact for keyword in keywords):
            return food_type, menu_keyword
    return None, None


def _is_vague_food_request(text: str, food_type: str | None, menu_keyword: str | None) -> bool:
    if food_type or menu_keyword:
        return False
    compact = _compact(text)
    return any(_compact(keyword) in compact for keyword in VAGUE_FOOD_KEYWORDS)


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
