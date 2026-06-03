# 오늘 뭐 먹지 AI

맛집 추천 AI Agent 웹 서비스입니다. 사용자가 지역, 세부 위치, 최근 먹은 메뉴, 날씨, 음식 선호도 또는 자연어 요청을 입력하면 Agent가 MCP 도구를 호출하고, ReAct Trace와 Plan-and-Solve 계획, Reflection 검토를 거쳐 최종 맛집을 추천합니다.

이 프로젝트는 13주차 실습 과제 제출을 기준으로 다음 항목을 포함합니다.

- FastAPI 백엔드와 React/Vite 프론트엔드
- Weather, Restaurant, Memory, Place MCP 서버 4개
- 자연어 요청 실행 API `/agent/run`
- 구조화 입력 추천 API `/recommend`
- ReAct 도구 호출 Trace와 제출용 Trace 생성 스크립트
- Reflection 기반 추천 품질 검토
- API Key 없이 실행 가능한 `fallback_sample` 데이터셋

## 1. 프로젝트 개요

서비스 이름은 **오늘 뭐 먹지 AI**입니다. 사용자의 조건을 아래 우선순위로 반영합니다.

1. 지역
2. 세부 위치
3. 메뉴 키워드
4. 음식 종류
5. 가격, 평점, 리뷰 수
6. 날씨
7. 최근 먹은 메뉴 중복 회피

날씨가 비나 추움이어도 사용자가 `파스타`, `초밥`, `카페`처럼 메뉴나 음식 종류를 명시하면 날씨가 그 조건을 덮어쓰지 않습니다. 지역도 다른 지역으로 임의 완화하지 않습니다.

## 2. 실행 환경

- Python 3.11 이상
- Node.js 18 이상 권장
- Windows PowerShell 기준 명령어 제공
- LLM API Key는 선택 사항
- 외부 장소 API Key도 선택 사항

## 3. 설치 방법

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

프론트엔드는 별도 설치합니다.

```powershell
cd frontend
npm install
cd ..
```

## 4. 백엔드 실행

```powershell
uvicorn app.main:app --reload --port 8000
```

접속:

- FastAPI Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- MCP Status: http://localhost:8000/mcp/status

## 5. 프론트엔드 실행

```powershell
cd frontend
npm run dev
```

접속:

- Web UI: http://localhost:5173

프론트엔드는 기본적으로 자연어 입력을 `/agent/run`으로 전송합니다. 구조화 입력 API인 `/recommend`도 백엔드 문서에서 직접 테스트할 수 있습니다.

## 6. 테스트 실행

```powershell
python -m pytest -q
```

프론트엔드 빌드 확인:

```powershell
cd frontend
npm run build
cd ..
```

## 7. 과제 시나리오 실행 방법

과제 문장:

```text
전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.
```

실행:

```powershell
python scripts/run_submission_scenario.py
```

생성 파일:

- `submission_outputs/실행로그_trace.json`
- `submission_outputs/실행로그_trace.txt`
- `submission_outputs/과제_실행_요약.md`

`submission_outputs/`는 기본적으로 git에는 포함하지 않습니다. 제출 zip에 실행 로그가 필요하면 위 명령을 실행한 뒤 직접 포함하면 됩니다.

## 8. ReAct Trace 생성 방법

Trace는 두 방식으로 확인할 수 있습니다.

1. 웹 UI의 **AI Agent 추론 과정 보기** 패널에서 확인
2. `python scripts/run_submission_scenario.py`로 제출용 로그 생성

Trace 고정 형식:

```text
User Query:
...

Parsed Conditions:
...

Step N
Thought
...
Action
...
Action Input
...
Observation
...

Reflection Review Result:
...

Final Answer:
...
```

프론트엔드에는 Trace 복사와 제출 로그 다운로드 버튼이 있습니다.

## 9. 사용한 Agentic Design Pattern 설명

자세한 설명은 [docs/agentic_design_patterns.md](docs/agentic_design_patterns.md)를 참고하세요.

