from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app


SCENARIO_QUERY = "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."
OUTPUT_DIR = Path("submission_outputs")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.getLogger().setLevel(logging.WARNING)
    OUTPUT_DIR.mkdir(exist_ok=True)
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "query": SCENARIO_QUERY,
            "yesterday_menu": "입력 없음",
            "today_menu": "입력 없음",
            "weather": None,
        },
    )
    response.raise_for_status()
    payload = response.json()

    json_path = OUTPUT_DIR / "실행로그_trace.json"
    txt_path = OUTPUT_DIR / "실행로그_trace.txt"
    summary_path = OUTPUT_DIR / "과제_실행_요약.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(payload["submission_trace_text"], encoding="utf-8")
    summary_path.write_text(_build_summary(payload, json_path, txt_path), encoding="utf-8")

    print(f"제출용 trace JSON 생성: {json_path}")
    print(f"제출용 trace TXT 생성: {txt_path}")
    print(f"과제 실행 요약 생성: {summary_path}")
    print("")
    print(payload["submission_trace_text"])


def _build_summary(payload: dict, json_path: Path, txt_path: Path) -> str:
    result = payload["result"]
    recommendations = result.get("final_recommendations", [])
    lines = [
        "# 과제 실행 요약",
        "",
        "## 사용한 Agentic Design Pattern",
        "",
        "- ReAct Pattern: Thought, Action, Action Input, Observation 단계로 MCP 도구 호출을 기록",
        "- Plan-and-Solve Pattern: `agent.plan_steps`로 추천 계획을 먼저 생성",
        "- Reflection Pattern: `reflection.check`로 초안 추천을 검토하고 필요 시 재정렬",
        "- Tool Use Pattern: Weather, Memory, Restaurant, Place MCP 도구 호출",
        "- Memory Pattern: 최근 식사 입력을 저장하고 중복 회피에 사용",
        "",
        "## 실행한 프롬프트",
        "",
        SCENARIO_QUERY,
        "",
        "## 최종 추천 3곳 요약",
        "",
    ]
    if recommendations:
        for index, item in enumerate(recommendations[:3], start=1):
            lines.extend(
                [
                    f"{index}. {item.get('name')}",
                    f"   - 지역: {item.get('region')} / {item.get('area') or '-'}",
                    f"   - 대표 메뉴: {', '.join(item.get('menu', []))}",
                    f"   - 가격대: {item.get('price_range')}",
                    f"   - 평점/리뷰: {item.get('rating')} / {item.get('review_count') or 0}",
                    f"   - 추천 이유: {item.get('reason')}",
                ]
            )
    else:
        lines.append("- 조건을 만족하는 최종 추천이 없어 Trace의 예외 대안을 확인하세요.")
    lines.extend(
        [
            "",
            "## Trace 파일 위치",
            "",
            f"- 텍스트 Trace: `{txt_path.as_posix()}`",
            f"- JSON Trace: `{json_path.as_posix()}`",
            "",
            "## API Key 없이 fallback 데이터로 실행 가능 여부",
            "",
            "- 가능",
            f"- USE_REAL_PLACE_API={os.getenv('USE_REAL_PLACE_API', 'false')}",
            "- Kakao/Google API Key가 없어도 fallback_sample 데이터와 placeholder 이미지로 실행됩니다.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
