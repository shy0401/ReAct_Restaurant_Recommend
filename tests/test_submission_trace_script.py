from __future__ import annotations

import json
from pathlib import Path

from scripts import run_submission_scenario


def test_submission_scenario_script_creates_standard_trace_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(run_submission_scenario, "OUTPUT_DIR", tmp_path)

    run_submission_scenario.main()

    txt_path = tmp_path / "실행로그_trace.txt"
    json_path = tmp_path / "실행로그_trace.json"
    summary_path = tmp_path / "과제_실행_요약.md"

    assert txt_path.exists()
    assert json_path.exists()
    assert summary_path.exists()

    trace_text = txt_path.read_text(encoding="utf-8")
    for required in [
        "User Query",
        "Parsed Conditions",
        "Thought",
        "Action",
        "Action Input",
        "Observation",
        "Candidate Filtering Result",
        "Reflection Review Result",
        "Final Answer",
    ]:
        assert required in trace_text

    for keyword in ["전주", "객사", "친구", "저녁", "가격", "리뷰", "3곳"]:
        assert keyword in trace_text

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    actions = [step["action"] for step in payload["result"]["react_trace"]]
    for required_action in [
        "agent.parse_user_query",
        "agent.plan_steps",
        "weather.get_weather",
        "memory.save_meal_history",
        "restaurant.search_restaurants",
        "agent.score_and_draft",
        "place.get_place_detail",
        "reflection.check",
        "agent.finalize",
    ]:
        assert required_action in actions

    summary = summary_path.read_text(encoding="utf-8")
    assert "사용한 Agentic Design Pattern" in summary
    assert run_submission_scenario.SCENARIO_QUERY in summary
    assert "Trace 파일 위치" in summary
    assert "API Key 없이 fallback 데이터로 실행 가능 여부" in summary
