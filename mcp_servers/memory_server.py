from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None

MEMORY_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "meal_history.json"


def _read() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        return {"recent_meals": []}
    with MEMORY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write(data: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_meal_history(yesterday_menu: str, today_menu: str) -> dict[str, Any]:
    meals = [meal for meal in [yesterday_menu, today_menu] if meal]
    data = {"recent_meals": meals}
    _write(data)
    return {"saved": True, **data}


def get_recent_meals() -> dict[str, Any]:
    return _read()


def check_duplicate(menu: str, recent_meals: list[str]) -> dict[str, Any]:
    menu_n = (menu or "").replace(" ", "").lower()
    duplicates = []
    for recent in recent_meals:
        recent_n = recent.replace(" ", "").lower()
        if recent_n and (recent_n in menu_n or menu_n in recent_n):
            duplicates.append(recent)
        elif "면" in recent_n and any(token in menu_n for token in ["면", "라면", "우동", "파스타"]):
            duplicates.append(recent)
    return {"menu": menu, "is_duplicate": bool(duplicates), "duplicates": duplicates}


if FastMCP:
    mcp = FastMCP("Memory MCP Server")
    mcp.tool()(save_meal_history)
    mcp.tool()(get_recent_meals)
    mcp.tool()(check_duplicate)


if __name__ == "__main__":
    if not FastMCP:
        print("mcp package is not installed. Run: pip install -r requirements.txt")
    else:
        mcp.run()