| Pattern | 적용 위치 | Trace 확인 방법 |
| --- | --- | --- |
| ReAct Pattern | `app/agent/react_agent.py` | `Thought`, `Action`, `Action Input`, `Observation` |
| Plan-and-Solve Pattern | `agent.plan_steps` | Trace의 `agent.plan_steps` Action |
| Reflection Pattern | `app/agent/reflection.py` | Trace의 `reflection.check` Action |
| Tool Use Pattern | `app/mcp_clients/mcp_client_manager.py` | `weather.*`, `restaurant.*`, `memory.*`, `place.*` Action |
| Memory Pattern | `mcp_servers/memory_server.py` | `memory.save_meal_history` Action |

## 10. 도구 목록과 역할

| MCP Server | 파일 | 주요 Tool | 역할 |
| --- | --- | --- | --- |
| Weather MCP | `mcp_servers/weather_server.py` | `get_weather(region)` | 지역 기반 날씨 조회, Open-Meteo 또는 fallback |
| Restaurant MCP | `mcp_servers/restaurant_server.py` | `search_restaurants(...)`, `get_restaurant_detail(...)` | 지역, 세부 위치, 메뉴, 가격, 평점, 리뷰 기반 후보 검색 |
| Memory MCP | `mcp_servers/memory_server.py` | `save_meal_history`, `get_recent_meals`, `check_duplicate` | 최근 식사 기록 저장과 중복 회피 |
| Place MCP | `mcp_servers/place_server.py` | `get_place_detail`, `get_place_photos`, `get_place_menu`, `get_static_map` | 퀵뷰 상세, 사진, 메뉴, 지도 좌표 보강 |

FastAPI 테스트와 웹 서비스에서는 `MCPClientManager`가 같은 Tool 함수를 직접 호출하므로, 별도 MCP 프로세스를 켜지 않아도 동작합니다. MCP 서버 파일은 아래처럼 개별 실행도 가능합니다.

```powershell
python mcp_servers/weather_server.py
python mcp_servers/restaurant_server.py
python mcp_servers/memory_server.py
python mcp_servers/place_server.py
```

## 11. 외부 API 사용 방법

자세한 설정은 [docs/api_usage.md](docs/api_usage.md)를 참고하세요.

백엔드 `.env` 예시:

```env
OPENAI_API_KEY=
USE_LLM=false
WEATHER_API_MODE=fallback
DATABASE_URL=sqlite:///./food_agent.db
FRONTEND_ORIGIN=http://localhost:5173

USE_REAL_PLACE_API=true
KAKAO_REST_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
GOOGLE_PLACES_API_KEY=
MAP_PROVIDER=leaflet
PLACE_CACHE_TTL_HOURS=24
BACKEND_PUBLIC_URL=http://localhost:8000
```

