from __future__ import annotations

import json
from typing import Any

from app.agent.schemas import ParsedRecommendationConditions, RecommendationResponse


def build_submission_trace_text(
    *,
    query: str,
    parsed_conditions: ParsedRecommendationConditions,
    result: RecommendationResponse,
) -> str:
    lines: list[str] = []
    lines.append("User Query:")
    lines.append(query)
    lines.append("")
    lines.append("Parsed Conditions:")
    lines.append(json.dumps(parsed_conditions.model_dump(), ensure_ascii=False, indent=2))
    lines.append("")

    for index, step in enumerate(result.react_trace, start=1):
        lines.append(f"Step {index}")
        lines.append("Thought:")
        lines.append(step.thought)
        lines.append("Action:")
        lines.append(step.action)
        lines.append("Action Input:")
        lines.append(_format_json(step.action_input))
        lines.append("Observation:")
        lines.append(_format_json(step.observation))
        lines.append("")

    lines.append("Final Answer:")
    if result.final_recommendations:
        for index, item in enumerate(result.final_recommendations, start=1):
            lines.append(f"{index}. {item.name}")
            lines.append(f"   - 대표 메뉴: {', '.join(item.menu)}")
            lines.append(f"   - 가격대: {item.price_range}")
            lines.append(f"   - 평점: {item.rating}")
            lines.append(f"   - 리뷰 수: {item.review_count or 0}")
            lines.append(f"   - 추천 이유: {item.reason}")
            lines.append(f"   - 조건 반영: {item.preference_relation}")
        if len(result.final_recommendations) < result.input.top_k:
            lines.append("")
            lines.append(f"현재 조건으로는 {result.input.top_k}곳을 모두 채우지 못했습니다.")
            lines.append("다른 지역으로 임의 대체하지 않았습니다.")
            lines.append("가격 조건, 리뷰 수 조건 또는 세부 위치를 완화하면 더 찾을 수 있습니다.")
    elif parsed_conditions.needs_clarification:
        lines.append(parsed_conditions.clarification_reason or "추가 조건 확인이 필요합니다.")
        lines.append("지역을 확인할 수 없어 실제 맛집 추천을 중단했습니다.")
    else:
        lines.append("조건을 만족하는 후보가 부족해 실제 맛집 추천을 반환하지 않았습니다.")
        lines.append("다른 지역으로 임의 대체하지 않았습니다.")
        lines.append("가격 또는 리뷰 조건을 완화하면 더 찾을 수 있습니다.")
    if parsed_conditions.suggested_queries:
        lines.append("")
        lines.append("Suggested Queries:")
        for query in parsed_conditions.suggested_queries:
            lines.append(f"- {query}")
    lines.append("")
    lines.append("Reflection:")
    lines.append(_format_json(result.reflection.model_dump()))
    return "\n".join(lines)


def _format_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return str(value)
