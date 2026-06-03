from __future__ import annotations

import os
import random
from typing import Any

import requests

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None


REGION_COORDS = {
    "전주": (35.8242, 127.1480),
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대전": (36.3504, 127.3845),
    "대구": (35.8714, 128.6014),
    "광주": (35.1595, 126.8526),
}

FALLBACK_WEATHER = {
    "전주": {"condition": "비", "temperature": 22, "humidity": 78},
    "서울": {"condition": "흐림", "temperature": 21, "humidity": 70},
    "부산": {"condition": "맑음", "temperature": 24, "humidity": 65},
    "대전": {"condition": "흐림", "temperature": 23, "humidity": 68},
    "대구": {"condition": "더움", "temperature": 29, "humidity": 55},
    "광주": {"condition": "맑음", "temperature": 25, "humidity": 60},
}


def _hint(condition: str) -> str:
    if condition in {"비", "흐림", "추움", "눈"}:
        return "비 오거나 쌀쌀한 날에는 국물 음식이나 따뜻한 메뉴를 추천합니다."
    if condition == "더움":
        return "더운 날에는 가벼운 음식이나 시원한 면 요리를 추천합니다."
    return "맑은 날에는 지역 대표 메뉴나 걷기 좋은 동선의 맛집을 추천합니다."


def _condition_from_code(code: int, temp: float) -> str:
    if code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "비"
    if code in {71, 73, 75, 77, 85, 86}:
        return "눈"
    if temp <= 8:
        return "추움"
    if temp >= 28:
        return "더움"
    if code in {1, 2, 3, 45, 48}:
        return "흐림"
    return "맑음"


def get_weather(region: str) -> dict[str, Any]:
    mode = os.getenv("WEATHER_API_MODE", "fallback").lower()
    base = FALLBACK_WEATHER.get(region, random.choice(list(FALLBACK_WEATHER.values()))).copy()
    source = "fallback"

    if mode == "open-meteo" and region in REGION_COORDS:
        lat, lon = REGION_COORDS[region]
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon, "current_weather": "true", "hourly": "relative_humidity_2m"},
                timeout=3,
            )
            response.raise_for_status()
            payload = response.json()
            current = payload.get("current_weather", {})
            temp = float(current.get("temperature", base["temperature"]))
            code = int(current.get("weathercode", 0))
            base.update({"condition": _condition_from_code(code, temp), "temperature": temp})
            source = "open-meteo"
        except Exception:
            source = "fallback_after_network_error"

    return {
        "region": region,
        "condition": base["condition"],
        "temperature": base["temperature"],
        "humidity": base["humidity"],
        "recommendation_hint": _hint(base["condition"]),
        "source": source,
    }


if FastMCP:
    mcp = FastMCP("Weather MCP Server")
    mcp.tool()(get_weather)


if __name__ == "__main__":
    if not FastMCP:
        print("mcp package is not installed. Run: pip install -r requirements.txt")
    else:
        mcp.run()
