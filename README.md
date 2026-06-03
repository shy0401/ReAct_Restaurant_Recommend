# 오늘 뭐 먹지 AI

맛집 추천 AI Agent 웹 서비스입니다. 사용자가 지역, 최근 먹은 메뉴, 날씨, 음식 선호도 또는 자연어 요청을 입력하면 Agent가 MCP 도구를 호출하고, ReAct Trace와 Plan-and-Solve 계획, Reflection 검토를 거쳐 최종 맛집 3곳 이상을 추천합니다.

## 전체 아키텍처

```text
React/Vite UI
  └─ FastAPI app.main
      ├─ /recommend: 구조화 입력 추천
      ├─ /agent/run: 자연어 과제 시나리오 실행
      ├─ /mcp/status: MCP 상태
      └─ /places/quick-view: 퀵뷰 상세
          └─ RecommendationService
              └─ FoodReActAgent
                  ├─ Weather MCP
                  ├─ Memory MCP
                  ├─ Restaurant MCP
                  └─ Place MCP
```

## Agentic Design Pattern

- **Plan-and-Solve Pattern**: Agent 실행 초반 `agent.plan_steps`에서 지역 분석, MCP 호출, 후보 검색, 상세 보강, Reflection까지의 계획을 먼저 생성합니다.
- **ReAct Pattern**: `Thought -> Action -> Action Input -> Observation` 형식으로 Weather, Memory, Restaurant, Place MCP를 호출합니다.
- **Reflection Pattern**: 초안 추천 후 가격, 평점, 리뷰 수, 세부 위치, 친구/저녁 목적, 메뉴 중복, 지도/사진 정보를 검토합니다.
- **Tool Use Pattern**: MCPClientManager를 통해 각 MCP 서버의 도구를 호출합니다.
- **Memory Pattern**: Memory MCP가 어제/오늘 먹은 메뉴를 저장하고 중복 메뉴 회피에 사용합니다.

## MCP 서버 구성

- `mcp_servers/weather_server.py`: `get_weather(region)` 제공. Open-Meteo 또는 fallback 날씨 사용.
- `mcp_servers/restaurant_server.py`: `search_restaurants(...)`, `get_restaurant_detail(...)` 제공. 지역, area, 가격, 평점, 리뷰 수 조건 검색과 조건 완화 검색을 지원합니다.
- `mcp_servers/memory_server.py`: `save_meal_history`, `get_recent_meals`, `check_duplicate` 제공.
- `mcp_servers/place_server.py`: `search_real_places`, `get_place_detail`, `get_place_photos`, `get_place_menu`, `get_static_map` 제공.

## 자연어 시나리오 실행

과제 예시 문장을 그대로 실행할 수 있습니다.

```bash
curl -X POST http://localhost:8000/agent/run ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.\",\"yesterday_menu\":\"입력 없음\",\"today_menu\":\"입력 없음\",\"weather\":null}"
```

응답에는 `parsed_conditions`, `result.react_trace`, `result.plan_steps`, `result.reflection`, `submission_trace_text`가 포함됩니다.

## 실행 방법

백엔드:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

MCP 서버를 별도 프로세스로 확인하고 싶을 때:

```bash
python mcp_servers/weather_server.py
python mcp_servers/restaurant_server.py
python mcp_servers/memory_server.py
python mcp_servers/place_server.py
```

프론트엔드:

```bash
cd frontend
npm install
npm run dev
```

접속:

- Web UI: http://localhost:5173
- FastAPI Docs: http://localhost:8000/docs

## 테스트와 제출 로그

```bash
python -m pytest -q
cd frontend
npm run build
cd ..
python scripts/run_submission_scenario.py
```

`scripts/run_submission_scenario.py`는 아래 파일을 생성합니다.

- `submission_outputs/실행로그_trace.json`
- `submission_outputs/실행로그_trace.txt`

`submission_outputs`는 `.gitignore`에 포함되어 있으므로 제출 zip에는 필요 시 직접 포함하세요.

## API 명세

### POST `/recommend`

구조화된 JSON 입력으로 추천합니다.

```json
{
  "region": "전주",
  "area": "객사",
  "yesterday_menu": "치킨",
  "today_menu": "라면",
  "weather": null,
  "preference": "따뜻한 한식, 국물 음식",
  "max_price": 15000,
  "min_rating": 4.0,
  "min_review_count": 50,
  "top_k": 3,
  "purpose": "저녁",
  "companion": "친구"
}
```

### POST `/agent/run`

자연어 요청을 파싱한 뒤 기존 추천 Agent를 실행합니다.

```json
{
  "query": "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘.",
  "yesterday_menu": "입력 없음",
  "today_menu": "입력 없음",
  "weather": null
}
```

### POST `/places/quick-view`

추천 카드의 퀵뷰 모달 상세 정보를 반환합니다.

## 외부 API와 fallback

`.env.example`을 참고해 `.env`를 만듭니다.

```env
OPENAI_API_KEY=
USE_LLM=false
WEATHER_API_MODE=fallback
DATABASE_URL=sqlite:///./food_agent.db
FRONTEND_ORIGIN=http://localhost:5173

USE_REAL_PLACE_API=false
KAKAO_REST_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
GOOGLE_PLACES_API_KEY=
MAP_PROVIDER=leaflet
PLACE_CACHE_TTL_HOURS=24
BACKEND_PUBLIC_URL=http://localhost:8000
```

프론트엔드 `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_MAP_PROVIDER=leaflet
VITE_KAKAO_JAVASCRIPT_KEY=
```

