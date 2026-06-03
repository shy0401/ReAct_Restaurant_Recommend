from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.scoring import score_restaurant
from mcp_servers.restaurant_server import search_restaurants
from mcp_servers.weather_server import get_weather


def test_weather_mcp_returns_dict() -> None:
    weather = get_weather("전주")
    assert isinstance(weather, dict)
    assert weather["region"] == "전주"
    assert "condition" in weather


def test_restaurant_mcp_filters_region_and_preference() -> None:
    results = search_restaurants("전주", food_type="국물", preference="따뜻한 한식, 국물 음식")
    candidates = [item for item in results if item.get("id")]
    assert len(candidates) >= 3
    assert all(item["region"] == "전주" for item in candidates)


def test_duplicate_menu_is_penalized() -> None:
    restaurant = {
        "region": "전주",
        "category": "분식",
        "menu": ["라면"],
        "tags": ["면", "국물"],
        "weather_match": ["비"],
        "rating": 4.0,
        "reason": "따뜻한 국물",
    }
    duplicate_score = score_restaurant(
        restaurant,
        region="전주",
        weather_condition="비",
        recent_meals=["치킨", "라면"],
        preference="국물 음식",
    )
    non_duplicate_score = score_restaurant(
        {**restaurant, "menu": ["콩나물국밥"]},
        region="전주",
        weather_condition="비",
        recent_meals=["치킨", "라면"],
        preference="국물 음식",
    )
    assert non_duplicate_score > duplicate_score


def test_recommend_api_returns_success() -> None:
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
    body = response.json()
    assert len(body["final_recommendations"]) >= 3
    assert any(step["action"] == "restaurant.search_restaurants" for step in body["react_trace"])
    assert "reflection" in body
