from __future__ import annotations

import logging
import os
from typing import Any

from app.agent.reflection import reflection_check
from app.agent.schemas import RecommendationItem, RecommendationRequest, RecommendationResponse, ReActTraceStep
from app.mcp_clients.mcp_client_manager import MCPClientManager
from app.services.scoring import (
    MENU_KEYWORD_TO_TYPE,
    enrich_recommendation,
    is_hard_mismatch,
    is_similar_menu,
    score_restaurant,
)

logger = logging.getLogger(__name__)


PLAN_STEPS = [
    "1. 사용자 요청에서 지역, 도시, 구/군, 세부 위치와 랜드마크를 분석한다.",
    "2. 음식 종류, 원하는 메뉴, 방문 목적, 가격대, 리뷰 조건을 추출한다.",
    "3. Weather MCP로 날씨를 확인하되 명시 메뉴/음식 종류를 덮어쓰지 않는다.",
    "4. Memory MCP로 최근 식사 기록을 확인한다.",
    "5. Restaurant MCP로 지역, 도시, 세부 위치, 메뉴/음식 종류 조건을 우선 검색한다.",
    "6. 후보가 부족하면 같은 지역/도시 안에서만 가격, 리뷰, 세부 위치 순서로 완화한다.",
    "7. 지역/메뉴/음식 종류 하드 미스매치 후보를 제거하고 점수를 계산한다.",
    "8. Place MCP로 메뉴, 사진, 지도 정보를 보강한다.",
    "9. Reflection으로 지역, 위치, 메뉴, 가격, 리뷰, 지도/사진 정보를 검토한다.",
    "10. 최종 추천을 출력한다.",
]


