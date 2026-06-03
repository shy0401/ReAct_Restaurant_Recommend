# 13주차 실습 과제 기준 진단 리포트

작성일: 2026-06-03  
작업 브랜치: `codex/assignment-gap-analysis`  
진단 범위: 현재 저장소의 FastAPI 백엔드, React/Vite 프론트엔드, MCP/도구 서버, ReAct Agent, Reflection, 제출용 Trace 스크립트

## 0. 기준 상태

- 최초 확인 명령: `git status --short --branch`
- 최초 상태: `## main...origin/main`, 작업트리 변경 없음
- 기준 브랜치 준비: `codex/assignment-gap-analysis` 브랜치 생성 후 문서 작성
- 이번 단계 원칙: 기능 수정 없음. 변경 대상은 이 문서 `docs/assignment_gap_analysis.md`만으로 제한

## 1. 프로젝트 구성 확인

| 구성 요소 | 충족 여부 | 확인 근거 |
|---|---:|---|
| Python FastAPI 백엔드 | 충족 | `app/main.py`에 `FastAPI` 앱, `/health`, `/mcp/status`, `/recommend`, `/agent/run`, `/places/quick-view`, `/places/photo` 엔드포인트가 있음. |
| React/Vite 프론트엔드 | 충족 | `frontend/package.json`, `frontend/src/App.jsx`, `frontend/src/components/*`, `frontend/src/api/recommendApi.js` 존재. `npm run build` 통과. |
| MCP/도구 서버 | 충족 | `mcp_servers/weather_server.py`, `restaurant_server.py`, `memory_server.py`, `place_server.py` 존재. `app/mcp_clients/mcp_client_manager.py`가 4개 서버 도구를 연결. |
| ReAct Agent | 충족 | `app/agent/react_agent.py`의 `FoodReActAgent.run()`이 Thought, Action, Action Input, Observation을 `ReActTraceStep`으로 누적. |
| Reflection | 충족 | `app/agent/reflection.py`의 `reflection_check()`가 추천 후보를 검토하고 `ReflectionResult`를 반환. |
| 제출용 Trace 스크립트 | 충족 | `scripts/run_submission_scenario.py`가 과제 예시 문장을 `/agent/run`에 보내고 `submission_outputs/실행로그_trace.json`, `submission_outputs/실행로그_trace.txt`를 생성. |

## 2. 과제 요구사항별 충족 현황

