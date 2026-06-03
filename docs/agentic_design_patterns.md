# Agentic Design Pattern 적용 설명

이 문서는 과제 제출 시 Agentic Design Pattern 적용 위치와 Trace 확인 방법을 설명합니다.

## 1. ReAct Pattern

적용 위치:

- `app/agent/react_agent.py`
- `app/services/submission_trace.py`
- `frontend/src/components/ReactTracePanel.jsx`

해결하는 문제:

- Agent가 단순히 한 번에 답을 생성하지 않고, 생각하고 도구를 선택하고 결과를 관찰한 뒤 다음 행동을 결정하게 합니다.
- Weather, Memory, Restaurant, Place MCP 도구 호출이 추천 과정에 실제로 반영됩니다.

실행 Trace 확인 방법:

- `Thought`: 사용자의 조건을 분석하거나 다음 도구 호출 이유를 설명합니다.
- `Action`: 호출한 도구 이름입니다.
- `Action Input`: 도구에 전달한 JSON 입력입니다.
- `Observation`: 도구 실행 결과 또는 실패/fallback 정보입니다.

대표 Action:

- `agent.parse_user_query`
- `agent.plan_steps`
- `weather.get_weather`
- `memory.save_meal_history`
- `restaurant.search_restaurants`
- `place.get_place_detail`
- `agent.score_and_draft`
- `reflection.check`
- `agent.finalize`

## 2. Plan-and-Solve Pattern

적용 위치:

- `app/agent/react_agent.py`
- `RecommendationResponse.plan_steps`

해결하는 문제:

- 추천을 바로 실행하기 전에 사용자 조건 분석, MCP 호출, 후보 검색, 점수 계산, 상세 정보 보강, Reflection 검토까지 단계별 계획을 만듭니다.
- 평가자가 Agent가 어떤 순서로 문제를 해결하는지 Trace에서 확인할 수 있습니다.

실행 Trace 확인 방법:

- Trace의 `agent.plan_steps` Action을 확인합니다.
- Observation에 1번부터 10번까지의 해결 계획이 기록됩니다.

## 3. Reflection Pattern

적용 위치:

- `app/agent/reflection.py`
- `app/agent/react_agent.py`

해결하는 문제:

- 초안 추천이 사용자의 명시 조건을 어겼는지 점검합니다.
- 지역, 세부 위치, 메뉴 키워드, 음식 종류, 가격, 평점, 리뷰 수, 친구/저녁 목적, 지도 좌표, 사진 출처를 검토합니다.
- critical issue가 있으면 승인하지 않고 hard mismatch 후보를 제거하거나 부족 안내를 남깁니다.

실행 Trace 확인 방법:

- Trace의 `reflection.check` Action을 확인합니다.
- Observation에 `approved`, `score`, `issues`, `checked_items`, `final_changes`가 포함됩니다.

## 4. Tool Use Pattern

적용 위치:

- `app/mcp_clients/mcp_client_manager.py`
- `mcp_servers/weather_server.py`
- `mcp_servers/restaurant_server.py`
- `mcp_servers/memory_server.py`
- `mcp_servers/place_server.py`

해결하는 문제:

- Agent가 내부 규칙만으로 답하지 않고 도구를 호출해 정보를 수집합니다.
- 도구 호출 실패도 `tool_call_failed` Observation으로 남겨 예외 상황을 설명합니다.

실행 Trace 확인 방법:

- `weather.get_weather`: 날씨 조회
- `memory.save_meal_history`: 최근 식사 저장
- `restaurant.search_restaurants`: 후보 검색
- `place.get_place_detail`: 퀵뷰 상세, 메뉴, 사진, 지도 보강

## 5. Memory Pattern

적용 위치:

- `mcp_servers/memory_server.py`
- `app/agent/react_agent.py`

해결하는 문제:

- 사용자가 어제/오늘 먹은 메뉴를 저장하고, 같은 메뉴 반복 추천을 피합니다.
- 과제 요구사항의 “최근 먹은 메뉴 중복 회피”를 도구 호출 기반으로 수행합니다.

실행 Trace 확인 방법:

- `memory.save_meal_history` Action에서 `recent_meals` Observation을 확인합니다.
- 최종 추천의 `recent_menu_relation` 필드에서 중복 회피 설명을 확인합니다.

## 제출용 Trace 생성

```powershell
python scripts/run_submission_scenario.py
```

생성 파일:

- `submission_outputs/실행로그_trace.txt`
- `submission_outputs/실행로그_trace.json`
- `submission_outputs/과제_실행_요약.md`

샘플 형식은 [docs/sample_submission_trace.txt](sample_submission_trace.txt)를 참고하세요.