프론트엔드 `frontend/.env` 예시:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_MAP_PROVIDER=leaflet
VITE_KAKAO_JAVASCRIPT_KEY=
```

주의:

- Kakao Local REST API Key와 Kakao Maps JavaScript Key는 다릅니다.
- 실제 음식점 사진은 Kakao Local API만으로 안정적으로 가져올 수 없습니다.
- 실제 사진을 원하면 `GOOGLE_PLACES_API_KEY`가 필요합니다.
- Google API Key는 프론트엔드에 노출하지 않고 백엔드 `/places/photo` 프록시를 사용합니다.

## 12. API Key가 없을 때 fallback 데이터셋으로 실행되는 방식

API Key가 없어도 서버는 죽지 않습니다.

- 날씨: `WEATHER_API_MODE=fallback`이면 fallback 날씨를 사용합니다.
- 장소 검색: `USE_REAL_PLACE_API=true`여도 Kakao Key가 없으면 `app/data/restaurants.json`의 `fallback_sample`을 사용합니다.
- 실제 사진: Google Places Key가 없으면 placeholder 이미지를 사용하고 UI에 기본 이미지임을 표시합니다.
- 지도: Key 없이도 Leaflet + OpenStreetMap으로 좌표 기반 지도를 표시합니다.
- 특정 지역 샘플 데이터가 없으면 다른 지역 후보로 채우지 않고 부족 안내를 반환합니다.

## 13. 예외 처리 전략

| 상황 | 처리 방식 |
| --- | --- |
| 모르는 지역 | 추천 중단, `needs_clarification=true`, suggested queries 제공 |
| 조건 부족 | 지역이 없으면 확인 요청, 지역만 있으면 추천 진행과 warning 기록 |
| 음식 종류 모호 | 평점/거리/가격 중심 추천, Trace에 모호함 Observation 기록 |
| API 호출 실패 | 앱 500으로 올리지 않고 Tool Observation에 실패와 fallback 전략 기록 |
| 검색 결과 없음 | `no_search_results` 또는 `not_enough_strict_candidates` Observation 기록 |
| 후보 부족 | 다른 지역으로 보강하지 않고 부족한 개수만 반환 |
| Reflection 미승인 | hard mismatch 제거, 재정렬 또는 부족 안내 |

## 14. 제출 zip에 포함할 파일

- `app/`
- `mcp_servers/`
- `frontend/`
- `scripts/`
- `tests/`
- `docs/`
- `README.md`
- `requirements.txt`
- `.env.example`
- `frontend/.env.example`
- `.gitignore`
- 필요 시 실행 후 생성한 `submission_outputs/실행로그_trace.txt`
- 필요 시 실행 후 생성한 `submission_outputs/실행로그_trace.json`
- 필요 시 실행 후 생성한 `submission_outputs/과제_실행_요약.md`

## 15. 제출 zip에서 제외할 파일

- `.venv/`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `node_modules/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.env`
- API Key가 들어 있는 파일
- `app/data/place_cache.json`
- IDE 설정 파일

제출 파일명 예시:

```text
신하윤_202112026_실습4.zip
```

## 16. 제출 전 체크리스트

자세한 체크리스트는 [docs/submission_checklist.md](docs/submission_checklist.md)를 참고하세요.

- [ ] `python -m pytest -q` 통과
- [ ] `python scripts/run_submission_scenario.py` 실행
- [ ] `cd frontend && npm run build` 통과
- [ ] README 실행 명령 확인
- [ ] ReAct Trace에 Thought, Action, Action Input, Observation 포함
- [ ] Reflection 결과 포함
- [ ] 과제 문장 최종 추천 3곳 확인
- [ ] `.env`, API Key, `.venv`, `node_modules` 제외

## 주요 API

### POST `/agent/run`

자연어 요청을 파싱한 뒤 추천 Agent를 실행합니다.

```json
{
  "query": "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.",
  "yesterday_menu": "입력 없음",
  "today_menu": "입력 없음",
  "weather": null
}
```

응답에는 `parsed_conditions`, `result.react_trace`, `result.reflection`, `result.final_recommendations`, `submission_trace_text`가 포함됩니다.

### POST `/recommend`

구조화된 JSON 입력으로 추천 Agent를 실행합니다.

```json
{
  "region": "전주",
  "city": "전주",
  "district": "완산구",
  "area": "객사",
  "yesterday_menu": "입력 없음",
  "today_menu": "입력 없음",
  "weather": null,
  "preference": "친구와 방문, 저녁, 가성비, 리뷰 좋은 곳",
  "max_price": 15000,
  "min_rating": 4.0,
  "min_review_count": 50,
  "top_k": 3,
  "purpose": "저녁",
  "companion": "친구"
}
```

### POST `/places/quick-view`

추천 카드의 퀵뷰 상세 정보를 반환합니다.

```json
{
  "place_id": "jeonju_010",
  "name": "객사 소담전골",
  "region": "전주"
}
```

### GET `/mcp/status`

연결된 MCP 서버 목록과 상태를 반환합니다.

### GET `/health`

서비스 상태와 LLM 사용 여부를 반환합니다.

## 캐시 초기화

장소 상세 캐시를 지우려면 아래 명령을 실행합니다.

```powershell
Remove-Item app\data\place_cache.json -ErrorAction SilentlyContinue
```
