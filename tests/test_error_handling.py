from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def run_query(query: str) -> dict:
    response = client.post(
        "/agent/run",
        json={"query": query, "yesterday_menu": "입력 없음", "today_menu": "입력 없음", "weather": None},
    )
    assert response.status_code == 200
    return response.json()


def test_unknown_region_does_not_return_default_jeonju_recommendations() -> None:
    body = run_query("없는동네에서 파스타 맛집 추천해줘")

    parsed = body["parsed_conditions"]
    assert parsed["needs_clarification"] is True
    assert parsed["error_code"] == "unknown_region"
    assert parsed["region"] == "미확인"
    assert parsed["suggested_queries"]
    assert body["result"]["final_recommendations"] == []

    actions = [step["action"] for step in body["result"]["react_trace"]]
    assert "agent.request_clarification" in actions
    assert "restaurant.search_restaurants" not in actions
    assert "지역을 확인" in body["submission_trace_text"]
    assert "Suggested Queries" in body["submission_trace_text"]


def test_unknown_city_mentions_region_confirmation_in_trace_and_final_answer() -> None:
    body = run_query("블라블라시에서 맛집 찾아줘")

    parsed = body["parsed_conditions"]
    assert parsed["needs_clarification"] is True
    assert parsed["error_code"] == "unknown_region"

    clarification_steps = [step for step in body["result"]["react_trace"] if step["action"] == "agent.request_clarification"]
    assert clarification_steps
    observation = clarification_steps[-1]["observation"]
    assert "지역을 확인" in observation["final_answer"]
    assert observation["suggested_queries"]
    assert "지역을 확인" in body["submission_trace_text"]


def test_vague_food_request_continues_with_warning_trace() -> None:
    body = run_query("전주 객사 근처에서 아무거나 추천해줘")

    parsed = body["parsed_conditions"]
    assert parsed["region"] == "전주"
    assert parsed["needs_clarification"] is False
    assert any("음식 종류가 모호" in warning for warning in parsed["warnings"])
    assert len(body["result"]["final_recommendations"]) >= 1

    warning_steps = [step for step in body["result"]["react_trace"] if step["action"] == "agent.input_warning"]
    assert warning_steps
    assert any("음식 종류가 모호" in warning for warning in warning_steps[-1]["observation"]["warnings"])
    restaurant_steps = [step for step in body["result"]["react_trace"] if step["action"] == "restaurant.search_restaurants"]
    assert restaurant_steps
    assert restaurant_steps[0]["action_input"]["food_type"] is None


def test_insufficient_conditions_are_recorded_but_recommendation_continues() -> None:
    body = run_query("전주 맛집 추천해줘")

    parsed = body["parsed_conditions"]
    assert parsed["region"] == "전주"
    assert parsed["needs_clarification"] is False
    assert any("지역 외 조건이 부족" in warning for warning in parsed["warnings"])
    assert len(body["result"]["final_recommendations"]) >= 1

    warning_steps = [step for step in body["result"]["react_trace"] if step["action"] == "agent.input_warning"]
    assert warning_steps
    assert any("지역 외 조건이 부족" in warning for warning in warning_steps[-1]["observation"]["warnings"])
