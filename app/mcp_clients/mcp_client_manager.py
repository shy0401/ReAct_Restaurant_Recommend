from __future__ import annotations

import logging
from typing import Any

from mcp_servers.memory_server import check_duplicate, get_recent_meals, save_meal_history
from mcp_servers.place_server import get_place_detail, get_place_menu, get_place_photos, get_static_map, search_real_places
from mcp_servers.restaurant_server import get_restaurant_detail, search_restaurants
from mcp_servers.weather_server import get_weather

logger = logging.getLogger(__name__)


class MCPClientManager:
    """Local MCP client facade.

    The project ships runnable MCP servers. For FastAPI/tests we call the same
    tool functions directly so the app works without managing subprocesses.
    """

    def __init__(self) -> None:
        self.servers = {
            "weather": {"status": "connected", "tools": ["get_weather"]},
            "restaurant": {"status": "connected", "tools": ["search_restaurants", "get_restaurant_detail"], "supports": ["nationwide_region_lock", "city", "district", "area", "landmark", "food_type", "menu_keyword", "price", "rating", "review_count"]},
            "memory": {"status": "connected", "tools": ["save_meal_history", "get_recent_meals", "check_duplicate"]},
            "place": {
                "status": "connected",
                "tools": ["search_real_places", "get_place_detail", "get_place_photos", "get_place_menu", "get_static_map"],
            },
        }

    async def call_tool(self, server: str, tool: str, arguments: dict[str, Any]) -> Any:
        logger.info("MCP tool call server=%s tool=%s arguments=%s", server, tool, arguments)
        try:
            if server == "weather" and tool == "get_weather":
                return get_weather(**arguments)
            if server == "restaurant" and tool == "search_restaurants":
                return search_restaurants(**arguments)
            if server == "restaurant" and tool == "get_restaurant_detail":
                return get_restaurant_detail(**arguments)
            if server == "memory" and tool == "save_meal_history":
                return save_meal_history(**arguments)
            if server == "memory" and tool == "get_recent_meals":
                return get_recent_meals()
            if server == "memory" and tool == "check_duplicate":
                return check_duplicate(**arguments)
            if server == "place" and tool == "search_real_places":
                return search_real_places(**arguments)
            if server == "place" and tool == "get_place_detail":
                return get_place_detail(**arguments)
            if server == "place" and tool == "get_place_photos":
                return get_place_photos(**arguments)
            if server == "place" and tool == "get_place_menu":
                return get_place_menu(**arguments)
            if server == "place" and tool == "get_static_map":
                return get_static_map(**arguments)
        except Exception as exc:
            logger.exception("MCP tool failed: %s.%s", server, tool)
            return _tool_failure_observation(server, tool, str(exc))
        return _tool_failure_observation(server, tool, f"Unknown MCP tool: {server}.{tool}")

    def status(self) -> dict[str, Any]:
        return {"servers": self.servers, "count": len(self.servers)}


def _tool_failure_observation(server: str, tool: str, message: str) -> dict[str, Any]:
    fallback_strategy = {
        "weather": "날씨 API 실패 시 fallback 날씨 데이터로 추천을 계속합니다.",
        "restaurant": "같은 지역 안에서 조건 완화 검색을 시도하고, 그래도 없으면 부족 안내를 반환합니다.",
        "memory": "현재 요청의 어제/오늘 메뉴 입력값만 사용해 중복 회피를 계속합니다.",
        "place": "장소 상세 API 실패 시 seed/fallback 상세 데이터와 기본 이미지를 사용합니다.",
    }.get(server, "가능한 fallback 데이터로 계속 진행하고 실패 사실을 Trace에 남깁니다.")
    return {
        "error": "tool_call_failed",
        "server": server,
        "tool": tool,
        "message": message,
        "fallback_strategy": fallback_strategy,
        "user_message": "일부 도구 호출에 실패했지만 가능한 fallback 전략으로 처리를 계속합니다.",
    }
