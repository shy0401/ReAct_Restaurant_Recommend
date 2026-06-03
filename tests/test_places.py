from __future__ import annotations

from fastapi.testclient import TestClient

from app.agent.reflection import reflection_check
from app.main import app
from mcp_servers.place_server import get_place_detail


def test_place_detail_endpoint_returns_fallback_detail(monkeypatch) -> None:
    monkeypatch.setenv("USE_REAL_PLACE_API", "false")
    client = TestClient(app)
    response = client.get("/places/jeonju_001")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["place"]["address"]
    assert len(body["place"]["menus"]) >= 3


def test_quick_view_returns_menu_photos_and_map(monkeypatch) -> None:
    monkeypatch.setenv("USE_REAL_PLACE_API", "false")
    client = TestClient(app)
    response = client.post(
        "/places/quick-view",
        json={"place_id": "jeonju_001", "name": "전주 온담국밥", "region": "전주"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["menus"]
    assert body["photos"]
    assert body["photos"][0]["is_fallback"] is True
    assert body["map"]["latitude"] is not None
    assert isinstance(body["map"]["latitude"], float)
    assert body["map"]["map_url"]
    assert body["map"]["directions_url"]
    assert body["map"]["has_coordinates"] is True


def test_place_detail_fallback_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("USE_REAL_PLACE_API", "true")
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
    detail = get_place_detail("jeonju_001", "전주 온담국밥", "전주")
    assert detail["source"] == "fallback"
    assert detail["photos"][0]["source"] == "fallback"
    assert detail["photos"][0]["is_fallback"] is True


def test_recommendation_contains_quick_view_fields() -> None:
    client = TestClient(app)
    response = client.post(
        "/recommend",
        json={
            "region": "전주",
            "yesterday_menu": "치킨",
            "today_menu": "라면",
            "weather": None,
            "preference": "따뜻한 한식, 국물 음식",
        },
    )
    assert response.status_code == 200
    item = response.json()["final_recommendations"][0]
    assert item["quick_view_available"] is True
    assert item["place_id"]
    assert item["thumbnail_url"]
    assert "thumbnail_is_fallback" in item
    assert item["latitude"] is not None


def test_unknown_place_uses_photo_fallback_and_map_when_available() -> None:
    detail = get_place_detail("unknown_place", "없는 식당", "전주")
    assert detail["photos"][0]["url"].startswith("/placeholders/")
    assert detail["source"] == "fallback"


def test_reflection_checks_place_detail_fields() -> None:
    result = reflection_check(
        [
            {
                "name": "전주 온담국밥",
                "region": "전주",
                "category": "한식",
                "menu": ["콩나물국밥"],
                "menus": [{"name": "콩나물국밥"}],
                "photos": [{"url": "/placeholders/soup.jpg", "is_fallback": True}],
                "thumbnail_url": "/placeholders/soup.jpg",
                "thumbnail_is_fallback": True,
                "tags": ["국물"],
                "weather_match": ["비"],
                "address": "전북 전주시 완산구 팔달로 12",
                "latitude": 35.818,
                "longitude": 127.156,
                "source": "fallback",
                "reason": "비 오는 날 먹기 좋은 따뜻한 국물 메뉴입니다.",
            }
        ],
        region="전주",
        weather_condition="비",
        recent_meals=["치킨", "라면"],
        preference="한식, 국물",
    )
    assert "지도 좌표 존재 여부 확인" in result.checked_items
    assert "대표 메뉴 정보 확인" in result.checked_items
    assert "실제 사진 부재 시 fallback 안내 확인" in result.checked_items
