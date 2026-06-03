from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from app.agent.schemas import (
    NaturalLanguageRecommendationRequest,
    NaturalLanguageRecommendationResponse,
    PlaceDetailResponse,
    PlaceQuickViewRequest,
    PlaceQuickViewResponse,
    ReActTraceStep,
    RecommendationRequest,
    RecommendationResponse,
)
from app.mcp_clients.mcp_client_manager import MCPClientManager
from app.services.google_places_service import fetch_google_photo
from app.services.query_parser import parse_recommendation_query
from app.services.recommendation_service import RecommendationService
from app.services.submission_trace import build_submission_trace_text

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "").split(",") if origin.strip()]

app = FastAPI(title="오늘 뭐 먹지 AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins + extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp_manager = MCPClientManager()
service = RecommendationService(mcp_manager)


@app.get("/health")
async def health() -> dict:
    use_llm = os.getenv("USE_LLM", "false").lower() == "true" and bool(os.getenv("OPENAI_API_KEY"))
    return {"status": "ok", "service": "food-recommend-agent", "use_llm": use_llm, "mode": "llm" if use_llm else "rule-based"}


@app.get("/mcp/status")
async def mcp_status() -> dict:
    return mcp_manager.status()


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest) -> RecommendationResponse:
    return await service.recommend(request)


@app.post("/agent/run", response_model=NaturalLanguageRecommendationResponse)
async def run_agent(request: NaturalLanguageRecommendationRequest) -> NaturalLanguageRecommendationResponse:
    parsed = parse_recommendation_query(request.query)
    initial_trace = [
        ReActTraceStep(
            thought="자연어 요청을 구조화된 추천 조건으로 변환해야 하므로 query parser를 실행한다.",
            action="agent.parse_user_query",
            action_input={"query": request.query},
            observation=parsed.model_dump(),
        )
    ]
    recommendation_request = RecommendationRequest(
        region=parsed.region,
        city=parsed.city,
        district=parsed.district,
        area=parsed.area,
        landmark=parsed.landmark,
        latitude=parsed.latitude,
        longitude=parsed.longitude,
        location_source=parsed.location_source,
        location_confidence=parsed.location_confidence,
        food_type=parsed.food_type,
        menu_keyword=parsed.menu_keyword,
        yesterday_menu=request.yesterday_menu or "입력 없음",
        today_menu=request.today_menu or "입력 없음",
        weather=request.weather,
        preference=parsed.preference,
        max_price=parsed.max_price,
        min_rating=parsed.min_rating,
        min_review_count=parsed.min_review_count,
        top_k=parsed.top_k,
        purpose=parsed.purpose,
        companion=parsed.companion,
        needs_clarification=parsed.needs_clarification,
        clarification_reason=parsed.clarification_reason,
        error_code=parsed.error_code,
        suggested_queries=parsed.suggested_queries,
        warnings=parsed.warnings,
    )
    result = await service.recommend(recommendation_request, initial_trace=initial_trace)
    trace_text = build_submission_trace_text(query=request.query, parsed_conditions=parsed, result=result)
    return NaturalLanguageRecommendationResponse(
        query=request.query,
        parsed_conditions=parsed,
        result=result,
        submission_trace_text=trace_text,
    )


@app.get("/places/{place_id}", response_model=PlaceDetailResponse)
async def get_place(place_id: str, name: str | None = None, region: str | None = None) -> PlaceDetailResponse:
    place = await mcp_manager.call_tool("place", "get_place_detail", {"place_id": place_id, "name": name, "region": region})
    return PlaceDetailResponse(place=place, source=place.get("source", "fallback"), fetched_at=datetime.now(timezone.utc).isoformat())


@app.post("/places/quick-view", response_model=PlaceQuickViewResponse)
async def quick_view(request: PlaceQuickViewRequest) -> PlaceQuickViewResponse:
    place = await mcp_manager.call_tool(
        "place",
        "get_place_detail",
        {"place_id": request.place_id, "name": request.name, "region": request.region},
    )
    latitude = _to_float(place.get("latitude"))
    longitude = _to_float(place.get("longitude"))
    map_url = _osm_url(latitude, longitude) or place.get("map_url")
    directions_url = _directions_url(latitude, longitude)
    map_provider = "kakao" if os.getenv("MAP_PROVIDER", "leaflet").lower() == "kakao" else "leaflet"
    map_payload = {
        "latitude": latitude,
        "longitude": longitude,
        "map_url": map_url,
        "directions_url": directions_url,
        "provider": map_provider,
        "has_coordinates": latitude is not None and longitude is not None,
    }
    if latitude is not None and longitude is not None:
        static_map = await mcp_manager.call_tool(
            "place",
            "get_static_map",
            {"latitude": latitude, "longitude": longitude, "name": place.get("name") or request.name or ""},
        )
        map_payload.update(static_map)
    return PlaceQuickViewResponse(
        place=place,
        menus=place.get("menus", []),
        photos=place.get("photos", []),
        map=map_payload,
        source=place.get("source", "fallback"),
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/places/photo")
async def place_photo(
    photo_name: str | None = None,
    photo_reference: str | None = None,
    max_width: int = Query(default=800, ge=100, le=1600),
) -> StreamingResponse:
    response = fetch_google_photo(photo_name=photo_name, photo_reference=photo_reference, max_width=max_width)
    if not response:
        raise HTTPException(status_code=404, detail="Google Places photo not available")
    content_type = response.headers.get("content-type", "image/jpeg")
    return StreamingResponse(response.iter_content(chunk_size=8192), media_type=content_type)


def _to_float(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _osm_url(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=17/{latitude}/{longitude}"


def _directions_url(latitude: float | None, longitude: float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return f"https://www.openstreetmap.org/directions?from=&to={latitude}%2C{longitude}"
