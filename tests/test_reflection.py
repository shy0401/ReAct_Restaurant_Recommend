from __future__ import annotations

from app.agent.reflection import reflection_check


def test_reflection_detects_duplicate_and_weather_mismatch() -> None:
    draft = [
        {
            "name": "라면집",
            "region": "전주",
            "category": "분식",
            "menu": ["라면"],
            "menus": [{"name": "라면"}],
            "photos": [{"url": "/placeholders/noodle.jpg", "is_fallback": True}],
            "thumbnail_url": "/placeholders/noodle.jpg",
            "thumbnail_is_fallback": True,
            "tags": ["면"],
            "weather_match": ["맑음"],
            "address": "전북 전주시 완산구 예시로 1",
            "latitude": 35.81,
            "longitude": 127.15,
            "source": "fallback",
            "reason": "간단한 메뉴",
        }
    ]
    result = reflection_check(
        draft,
        region="전주",
        weather_condition="비",
        recent_meals=["치킨", "라면"],
        preference="따뜻한 한식, 국물 음식",
    )
    assert not result.approved
    assert result.score < 8
    assert result.issues
