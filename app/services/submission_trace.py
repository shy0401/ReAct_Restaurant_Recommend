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
    for index, item in enumerate(result.final_recommendations, start=1):
        lines.append(f"{index}. {item.name}")
        lines.append(f"   - 대표 메뉴: {', '.join(item.menu)}")
        lines.append(f"   - 가격대: {item.price_range}")
        lines.append(f"   - 평점: {item.rating}")
        lines.append(f"   - 리뷰 수: {item.review_count or 0}")
        lines.append(f"   - 추천 이유: {item.reason}")
        lines.append(f"   - 조건 반영: {item.preference_relation}")
    lines.append("")
    lines.append("Reflection:")
    lines.append(_format_json(result.reflection.model_dump()))
    return "\n".join(lines)


def _format_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return str(value)