class FoodReActAgent:
    def __init__(self, mcp_manager: MCPClientManager) -> None:
        self.mcp = mcp_manager
        self.use_llm = os.getenv("USE_LLM", "false").lower() == "true" and bool(os.getenv("OPENAI_API_KEY"))

    async def _act(self, trace: list[ReActTraceStep], thought: str, action: str, action_input: dict[str, Any]) -> Any:
        try:
            server, tool = action.split(".", 1)
            observation = await self.mcp.call_tool(server, tool, action_input)
        except Exception as exc:
            observation = {
                "error": "tool_call_failed",
                "action": action,
                "message": str(exc),
                "fallback_strategy": "가능한 경우 같은 지역 안에서만 조건을 완화해 다시 검색합니다.",
            }
            logger.exception("Tool call failed: %s", action)
        trace.append(ReActTraceStep(thought=thought, action=action, action_input=action_input, observation=observation))
        return observation

    def _choose_food_type(self, request: RecommendationRequest, weather: dict[str, Any], recent_meals: list[str]) -> str | None:
        if request.food_type:
            return request.food_type
        if request.menu_keyword:
            inferred = MENU_KEYWORD_TO_TYPE.get(request.menu_keyword)
            if inferred:
                return inferred
        if request.preference:
            for token in ["한식", "중식", "일식", "양식", "분식", "카페", "고기", "국물", "매운 음식"]:
                if token in request.preference:
                    return token
        condition = weather.get("condition", "")
        if not request.menu_keyword and condition in {"비", "흐림", "추움", "눈"}:
            return "국물"
        if "라면" in recent_meals or "면" in " ".join(recent_meals):
            return None
        return None

    def _extract_candidate_items(self, observation: Any) -> tuple[list[dict], list[dict]]:
        if isinstance(observation, dict):
            return [], [observation]
        if not isinstance(observation, list):
            return [], [{"error": "invalid_observation", "message": "Restaurant MCP 응답 형식이 list가 아닙니다."}]
        metadata = [item for item in observation if isinstance(item, dict) and ("warning" in item or "error" in item)]
        items = [item for item in observation if isinstance(item, dict) and item.get("id")]
        return items, metadata

    def _rank(self, candidates: list[dict], request: RecommendationRequest, weather: dict[str, Any]) -> list[dict]:
        recent_meals = [request.yesterday_menu, request.today_menu]
        condition = weather.get("condition", request.weather or "맑음")
        ranked = []
        for item in candidates:
            score = score_restaurant(
                item,
                region=request.region,
                city=request.city,
                landmark=request.landmark,
                weather_condition=condition,
                recent_meals=recent_meals,
                preference=request.preference,
                max_price=request.max_price,
                min_rating=request.min_rating,
                min_review_count=request.min_review_count,
                area=request.area,
                food_type=request.food_type,
                menu_keyword=request.menu_keyword,
            )
            ranked.append(
                enrich_recommendation(
                    item,
                    score=score,
                    weather_condition=condition,
                    recent_meals=recent_meals,
                    preference=request.preference,
                    max_price=request.max_price,
                    min_rating=request.min_rating,
                    min_review_count=request.min_review_count,
                    purpose=request.purpose,
                    companion=request.companion,
                )
            )
        return sorted(ranked, key=lambda item: item["score"], reverse=True)

    def _dedupe(self, items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        deduped: list[dict] = []
        for item in items:
            item_id = item.get("id") or item.get("place_id") or item.get("name")
            if item_id not in seen:
                deduped.append(item)
                seen.add(item_id)
        return deduped

    async def _attach_place_details(self, trace: list[ReActTraceStep], items: list[dict]) -> list[dict]:
        detailed_items = []
        for item in items:
            detail = await self._act(
                trace,
                "추천 맛집의 실제 메뉴, 사진, 지도 좌표를 확인해야 하므로 Place MCP를 호출한다.",
                "place.get_place_detail",
                {"place_id": item.get("place_id") or item.get("id"), "name": item.get("name"), "region": item.get("region")},
            )
            if not isinstance(detail, dict) or detail.get("error"):
                detail = {}
            photos = detail.get("photos") or item.get("photos") or []
            first_photo = photos[0] if photos else {}
            if trace:
                trace[-1].observation = {
                    "place_id": detail.get("id") or item.get("id"),
                    "photos_found": len([photo for photo in photos if not photo.get("is_fallback", True)]),
                    "photo_source": first_photo.get("source", "fallback"),
                    "photo_is_fallback": first_photo.get("is_fallback", True),
                    "has_coordinates": detail.get("latitude", item.get("latitude")) is not None
                    and detail.get("longitude", item.get("longitude")) is not None,
                    "map_provider": "kakao" if os.getenv("MAP_PROVIDER", "leaflet").lower() == "kakao" else "leaflet",
                    "source": detail.get("source", item.get("source", "fallback")),
                }
            merged = {
                **item,
                "place_id": detail.get("id") or item.get("place_id") or item.get("id"),
                "city": detail.get("city") or item.get("city"),
                "district": detail.get("district") or item.get("district"),
                "area": detail.get("area") or item.get("area"),
                "address": detail.get("address") or item.get("address"),
                "road_address": detail.get("road_address") or item.get("road_address") or item.get("address"),
                "latitude": detail.get("latitude", item.get("latitude")),
                "longitude": detail.get("longitude", item.get("longitude")),
                "thumbnail_url": first_photo.get("url") if first_photo else item.get("thumbnail_url"),
                "thumbnail_source": first_photo.get("source", "fallback") if first_photo else item.get("thumbnail_source", "fallback"),
                "thumbnail_is_fallback": first_photo.get("is_fallback", True) if first_photo else item.get("thumbnail_is_fallback", True),
                "map_url": detail.get("map_url") or item.get("map_url"),
                "place_url": detail.get("place_url") or item.get("place_url"),
                "menus": detail.get("menus") or item.get("menus") or [],
                "photos": photos,
                "phone": detail.get("phone") or item.get("phone"),
                "opening_hours": detail.get("opening_hours") or item.get("opening_hours"),
                "review_count": detail.get("review_count", item.get("review_count")),
                "distance": detail.get("distance") or item.get("distance"),
                "source": detail.get("source") or item.get("source") or "fallback",
                "quick_view_available": True,
            }
            detailed_items.append(merged)
        return detailed_items

    async def _restaurant_search(
        self,
        trace: list[ReActTraceStep],
        request: RecommendationRequest,
        *,
        thought: str,
        area: str | None,
        max_price: int | None,
        min_rating: float | None,
        min_review_count: int | None,
        food_type: str | None,
        menu_keyword: str | None,
    ) -> tuple[list[dict], list[dict]]:
        observation = await self._act(
            trace,
            thought,
            "restaurant.search_restaurants",
            {
                "region": request.region,
                "city": request.city,
                "district": request.district,
                "area": area,
                "landmark": request.landmark,
                "latitude": request.latitude,
                "longitude": request.longitude,
                "food_type": food_type,
                "menu_keyword": menu_keyword,
                "preference": request.preference,
                "max_price": max_price,
                "min_rating": min_rating,
                "min_review_count": min_review_count,
                "limit": max(request.top_k * 3, 10),
            },
        )
        return self._extract_candidate_items(observation)

    async def _search_candidates(self, trace: list[ReActTraceStep], request: RecommendationRequest, food_type: str | None) -> tuple[list[dict], list[dict]]:
        stages = [
            ("지역, 도시, 세부 위치, 메뉴/음식 종류, 가격, 리뷰 조건을 모두 반영해 Restaurant MCP에서 후보를 검색한다.", request.area, request.max_price, request.min_rating, request.min_review_count, food_type, request.menu_keyword),
            ("후보가 부족하면 같은 지역/도시와 세부 위치, 메뉴/음식 종류는 유지하고 가격/리뷰 조건만 완화한다.", request.area, None, None, None, food_type, request.menu_keyword),
            ("후보가 여전히 부족하면 같은 지역/도시 안에서 메뉴/음식 종류를 유지하고 세부 위치만 완화한다.", None, None, None, None, food_type, request.menu_keyword),
            ("메뉴 후보가 부족한 경우 같은 지역/도시의 음식 종류 후보까지만 확장한다. 다른 지역이나 무관한 음식은 넣지 않는다.", None, None, None, None, food_type, None if request.menu_keyword else request.menu_keyword),
        ]

        all_candidates: list[dict] = []
        all_metadata: list[dict] = []
        for thought, area, max_price, min_rating, min_review_count, stage_food_type, stage_menu_keyword in stages:
            candidates, metadata = await self._restaurant_search(
                trace,
                request,
                thought=thought,
                area=area,
                max_price=max_price,
                min_rating=min_rating,
                min_review_count=min_review_count,
                food_type=stage_food_type,
                menu_keyword=stage_menu_keyword,
            )
            all_metadata.extend(metadata)
            all_candidates = self._dedupe([*all_candidates, *candidates])
            hard_valid = [item for item in all_candidates if not is_hard_mismatch(item, request)]
            if len(hard_valid) >= request.top_k:
                return hard_valid, all_metadata
        hard_valid = [item for item in all_candidates if not is_hard_mismatch(item, request)]
        return hard_valid, all_metadata

    def _filter_final_pool(self, trace: list[ReActTraceStep], items: list[dict], request: RecommendationRequest, recent_meals: list[str]) -> list[dict]:
        removed = [item.get("name") for item in items if is_hard_mismatch(item, request)]
        filtered = [item for item in items if not is_hard_mismatch(item, request)]
        if removed:
            trace.append(
                ReActTraceStep(
                    thought="최종 추천 직전 지역/메뉴/음식 종류 불일치 후보를 제거한다.",
                    action="agent.filter_region_mismatch",
                    action_input={"region": request.region, "city": request.city, "food_type": request.food_type, "menu_keyword": request.menu_keyword},
                    observation={"removed": removed, "reason": "요청 지역 또는 명시 메뉴/음식 종류와 다른 후보"},
                )
            )
        non_duplicate = [
            item for item in filtered if not any(is_similar_menu(menu, recent_meals) for menu in item.get("menu", []))
        ]
        return non_duplicate or filtered

    async def run(self, request: RecommendationRequest, initial_trace: list[ReActTraceStep] | None = None) -> RecommendationResponse:
        trace: list[ReActTraceStep] = list(initial_trace or [])
        recent_meals = [request.yesterday_menu, request.today_menu]
        top_k = max(1, request.top_k or 3)

        trace.append(
            ReActTraceStep(
                thought="Plan-and-Solve 패턴으로 추천에 필요한 하위 단계를 먼저 계획한다.",
                action="agent.plan_steps",
                action_input={
                    "region": request.region,
                    "city": request.city,
                    "district": request.district,
                    "area": request.area,
                    "landmark": request.landmark,
                    "food_type": request.food_type,
                    "menu_keyword": request.menu_keyword,
                    "top_k": top_k,
                },
                observation=PLAN_STEPS,
            )
        )

        if request.weather:
            weather = {
                "region": request.region,
                "condition": request.weather,
                "temperature": None,
                "humidity": None,
                "recommendation_hint": f"사용자가 직접 입력한 날씨({request.weather})를 보조 조건으로 반영합니다.",
                "source": "user_input",
            }
            trace.append(
                ReActTraceStep(
                    thought="사용자가 날씨를 직접 입력했으므로 Weather MCP 조회 없이 입력값을 Observation으로 사용한다.",
                    action="weather.user_input",
                    action_input={"region": request.region, "weather": request.weather},
                    observation=weather,
                )
            )
        else:
            weather = await self._act(trace, "지역 기반 날씨가 필요하므로 Weather MCP 서버를 호출한다.", "weather.get_weather", {"region": request.region})
            if not isinstance(weather, dict) or weather.get("error"):
                weather = {"region": request.region, "condition": "맑음", "temperature": None, "humidity": None, "recommendation_hint": "날씨 조회 실패로 기본 날씨를 사용합니다.", "source": "fallback_after_error"}

        await self._act(trace, "어제와 오늘 먹은 메뉴를 Memory MCP에 저장해 중복 추천을 피한다.", "memory.save_meal_history", {"yesterday_menu": request.yesterday_menu, "today_menu": request.today_menu})

        food_type = self._choose_food_type(request, weather, recent_meals)
        if request.food_type != food_type:
            request = request.model_copy(update={"food_type": food_type})

        candidates, search_metadata = await self._search_candidates(trace, request, food_type)
        ranked_pool = self._rank(candidates, request, weather)
        filtered_pool = self._filter_final_pool(trace, ranked_pool, request, recent_meals)
        draft = await self._attach_place_details(trace, filtered_pool[:top_k])

        trace.append(
            ReActTraceStep(
                thought="후보별 점수를 계산하고 하드 미스매치 후보를 제거한 뒤 추천 초안을 만든다.",
                action="agent.score_and_draft",
                action_input={"candidate_count": len(candidates), "top_k": top_k, "priority": "region/city > area/landmark > menu_keyword > food_type > price > rating/review > weather > recent meals", "search_metadata": search_metadata},
                observation=[{"name": item["name"], "score": item["score"], "price_range": item.get("price_range")} for item in draft],
            )
        )

        reflection = reflection_check(
            draft,
            region=request.region,
            city=request.city,
            district=request.district,
            landmark=request.landmark,
            weather_condition=weather.get("condition", request.weather or "맑음"),
            recent_meals=recent_meals,
            preference=request.preference,
            max_price=request.max_price,
            min_rating=request.min_rating,
            min_review_count=request.min_review_count,
            area=request.area,
            food_type=request.food_type,
            menu_keyword=request.menu_keyword,
            purpose=request.purpose,
            companion=request.companion,
        )

        final = draft
        if not reflection.approved:
            cleaned_pool = self._filter_final_pool(trace, filtered_pool or ranked_pool, request, recent_meals)
            final = await self._attach_place_details(trace, cleaned_pool[:top_k])
            trace.append(
                ReActTraceStep(
                    thought="Reflection에서 문제를 발견해 하드 미스매치 후보를 제거하고 같은 조건 안에서 다시 정렬한다.",
                    action="reflection.re_rank",
                    action_input={"issues": reflection.issues, "instruction": reflection.improvement_instruction},
                    observation=[{"name": item["name"], "score": item["score"]} for item in final],
                )
            )
            reflection = reflection_check(
                final,
                region=request.region,
                city=request.city,
                district=request.district,
                landmark=request.landmark,
                weather_condition=weather.get("condition", request.weather or "맑음"),
                recent_meals=recent_meals,
                preference=request.preference,
                max_price=request.max_price,
                min_rating=request.min_rating,
                min_review_count=request.min_review_count,
                area=request.area,
                food_type=request.food_type,
                menu_keyword=request.menu_keyword,
                purpose=request.purpose,
                companion=request.companion,
            )

        if len(final) < top_k:
            trace.append(
                ReActTraceStep(
                    thought="조건에 맞는 후보가 요청 개수보다 적어 다른 지역 후보로 채우지 않고 부족 사실을 명확히 남긴다.",
                    action="agent.shortage_notice",
                    action_input={"requested_top_k": top_k, "final_count": len(final), "region": request.region, "city": request.city, "area": request.area, "menu_keyword": request.menu_keyword, "food_type": request.food_type},
                    observation={"warning": "not_enough_strict_candidates", "message": f"{request.region} {request.area or request.landmark or ''} {request.menu_keyword or request.food_type or ''} 조건을 만족하는 후보가 부족해 조건에 맞는 후보만 반환합니다."},
                )
            )

        for item in final:
            item["reflection_result"] = reflection.summary
        for item in draft:
            item["reflection_result"] = reflection.summary

        return RecommendationResponse(
            input=request,
            plan_steps=PLAN_STEPS,
            weather=weather,
            react_trace=trace,
            draft_recommendations=[RecommendationItem(**item) for item in draft],
            reflection=reflection,
            final_recommendations=[RecommendationItem(**item) for item in final],
        )