- Kakao Local API는 장소명, 주소, 좌표, 전화번호 중심 정보를 제공합니다.
- Kakao REST API 키와 Kakao Maps JavaScript 키는 다릅니다.
- 실제 음식점 사진을 가져오려면 `GOOGLE_PLACES_API_KEY`가 필요합니다.
- API Key가 없으면 fallback 이미지를 표시합니다. 이는 오류가 아니라 API Key 없는 상태의 정상 동작입니다.
- 지도는 API Key 없이도 Leaflet + OpenStreetMap으로 표시됩니다.

## 지도와 이미지 확인 포인트

- 지도는 `PlaceMap.jsx`에서 Leaflet 컴포넌트로 렌더링합니다.
- OpenStreetMap URL은 이미지가 아니므로 `img src`에 넣지 않습니다.
- `latitude`, `longitude`가 문자열이어도 숫자로 변환합니다.
- `/places/quick-view` 응답의 `map.has_coordinates`가 `true`이면 지도 미리보기가 표시됩니다.
- placeholder 이미지는 `frontend/public/placeholders/` 기준으로 제공됩니다.
## 최종 보강 사항: 추천 우선순위

명시적인 사용자 조건이 날씨 추천 힌트에 덮이지 않도록 아래 우선순위를 코드와 테스트에 반영했습니다.

1. 지역
2. 세부 위치
3. 원하는 메뉴 또는 음식 종류
4. 가격대, 가성비
5. 평점, 리뷰 수
6. 날씨
7. 최근 먹은 메뉴 중복 회피

예를 들어 `양식 파스타 먹고싶어. 전북대 근처 가성비 있는 곳`은 `region=전주`, `area=전북대`, `food_type=양식`, `menu_keyword=파스타`, `max_price=15000`으로 파싱됩니다. 날씨가 비여도 국밥, 전골, 삼계탕, 찌개 같은 한식 국물류로 대체하지 않습니다.

## 자연어 실행 API

```http
POST /agent/run
```

```json
{
  "query": "양식 파스타 먹고싶어. 전북대 근처 가성비 있는 곳",
  "yesterday_menu": "입력 없음",
  "today_menu": "입력 없음",
  "weather": null
}
```

응답에는 `parsed_conditions`, `result.react_trace`, `result.reflection`, `result.final_recommendations`, `submission_trace_text`가 포함됩니다. 기본 React 화면도 이 API를 사용합니다.

## 실제 데이터 연동과 fallback

- Kakao Local API: 실제 장소명, 주소, 좌표, 전화번호, place_url 보강에 사용합니다.
- Google Places Photo API: 실제 음식점 사진이 필요할 때 사용합니다. 프론트엔드에는 API 키를 노출하지 않고 `/places/photo` 프록시를 사용합니다.
- Leaflet + OpenStreetMap: API 키 없이도 지도 미리보기를 표시합니다.
- Kakao Maps JavaScript SDK: `VITE_KAKAO_JAVASCRIPT_KEY`와 `VITE_MAP_PROVIDER=kakao` 설정 시 브라우저 지도 렌더링에 사용합니다.
- API 키가 없으면 `fallback_sample` 데이터와 placeholder 이미지를 사용합니다. fallback 이미지는 실제 매장 사진이 아니며 UI에서 기본 이미지로 표시합니다.

## 제출용 테스트 명령

```powershell
python -m pytest -q
python scripts/run_submission_scenario.py

cd frontend
npm install
npm run build
```

제출용 로그는 `submission_outputs/실행로그_trace.json`, `submission_outputs/실행로그_trace.txt`에 생성됩니다. zip 제출 시 `.venv/`, `__pycache__/`, `node_modules/`, `.env`, API Key, 캐시 파일은 제외하세요.

## 전국 지역 대응 원칙

전국 지역 대응을 위해 `app/services/location_resolver.py`와 `app/data/korea_location_aliases.json`을 추가했습니다. 자연어 요청은 먼저 지역, 도시, 구/군, 세부 위치, 랜드마크로 해석되고, 이후 메뉴/음식 종류 조건과 결합됩니다.

- 지역은 절대 다른 지역으로 완화하지 않습니다.
- 세부 위치는 같은 지역/도시 안에서만 완화합니다.
- 메뉴 키워드와 음식 종류는 날씨보다 우선합니다.
- 후보가 부족하면 다른 지역 후보로 채우지 않고 부족 안내를 반환합니다.
- API 키가 있으면 Kakao Local API로 실제 전국 장소 검색을 먼저 시도합니다.
- API 키가 없으면 `fallback_sample` 데이터만 사용합니다.

전국 위치 alias 데이터는 다음 구조를 따릅니다.

```json
{
  "대전": {
    "canonical_region": "대전",
    "city": "대전",
    "aliases": ["대전", "대전시", "대전광역시"],
    "areas": {
      "구암역": ["구암역", "대전 구암역", "구암역 근처", "구암역 앞"]
    },
    "districts": {
      "구암역": "유성구"
    },
    "coordinates": {
      "구암역": [36.3565, 127.3307]
    }
  }
}
```

실제 API 역할:

- Kakao Local API: 전국 장소 검색, 주소, 좌표, 전화번호, place_url
- Google Places Photo API: 실제 음식점 사진
- Leaflet/OpenStreetMap: API 키 없이 지도 렌더링

캐시 초기화:

```powershell
Remove-Item app\data\place_cache.json -ErrorAction SilentlyContinue
```

전국 테스트 예시:

- 대전 구암역 파스타
- 서울 홍대 초밥
- 부산 해운대 카페
- 제주 애월 파스타
- 전주 객사 저녁
