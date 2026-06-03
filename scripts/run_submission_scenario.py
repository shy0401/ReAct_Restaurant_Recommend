from __future__ import annotations

import json
import logging
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
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(payload["submission_trace_text"], encoding="utf-8")

    print(f"제출용 trace JSON 생성: {json_path}")
    print(f"제출용 trace TXT 생성: {txt_path}")
    print("")
    print(payload["submission_trace_text"])


if __name__ == "__main__":
    main()
