from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ASSIGNMENT_QUERY = "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."


def _run(query: str) -> dict:
    response = client.post(
        "/agent/run",
        json={"query": query, "yesterday_menu": "입력 없음", "today_menu": "입력 없음", "weather": None},
    )
    assert response.status_code == 200
    return response.json()


def _haystack(item: dict) -> str:
    return " ".join(
        [
            item.get("name", ""),
            item.get("address", ""),
            item.get("road_address", ""),
            item.get("category", ""),
            item.get("reason", ""),
            " ".join(item.get("menu", [])),
            " ".join(item.get("tags", [])),
        ]
    )


def _quality_mentions(item: dict) -> int:
    text = " ".join([item.get("reason", ""), item.get("preference_relation", ""), " ".join(item.get("tags", []))])
    groups = [
        ["친구", "모임"],
        ["저녁", "디너"],
        ["가격", "가성비", "15,000", "15000"],
        ["리뷰", "평점"],
    ]
    return sum(1 for group in groups if any(token in text for token in group))


def test_jbnu_pasta_request_preserves_menu_and_region_priority() -> None:
    body = _run("양식 파스타 먹고싶어\n전북대 근처 가성비 있는 곳")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "전주"
    assert parsed["area"] == "전북대"
    assert parsed["food_type"] == "양식"
    assert parsed["menu_keyword"] == "파스타"
    assert parsed["max_price"] == 15000

    recommendations = body["result"]["final_recommendations"]
    assert len(recommendations) >= 3
    forbidden = ["국밥", "전골", "삼계탕", "찌개", "해장국"]
    area_hits = 0
    for item in recommendations:
        text = _haystack(item)
        assert item["region"] == "전주"
        assert item["category"] == "양식" or "파스타" in text
        assert "파스타" in text
        assert not any(word in text for word in forbidden)
        if "전북대" in text or "덕진" in text or "전북대학교" in text:
            area_hits += 1
    assert area_hits >= 2

    restaurant_steps = [step for step in body["result"]["react_trace"] if step["action"] == "restaurant.search_restaurants"]
    assert restaurant_steps
    first_input = restaurant_steps[0]["action_input"]
    assert first_input["region"] == "전주"
    assert first_input["area"] == "전북대"
    assert first_input["food_type"] == "양식"
    assert first_input["menu_keyword"] == "파스타"
    assert body["result"]["reflection"]["approved"] is True


def test_hongdae_sushi_request_does_not_return_unrelated_food() -> None:
    body = _run("서울 홍대 초밥 리뷰 좋은 곳")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "서울"
    assert parsed["area"] == "홍대"
    assert parsed["food_type"] == "일식"
    assert parsed["menu_keyword"] == "초밥"
    forbidden = ["국밥", "전골", "삼계탕", "파스타"]
    for item in body["result"]["final_recommendations"]:
        text = _haystack(item)
        assert item["region"] == "서울"
        assert "초밥" in text
        assert not any(word in text for word in forbidden)


def test_haeundae_cafe_dessert_request_returns_cafe_candidates() -> None:
    body = _run("부산 해운대 카페 디저트")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "부산"
    assert parsed["area"] == "해운대"
    assert parsed["food_type"] == "카페"
    assert parsed["menu_keyword"] == "디저트"
    for item in body["result"]["final_recommendations"]:
        text = _haystack(item)
        assert item["region"] == "부산"
        assert item["category"] == "카페"
        assert "디저트" in text or "카페" in text


def test_gaeksa_friend_dinner_budget_scenario_keeps_area_and_reflection_score() -> None:
    body = _run("전주 객사 근처 친구랑 저녁 가성비 좋은 곳")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "전주"
    assert parsed["area"] == "객사"
    assert parsed["top_k"] == 3
    recommendations = body["result"]["final_recommendations"]
    assert len(recommendations) >= 3
    area_hits = sum(1 for item in recommendations if "객사" in _haystack(item) or "객리단길" in _haystack(item))
    assert area_hits >= 2
    assert all(item["region"] == "전주" for item in recommendations)
    assert body["result"]["reflection"]["score"] >= 7

    trace_text = body["submission_trace_text"]
    for token in ["Thought", "Action", "Observation", "Final Answer", "객사", "가격", "리뷰", "친구", "저녁"]:
        assert token in trace_text


def test_exact_assignment_scenario_quality_is_locked() -> None:
    body = _run(ASSIGNMENT_QUERY)
    parsed = body["parsed_conditions"]

    assert parsed["region"] == "전주"
    assert parsed["area"] == "객사"
    assert parsed["companion"] == "친구"
    assert parsed["purpose"] == "저녁"
    assert parsed["max_price"] == 15000
    assert parsed["min_rating"] >= 4.0
    assert parsed["min_review_count"] >= 50

    recommendations = body["result"]["final_recommendations"]
    assert len(recommendations) >= 3
    assert all(item["region"] == "전주" for item in recommendations)
    assert sum(1 for item in recommendations[:3] if "객사" in _haystack(item) or "객리단길" in _haystack(item)) >= 2

    for item in recommendations[:3]:
        for field in ["area", "district", "rating", "review_count", "price_range", "distance", "tags", "reason", "menus", "opening_hours", "latitude", "longitude"]:
            assert item.get(field), f"{item['name']} missing {field}"
        assert item["rating"] >= 4.0
        assert item["review_count"] >= 50
        assert _quality_mentions(item) >= 3
        assert "가격" in item["reason"] or "15,000" in item["reason"] or "15000" in item["reason"]
        assert "리뷰" in item["reason"] or "평점" in item["reason"]

    weather_step = next(step for step in body["result"]["react_trace"] if step["action"] == "weather.get_weather")
    assert weather_step["observation"]["condition"] == "비"
    restaurant_step = next(step for step in body["result"]["react_trace"] if step["action"] == "restaurant.search_restaurants")
    assert restaurant_step["action_input"]["food_type"] is None
    assert restaurant_step["action_input"]["region"] == "전주"
    assert restaurant_step["action_input"]["area"] == "객사"

    actions = [step["action"] for step in body["result"]["react_trace"]]
    assert "reflection.check" in actions
    assert "agent.finalize" in actions
    assert body["result"]["reflection"]["approved"] is True
    assert body["result"]["reflection"]["score"] >= 7
    assert "다른 지역 후보로 임의 대체하지 않음" in body["submission_trace_text"]


def test_quick_view_has_numeric_coordinates_and_clear_photo_source() -> None:
    body = _run("양식 파스타 먹고싶어 전북대 근처 가성비 있는 곳")
    first = body["result"]["final_recommendations"][0]
    response = client.post(
        "/places/quick-view",
        json={"place_id": first["place_id"], "name": first["name"], "region": first["region"]},
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["map"]["has_coordinates"] is True
    assert isinstance(detail["map"]["latitude"], float)
    assert isinstance(detail["map"]["longitude"], float)
    assert detail["photos"]
    assert detail["photos"][0]["source"] in {"google_places", "seed", "fallback"}
    if detail["photos"][0]["source"] == "fallback":
        assert detail["photos"][0]["is_fallback"] is True