| 과제 요구사항 | 현재 판정 | 관련 파일 | 확인 근거와 비고 |
|---|---:|---|---|
| 맛집 검색 도구 구현 | 충족 | `mcp_servers/restaurant_server.py` | `search_restaurants()`와 `get_restaurant_detail()`이 구현되어 있고, MCP tool로 등록됨. |
| 지역 기반 검색 | 충족 | `mcp_servers/restaurant_server.py`, `app/services/location_resolver.py`, `app/data/korea_location_aliases.json` | `region`, `city`, `district`, `area`, `landmark`를 받아 지역 불일치 후보를 제거. 전국 alias 기반 위치 해석도 존재. |
| 음식 종류 기반 검색 | 충족 | `app/services/query_parser.py`, `mcp_servers/restaurant_server.py`, `app/services/scoring.py` | 자연어에서 `food_type`, `menu_keyword`를 추출하고 검색/점수/하드 미스매치 필터에 반영. |
| 평점, 리뷰 수, 거리, 가격대 고려 | 충족 | `mcp_servers/restaurant_server.py`, `app/services/scoring.py`, `app/services/geo_utils.py` | `max_price`, `min_rating`, `min_review_count`, 위경도 거리 계산을 검색과 정렬에 사용. |
| 외부 API 또는 샘플 데이터셋 사용 | 충족 | `app/data/restaurants.json`, `app/services/kakao_local_service.py`, `app/services/google_places_service.py`, `mcp_servers/place_server.py` | fallback sample 데이터셋이 있고, Kakao Local/Google Places Photo 연동 경로가 있음. API 키 없으면 fallback으로 동작. |
| ReAct Pattern 필수 적용 | 충족 | `app/agent/react_agent.py`, `app/agent/schemas.py` | `ReActTraceStep` 모델과 `_act()`가 Thought, Action, Action Input, Observation을 기록. |
| Agentic Design Pattern 2개 이상 적용 | 충족 | `app/agent/react_agent.py`, `app/agent/reflection.py`, `app/mcp_clients/mcp_client_manager.py` | ReAct, Plan-and-Solve(`agent.plan_steps`), Reflection, Tool Use, Memory Pattern이 README와 코드에 반영. |
| ReAct Agent Client 실행 루프 | 부분 충족 | `app/agent/react_agent.py`, `app/mcp_clients/mcp_client_manager.py` | Agent가 순차적으로 Weather, Memory, Restaurant, Place 도구를 호출하고 Observation을 저장함. 다만 FastAPI 실행 경로에서는 MCP 서버를 별도 네트워크 프로세스로 호출하지 않고 동일 도구 함수를 local facade로 직접 호출함. |
| 존재하지 않는 지역 예외 처리 | 부분 충족 | `app/services/location_resolver.py`, `mcp_servers/restaurant_server.py`, `tests/test_nationwide_location_priority.py` | `restaurant_server`는 해당 region 후보가 없으면 `region_not_found` error object를 반환. 그러나 자연어 위치 해석 실패 시 `location_resolver`가 기본 지역 `전주`로 대체하므로, "알 수 없는 지역" 자체를 유지한 에러로 남기는 흐름은 보강 여지가 있음. |
| 검색 결과 없음 예외 처리 | 충족 | `mcp_servers/restaurant_server.py`, `app/agent/react_agent.py` | 후보가 없으면 `not_enough_strict_candidates` warning을 반환하고, Agent가 `agent.shortage_notice` Trace를 남김. |
| 음식 종류가 너무 모호한 경우 | 부분 충족 | `app/services/query_parser.py`, `app/agent/react_agent.py` | 음식 종류를 찾지 못해도 추천은 실패하지 않음. 다만 "음식 종류가 모호하다"는 별도 Observation 또는 사용자 안내가 명확히 남는 구조는 아직 약함. |
| API 호출 실패 대응 | 충족 | `app/agent/react_agent.py`, `app/mcp_clients/mcp_client_manager.py`, `app/services/location_resolver.py`, `mcp_servers/weather_server.py`, `mcp_servers/place_server.py` | `_act()`와 `MCPClientManager.call_tool()`이 예외를 error Observation으로 전환. Weather/Place/Kakao/Google 경로도 fallback 또는 warning을 남김. |
| 사용자의 조건 부족 대응 | 부분 충족 | `app/services/query_parser.py`, `app/services/location_resolver.py`, `frontend/src/components/RecommendationForm.jsx` | 지역/목적 일부 부족은 warnings 또는 기본값으로 처리. 하지만 음식 종류/가격/동행 목적이 모두 부족한 경우, 조건 부족을 명확히 묻거나 Trace에 별도 단계로 남기는 UX는 보강 가능. |
| 실행 테스트 시나리오와 Trace 제출 | 충족 | `scripts/run_submission_scenario.py`, `app/services/submission_trace.py`, `tests/test_assignment_scenario.py` | 과제 문장 그대로 `/agent/run` 실행 후 JSON/TXT Trace 생성. 테스트도 Trace action과 `submission_trace_text`를 검증. |
| README, requirements, 실행 로그, 패턴 설명, API 설명 | 충족 | `README.md`, `requirements.txt`, `scripts/run_submission_scenario.py` | README에 아키텍처, Pattern, MCP 서버, API, 실행 방법, fallback, 전국 지역 대응, 제출용 로그 생성 방법이 포함. `requirements.txt`도 FastAPI, uvicorn, pydantic, requests, mcp, pytest, httpx 등을 포함. |

## 3. 예상 보강 포인트 확인

