# 외부 API 사용 방법

이 프로젝트는 외부 API Key가 없어도 `fallback_sample` 데이터셋으로 실행됩니다. 실제 장소 정보나 사진을 더 풍부하게 쓰려면 아래 API Key를 설정할 수 있습니다.

실제 `.env` 파일은 절대 커밋하지 마세요. 제출 시에는 `.env.example`만 포함합니다.

## 1. 백엔드 환경 변수

`.env.example`을 복사해 `.env`를 만듭니다.

```powershell
Copy-Item .env.example .env
```

기본 실행:

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

## 2. 프론트엔드 환경 변수

`frontend/.env.example`을 복사해 `frontend/.env`를 만듭니다.

```powershell
Copy-Item frontend\.env.example frontend\.env
```

기본 실행:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_MAP_PROVIDER=leaflet
VITE_KAKAO_JAVASCRIPT_KEY=
```

## 3. Kakao Local API

용도:

- 전국 장소 검색
- 장소명, 주소, 도로명 주소, 좌표, 전화번호, Kakao place_url 보강

설정:

```env
USE_REAL_PLACE_API=true
KAKAO_REST_API_KEY=
```

위 값에 발급받은 Kakao REST API Key를 입력합니다.

주의:

- Kakao Local REST API Key는 백엔드에서 사용합니다.
- Kakao Local API는 실제 음식점 사진과 메뉴 이미지를 안정적으로 제공하지 않습니다.
- 응답의 `x`는 longitude, `y`는 latitude로 변환합니다.

적용 위치:

- `app/services/kakao_local_service.py`
- `app/services/location_resolver.py`
- `mcp_servers/restaurant_server.py`
- `mcp_servers/place_server.py`

## 4. Naver Search API

용도:

- 향후 장소 검색 보강용 환경 변수를 제공합니다.

설정:

```env
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```

위 값에 발급받은 Naver Client ID와 Client Secret을 입력합니다.

현재 기본 추천 흐름은 Kakao Local API를 시도할 수 있고, Key가 없거나 실패하면 fallback_sample을 사용합니다.

## 5. Google Places API

용도:

- 실제 음식점 사진 조회
- Google Places Photo API를 통한 이미지 프록시 제공

설정:

```env
USE_REAL_PLACE_API=true
GOOGLE_PLACES_API_KEY=
BACKEND_PUBLIC_URL=http://localhost:8000
```

위 값에 발급받은 Google Places API Key를 입력합니다.

주의:

- Google API Key는 프론트엔드에 노출하지 않습니다.
- 프론트엔드는 `/places/photo` 백엔드 프록시 URL만 사용합니다.
- 실제 사진이 없거나 Key가 없으면 fallback 이미지가 표시되며, UI에 기본 이미지임을 표시합니다.

적용 위치:

- `app/services/google_places_service.py`
- `mcp_servers/place_server.py`
- `app/main.py`의 `/places/photo`

## 6. Open-Meteo

용도:

- 날씨 API 모드에서 지역별 날씨 조회

설정:

```env
WEATHER_API_MODE=open-meteo
```

기본값:

```env
WEATHER_API_MODE=fallback
```

fallback 모드에서는 네트워크 없이도 날씨 Observation이 생성됩니다.

적용 위치:

- `mcp_servers/weather_server.py`

## 7. Kakao Maps JavaScript SDK

용도:

- 브라우저에서 Kakao 지도 렌더링

설정:

```env
VITE_MAP_PROVIDER=kakao
VITE_KAKAO_JAVASCRIPT_KEY=발급받은_KAKAO_JS_KEY
```

주의:

- Kakao JavaScript Key는 프론트엔드에서 지도 SDK 로딩에 사용합니다.
- Kakao REST API Key와 JavaScript Key는 서로 다릅니다.
- Key가 없으면 Leaflet + OpenStreetMap으로 자동 fallback됩니다.

## 8. API Key 없이 실행할 때

API Key가 없을 때 동작:

- `Restaurant MCP`: `USE_REAL_PLACE_API=true`여도 Kakao Key가 없으면 `app/data/restaurants.json`의 `fallback_sample` 사용
- `Place MCP`: seed 상세 정보, placeholder 이미지, OpenStreetMap 지도 URL 사용
- `Weather MCP`: fallback 날씨 사용
- `Google Places`: 실제 사진 없음 안내와 기본 이미지 표시

이 fallback은 오류가 아니라 API Key 없는 상태의 정상 동작입니다.

## 9. 캐시 초기화

장소 상세 캐시가 꼬였거나 API Key 설정을 바꾼 경우 캐시를 삭제합니다.

```powershell
Remove-Item app\data\place_cache.json -ErrorAction SilentlyContinue
```
