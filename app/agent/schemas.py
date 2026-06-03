from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    region: str = Field(..., min_length=1, examples=["대전"])
    city: str | None = Field(default=None, examples=["대전"])
    district: str | None = Field(default=None, examples=["유성구"])
    area: str | None = Field(default=None, examples=["구암역"])
    landmark: str | None = Field(default=None, examples=["구암역"])
    latitude: float | None = Field(default=None, examples=[36.3565])
    longitude: float | None = Field(default=None, examples=[127.3307])
    location_source: str | None = Field(default=None, examples=["local_alias"])
    location_confidence: float | None = Field(default=None, examples=[0.92])
    yesterday_menu: str = Field(..., min_length=1, examples=["치킨"])
    today_menu: str = Field(..., min_length=1, examples=["라면"])
    weather: str | None = Field(default=None, examples=[None, "비"])
    preference: str = Field(..., min_length=1, examples=["양식, 파스타"])
    food_type: str | None = Field(default=None, examples=["양식"])
    menu_keyword: str | None = Field(default=None, examples=["파스타"])
    max_price: int | None = Field(default=None, examples=[15000])
    min_rating: float | None = Field(default=None, examples=[4.0])
    min_review_count: int | None = Field(default=None, examples=[50])
    top_k: int = Field(default=3, ge=1, le=10)
    purpose: str | None = Field(default=None, examples=["저녁"])
    companion: str | None = Field(default=None, examples=["친구"])
    needs_clarification: bool = False
    clarification_reason: str | None = None
    error_code: str | None = None
    suggested_queries: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReActTraceStep(BaseModel):
    thought: str
    action: str
    action_input: dict[str, Any]
    observation: Any


class RecommendationItem(BaseModel):
    id: str
    place_id: str | None = None
    name: str
    region: str
    city: str | None = None
    district: str | None = None
    area: str | None = None
    category: str
    menu: list[str]
    menus: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str]
    weather_match: list[str]
    photos: list[dict[str, Any]] = Field(default_factory=list)
    price_range: str
    rating: float
    address: str
    road_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    thumbnail_url: str | None = None
    thumbnail_source: str | None = None
    thumbnail_is_fallback: bool = True
    map_url: str | None = None
    place_url: str | None = None
    quick_view_available: bool = True
    phone: str | None = None
    opening_hours: str | None = None
    review_count: int | None = None
    distance: str | None = None
    distance_km: float | None = None
    source: str | None = None
    reason: str
    score: float
    weather_relation: str
    recent_menu_relation: str
    preference_relation: str
    reflection_result: str | None = None


class ReflectionResult(BaseModel):
    approved: bool
    score: int
    issues: list[str]
    checked_items: list[str] = Field(default_factory=list)
    improvement_instruction: str
    summary: str
    final_changes: list[str] = Field(default_factory=list)


class PlaceMenuItem(BaseModel):
    name: str
    price: str = "가격 정보 없음"
    description: str = ""
    is_recommended: bool = False


class PlacePhoto(BaseModel):
    url: str
    alt: str
    source: str = "fallback"
    is_fallback: bool = True
    attributions: list[str] = Field(default_factory=list)


class PlaceDetail(BaseModel):
    id: str
    name: str
    category: str | None = None
    region: str | None = None
    city: str | None = None
    district: str | None = None
    area: str | None = None
    address: str | None = None
    road_address: str | None = None
    phone: str | None = None
    rating: float | None = None
    review_count: int | None = None
    price_range: str | None = None
    opening_hours: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance: str | None = None
    place_url: str | None = None
    map_url: str | None = None
    static_map_url: str | None = None
    menus: list[PlaceMenuItem] = Field(default_factory=list)
    photos: list[PlacePhoto] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source: str = "fallback"
    fallback_messages: list[str] = Field(default_factory=list)


class PlaceDetailResponse(BaseModel):
    place: PlaceDetail
    source: str
    fetched_at: str


class PlaceQuickViewRequest(BaseModel):
    place_id: str
    name: str | None = None
    region: str | None = None


class PlaceQuickViewResponse(BaseModel):
    place: PlaceDetail
    menus: list[PlaceMenuItem]
    photos: list[PlacePhoto]
    map: dict[str, Any]
    source: str
    fetched_at: str


class RecommendationResponse(BaseModel):
    input: RecommendationRequest
    plan_steps: list[str] = Field(default_factory=list)
    weather: dict[str, Any]
    react_trace: list[ReActTraceStep]
    draft_recommendations: list[RecommendationItem]
    reflection: ReflectionResult
    final_recommendations: list[RecommendationItem]


class NaturalLanguageRecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    yesterday_menu: str | None = "입력 없음"
    today_menu: str | None = "입력 없음"
    weather: str | None = None


class ParsedRecommendationConditions(BaseModel):
    region: str
    city: str | None = None
    district: str | None = None
    area: str | None = None
    landmark: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_source: str | None = None
    location_confidence: float | None = None
    food_type: str | None = None
    menu_keyword: str | None = None
    preference: str
    purpose: str | None = None
    companion: str | None = None
    budget_level: str | None = None
    max_price: int | None = None
    min_rating: float | None = None
    min_review_count: int | None = None
    top_k: int = 3
    warnings: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_reason: str | None = None
    error_code: str | None = None
    suggested_queries: list[str] = Field(default_factory=list)


class NaturalLanguageRecommendationResponse(BaseModel):
    query: str
    parsed_conditions: ParsedRecommendationConditions
    result: RecommendationResponse
    submission_trace_text: str
