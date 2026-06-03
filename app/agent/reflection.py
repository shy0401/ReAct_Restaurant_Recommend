from __future__ import annotations

from app.agent.schemas import ReflectionResult
from app.services.scoring import (
    area_matches,
    contains_keyword,
    food_type_matches,
    is_forbidden_for_keyword,
    is_similar_menu,
    price_max,
    region_matches,
    restaurant_has_preference,
)


def reflection_check(
    recommendations: list[dict],
    *,
    region: str,
    weather_condition: str,
    recent_meals: list[str],
    preference: str,
    city: str | None = None,
    district: str | None = None,
    landmark: str | None = None,
    max_price: int | None = None,
    min_rating: float | None = None,
    min_review_count: int | None = None,
    area: str | None = None,
    food_type: str | None = None,
    menu_keyword: str | None = None,
    purpose: str | None = None,
    companion: str | None = None,
) -> ReflectionResult:
    issues: list[str] = []
    checked_items: list[str] = [
        "지역 일치 확인",
        "도시 일치 확인",
        "구/군 조건 확인",
        "세부 위치/랜드마크 조건 확인",
        "음식 종류 일치 확인",
        "메뉴 키워드 일치 확인",
        "가격 조건 확인",
        "평점/리뷰 조건 확인",
        "날씨는 보조 조건으로만 확인",
        "최근 먹은 메뉴 중복 여부 확인",
        "지도 좌표 존재 여부 확인",
        "대표 메뉴 정보 확인",
        "사진 source 명확성 확인",
    ]
    if max_price is not None:
        checked_items.append(f"가격 상한 {max_price:,}원 이하 여부 확인")
    if min_rating is not None:
        checked_items.append(f"평점 {min_rating}점 이상 여부 확인")
    if min_review_count is not None:
        checked_items.append(f"리뷰 수 {min_review_count}개 이상 여부 확인")
    if companion:
        checked_items.append(f"{companion} 동행 조건 확인")
    if purpose:
        checked_items.append(f"{purpose} 방문 목적 확인")
    score = 10
    critical_issues = 0

    if len(recommendations) < 3:
        issues.append("추천 결과가 3개 미만입니다. 단, 다른 지역 후보로 채우지 않았습니다.")
        score -= 1

    area_match_count = sum(1 for item in recommendations if area_matches(item, area, landmark)) if area or landmark else len(recommendations)

    for item in recommendations:
        name = item.get("name", "이름 없는 후보")
        if not region_matches(item, region, city):
            issues.append(f"{name}: 요청 지역/도시({region}/{city or '-'})와 다릅니다.")
            score -= 5
            critical_issues += 1
        if district and district not in " ".join([item.get("district", ""), item.get("address", ""), item.get("road_address", "")]):
            issues.append(f"{name}: 요청 구/군({district}) 반영이 약합니다.")
            score -= 1
        if (area or landmark) and not area_matches(item, area, landmark):
            issues.append(f"{name}: 세부 위치/랜드마크({area or landmark})와 직접 일치하지 않아 완화 후보입니다.")
            score -= 1
        if food_type and not food_type_matches(item, food_type):
            issues.append(f"{name}: 요청 음식 종류({food_type})와 맞지 않습니다.")
            score -= 4
            critical_issues += 1
        if menu_keyword and not contains_keyword(item, menu_keyword):
            issues.append(f"{name}: 요청 메뉴({menu_keyword})가 메뉴/태그/설명에 없습니다.")
            score -= 5
            critical_issues += 1
        if is_forbidden_for_keyword(item, menu_keyword, food_type):
            issues.append(f"{name}: 요청 메뉴/음식 종류와 충돌하는 후보입니다.")
            score -= 5
            critical_issues += 1
        if any(is_similar_menu(menu, recent_meals) for menu in item.get("menu", [])):
            issues.append(f"{name}: 대표 메뉴가 최근 먹은 메뉴와 유사합니다.")
            score -= 2
        if not restaurant_has_preference(item, preference):
            issues.append(f"{name}: 선호도({preference}) 반영이 약합니다.")
            score -= 1
        if max_price is not None:
            item_max_price = price_max(item.get("price_range"))
            if item_max_price is not None and item_max_price > max_price:
                issues.append(f"{name}: 예상 가격대가 {max_price:,}원 조건을 일부 초과합니다.")
                score -= 1
        if min_rating is not None and float(item.get("rating", 0) or 0) < min_rating:
            issues.append(f"{name}: 평점이 {min_rating}점 기준보다 낮습니다.")
            score -= 1
        if min_review_count is not None and int(item.get("review_count", 0) or 0) < min_review_count:
            issues.append(f"{name}: 리뷰 수가 {min_review_count}개 기준보다 적습니다.")
            score -= 1
        if companion == "친구":
            tags = " ".join(item.get("tags", []))
            if "혼밥" in tags and not any(tag in tags for tag in ["친구", "저녁", "분위기", "데이트", "고기"]):
                issues.append(f"{name}: 친구와 방문하기에는 혼밥 성격이 강합니다.")
                score -= 1
            elif not any(token in " ".join([tags, item.get("reason", ""), item.get("preference_relation", "")]) for token in ["친구", "모임", "분위기"]):
                issues.append(f"{name}: 친구와 방문 조건 설명이 약합니다.")
                score -= 1
        if purpose == "저녁" and item.get("category") == "카페" and food_type != "카페":
            issues.append(f"{name}: 저녁 식사 목적에 비해 카페/디저트 성격이 강합니다.")
            score -= 1
        elif purpose == "저녁" and "저녁" not in " ".join([item.get("reason", ""), " ".join(item.get("tags", [])), item.get("preference_relation", "")]):
            issues.append(f"{name}: 저녁 목적 설명이 약합니다.")
            score -= 1
        if weather_condition not in item.get("weather_match", []):
            checked_items.append(f"{name}: 날씨({weather_condition})는 보조 조건으로만 확인")
            if not food_type and not menu_keyword:
                issues.append(f"{name}: 명시 메뉴/음식 종류가 없는 요청에서 현재 날씨({weather_condition})와의 직접 매칭이 약합니다.")
                score -= 1
        if not item.get("address"):
            issues.append(f"{name}: 주소 정보가 부족합니다.")
            score -= 1
        if item.get("latitude") is None or item.get("longitude") is None:
            issues.append(f"{name}: 지도 좌표가 부족합니다.")
            score -= 1
        if not item.get("menus") and not item.get("menu"):
            issues.append(f"{name}: 메뉴 정보가 부족합니다.")
            score -= 1
        if not item.get("photos") and not item.get("thumbnail_url"):
            issues.append(f"{name}: 사진 또는 fallback 이미지가 부족합니다.")
            score -= 1
        if item.get("thumbnail_is_fallback") is True or any(photo.get("is_fallback") for photo in item.get("photos", [])):
            checked_items.append("실제 사진 부재 시 fallback 안내 확인")
        if not item.get("source"):
            issues.append(f"{name}: 데이터 출처가 표시되지 않았습니다.")
            score -= 1

    if (area or landmark) and area_match_count >= min(2, len(recommendations)):
        checked_items.append(f"최종 추천 중 {area_match_count}개가 {area or landmark} 권역 조건을 충족")
        score = max(score, 7)
    if menu_keyword and all(contains_keyword(item, menu_keyword) for item in recommendations):
        checked_items.append(f"모든 최종 후보가 메뉴 키워드({menu_keyword})를 포함")
    if food_type and all(food_type_matches(item, food_type) for item in recommendations):
        checked_items.append(f"모든 최종 후보가 음식 종류({food_type})와 일치")
    if recommendations and all(region_matches(item, region, city) for item in recommendations):
        checked_items.append("모든 최종 후보가 요청 지역/도시와 일치")

    score = max(0, min(10, score))
    approved = score >= 7 and critical_issues == 0
    if approved:
        instruction = "명시된 지역, 위치, 메뉴/음식 종류 조건을 우선 만족하므로 현재 추천을 승인합니다."
        summary = f"Reflection 점수 {score}/10: 전국 지역/도시, 위치, 메뉴/음식 종류, 가격, 리뷰, 지도/사진 정보를 검토했습니다."
        final_changes = [
            "날씨는 보조 설명으로만 반영하고 명시 메뉴/음식 종류를 우선했습니다.",
            "지역/도시 또는 메뉴 하드 미스매치 후보를 최종 추천에서 제거했습니다.",
            f"세부 위치 조건은 최종 {area_match_count}개 후보에서 확인했습니다." if area or landmark else "세부 위치 조건은 별도 지정되지 않았습니다.",
        ]
    else:
        instruction = "critical issue가 남아 있으므로 지역/도시/메뉴/음식 종류 불일치 후보를 제거하고, 부족하면 부족 안내를 출력해야 합니다."
        summary = f"Reflection 점수 {score}/10: {len(issues)}개 개선점을 발견했습니다."
        final_changes = [
            "지역 불일치, 도시 불일치, 메뉴 키워드 불일치, 음식 종류 불일치 후보를 제거해야 합니다.",
            "부족한 개수는 다른 지역 후보로 채우지 말고 조건 부족으로 안내합니다.",
        ]

    return ReflectionResult(
        approved=approved,
        score=score,
        issues=issues,
        checked_items=list(dict.fromkeys(checked_items)),
        improvement_instruction=instruction,
        summary=summary,
        final_changes=final_changes,
    )
