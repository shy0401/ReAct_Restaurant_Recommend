from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
import app.mcp_clients.mcp_client_manager as mcp_client_module


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


def test_restaurant_tool_exception_is_recorded_as_tool_call_failed(monkeypatch) -> None:
    def broken_search_restaurants(**_: object) -> list[dict]:
        raise RuntimeError("forced restaurant MCP failure")

    monkeypatch.setattr(mcp_client_module, "search_restaurants", broken_search_restaurants)
    body = run_query("전주 객사 근처 파스타 맛집 추천해줘")

    restaurant_steps = [step for step in body["result"]["react_trace"] if step["action"] == "restaurant.search_restaurants"]
    assert restaurant_steps
    observation = restaurant_steps[0]["observation"]
    assert observation["error"] == "tool_call_failed"
    assert observation["server"] == "restaurant"
    assert observation["tool"] == "search_restaurants"
    assert "fallback_strategy" in observation
    assert "user_message" in observation


def test_kakao_api_key_missing_is_observed_as_fallback_sample(monkeypatch) -> None:
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
    monkeypatch.setenv("USE_REAL_PLACE_API", "false")

    body = run_query("대전 구암역 근처에서 파스타를 먹고 싶어")
    restaurant_steps = [step for step in body["result"]["react_trace"] if step["action"] == "restaurant.search_restaurants"]
    assert restaurant_steps
    observation = restaurant_steps[0]["observation"]
    metadata = observation[0]
    assert metadata["warning"] == "relaxed_conditions"
    assert metadata["fallback_used"] == "fallback_sample"
    assert metadata["external_api"]["provider"] == "kakao_local"
    assert metadata["external_api"]["status"] in {"disabled", "api_key_missing"}
    assert any("fallback_sample" in message for message in metadata["messages"])


def test_no_search_results_observation_and_final_answer_do_not_cross_region() -> None:
    body = run_query("대전 구암역 초밥 리뷰 좋은 곳 추천해줘")

    assert body["parsed_conditions"]["region"] == "대전"
    assert body["result"]["final_recommendations"] == []
    restaurant_steps = [step for step in body["result"]["react_trace"] if step["action"] == "restaurant.search_restaurants"]
    assert restaurant_steps
    no_result_observations = [
        item
        for step in restaurant_steps
        for item in (step["observation"] if isinstance(step["observation"], list) else [step["observation"]])
        if isinstance(item, dict) and item.get("warning") in {"no_search_results", "not_enough_strict_candidates"}
    ]
    assert no_result_observations
    assert no_result_observations[-1]["not_done"] == "다른 지역 후보로 임의 대체하지 않음"

    shortage_steps = [step for step in body["result"]["react_trace"] if step["action"] == "agent.shortage_notice"]
    assert shortage_steps
    assert shortage_steps[-1]["observation"]["warning"] == "no_search_results"
    assert "다른 지역으로 임의 대체하지 않았습니다" in body["submission_trace_text"]
    assert "가격 또는 리뷰 조건을 완화" in body["submission_trace_text"]


def test_unknown_region_still_never_uses_other_region_candidates() -> None:
    body = run_query("없는동네에서 파스타 맛집 추천해줘")

    assert body["parsed_conditions"]["error_code"] == "unknown_region"
    assert body["result"]["final_recommendations"] == []
    assert all(step["action"] != "restaurant.search_restaurants" for step in body["result"]["react_trace"])