| 확인 항목 | 현재 상태 | 근거 | 보강 판단 |
|---|---:|---|---|
| 자연어 입력에서 모르는 지역을 전주로 자동 대체하는지 | 예 | `app/services/location_resolver.py`에서 alias/API로 지역을 찾지 못하면 `region="전주"`, `source="fallback"`로 설정하고 warning을 추가. | P0 후보. 전국 대응 원칙상 사용자가 모르는 지역을 입력했을 때 전주 추천으로 오해될 수 있음. |
| 모호한 음식 요청이 명확한 Observation으로 남는지 | 부분 | `/agent/run`의 `agent.parse_user_query` Observation에 `food_type=None`, `menu_keyword=None`은 남을 수 있음. 그러나 "음식 종류가 모호함"을 별도 warning/action으로 명시하지는 않음. | P1 후보. 평가자가 Trace에서 모호성 대응을 쉽게 볼 수 있게 개선 필요. |
| API 실패가 Tool Observation에 남는지 | 대체로 예 | `FoodReActAgent._act()`가 tool failure를 `tool_call_failed` observation으로 저장. `MCPClientManager.call_tool()`도 error dict를 반환. 외부 API 실패는 location/place/weather fallback warning으로 남음. | P1. 모든 외부 API 실패가 ReAct action 단위 Observation으로 보이는지 정교화 가능. |
| 제출용 스크립트가 과제 문장 그대로 Trace 파일을 생성하는지 | 예 | `scripts/run_submission_scenario.py`의 `SCENARIO_QUERY`가 `"전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."`와 일치. | 충족. |
| 프론트엔드에서 ReAct Trace와 Reflection이 표시되는지 | 예 | `frontend/src/App.jsx`가 `ReflectionPanel`과 `ReactTracePanel`을 렌더링. `frontend/src/components/ReactTracePanel.jsx`, `ReflectionPanel.jsx` 존재. | 충족. |

## 4. 검증 결과

| 명령 | 결과 | 비고 |
|---|---:|---|
| `python -m pytest -q` | 통과 | `23 passed in 7.21s` |
| `cd frontend && npm run build` | 통과 | `Frontend build completed: dist/` |

테스트와 빌드가 생성한 `frontend/dist/`, `__pycache__/`, `.pytest_cache/`, `app/data/place_cache.json`, `app/data/meal_history.json` 등은 `.gitignore`에 의해 커밋 대상에서 제외된다.

## 5. 수정 우선순위

### P0

- 알 수 없는 지역을 무조건 `전주`로 대체하는 현재 fallback 정책 재검토.
  - 과제의 "존재하지 않는 지역 예외 처리" 관점에서는 `region_not_found` 또는 `location_unresolved` Observation을 더 명확히 남기는 편이 안전하다.
  - 특히 전국 지역 대응 원칙과 충돌할 수 있으므로, 사용자가 지역을 입력했지만 해석 실패한 경우에는 다른 지역 추천으로 넘어가지 않는 구조가 필요하다.

### P1

- 음식 종류가 모호한 요청에 대해 별도 warning 또는 `agent.ambiguous_food_request` Trace step 추가.
  - 현재는 추천이 실패하지 않는다는 장점은 있으나, 평가자가 "모호한 음식 종류 대응"을 Trace에서 바로 확인하기 어렵다.
- API 실패 대응을 더 일관된 Tool Observation 형태로 정리.
  - MCP 도구 실패는 잘 남지만, Kakao/Google 같은 외부 API 실패가 일부는 warning/fallback message로만 남는다.
- `/agent/run`의 parsed conditions와 shortage notice를 프론트엔드에서 더 눈에 띄게 표시.

### P2

- FastAPI 경로에서 MCP 서버를 local facade로 직접 호출하는 구조와 별도 MCP 서버 실행 구조의 관계를 README에 더 명확히 설명.
- 제출용 `project_combined.txt` 생성 시 캐시/로그 파일이 포함되지 않는지 정기 확인.
- README의 실행 예시와 실제 프론트엔드 입력 흐름을 과제 시연 순서에 맞춰 조금 더 압축 정리.
