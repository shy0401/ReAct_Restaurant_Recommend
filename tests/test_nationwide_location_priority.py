from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _run(query: str) -> dict:
    response = client.post("/agent/run", json={"query": query, "yesterday_menu": "입력 없음", "today_menu": "입력 없음"})
    assert response.status_code == 200
    return response.json()


def _text(item: dict) -> str:
    return " ".join(
        [
            item.get("name", ""),
            item.get("region", ""),
            item.get("city", ""),
            item.get("district", ""),
            item.get("area", ""),
            item.get("category", ""),
            item.get("address", ""),
            item.get("road_address", ""),
            item.get("reason", ""),
            " ".join(item.get("menu", [])),
            " ".join(item.get("tags", [])),
        ]
    )


def test_daejeon_guam_pasta_does_not_fallback_to_jeonju() -> None:
    body = _run("대전 구암역 근처에서 파스타를 먹고 싶어.")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "대전"
    assert parsed["city"] == "대전"
    assert parsed["district"] == "유성구"
    assert parsed["area"] == "구암역"
    assert parsed["food_type"] == "양식"
    assert parsed["menu_keyword"] == "파스타"
    recs = body["result"]["final_recommendations"]
    assert len(recs) >= 3
    for item in recs:
        assert item["region"] == "대전"
        assert "전북대" not in _text(item)
        assert "객사" not in _text(item)
        assert "파스타" in _text(item)


def test_area_only_guam_resolves_to_daejeon() -> None:
    body = _run("구암역 파스타")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "대전"
    assert parsed["area"] == "구암역"
    assert all(item["region"] == "대전" for item in body["result"]["final_recommendations"])


def test_busan_haeundae_cafe_dessert_stays_in_busan() -> None:
    body = _run("부산 해운대 카페 디저트")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "부산"
    assert parsed["area"] == "해운대"
    assert parsed["food_type"] == "카페"
    for item in body["result"]["final_recommendations"]:
        assert item["region"] == "부산"
        assert item["category"] == "카페"
        assert "카페" in _text(item) or "디저트" in _text(item)


def test_seoul_hongdae_sushi_stays_in_seoul() -> None:
    body = _run("서울 홍대 초밥 리뷰 좋은 곳")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "서울"
    assert parsed["area"] == "홍대"
    assert parsed["food_type"] == "일식"
    assert parsed["menu_keyword"] == "초밥"
    for item in body["result"]["final_recommendations"]:
        assert item["region"] == "서울"
        assert "초밥" in _text(item)
        assert "파스타" not in _text(item)


def test_jeju_aewol_pasta_never_uses_other_regions() -> None:
    body = _run("제주 애월 파스타")
    parsed = body["parsed_conditions"]
    assert parsed["region"] == "제주"
    assert parsed["area"] == "애월"
    assert parsed["food_type"] == "양식"
    assert parsed["menu_keyword"] == "파스타"
    for item in body["result"]["final_recommendations"]:
        assert item["region"] == "제주"
        assert "파스타" in _text(item)
        assert item["region"] not in {"전주", "서울", "부산"}


def test_missing_region_sample_returns_shortage_notice_not_other_region() -> None:
    body = _run("울산 삼산동 파스타")
    assert body["parsed_conditions"]["region"] == "울산"
    assert body["result"]["final_recommendations"] == []
    actions = [step["action"] for step in body["result"]["react_trace"]]
    assert "agent.shortage_notice" in actions


def test_structured_recommend_daejeon_guam_pasta() -> None:
    response = client.post(
        "/recommend",
        json={
            "region": "대전",
            "city": "대전",
            "district": "유성구",
            "area": "구암역",
            "landmark": "구암역",
            "latitude": 36.3565,
            "longitude": 127.3307,
            "food_type": "양식",
            "menu_keyword": "파스타",
            "preference": "양식, 파스타",
            "yesterday_menu": "입력 없음",
            "today_menu": "입력 없음",
            "top_k": 3,
        },
    )
    assert response.status_code == 200
    recs = response.json()["final_recommendations"]
    assert len(recs) >= 3
    for item in recs:
        assert item["region"] == "대전"
        assert "파스타" in _text(item)
        assert "전북대" not in _text(item)
