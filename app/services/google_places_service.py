from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import requests


GOOGLE_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
GOOGLE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
GOOGLE_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"


def _api_key() -> str | None:
    return os.getenv("GOOGLE_PLACES_API_KEY") or None


def _backend_public_url() -> str:
    return os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")


def search_google_place(name: str, region: str, address: str | None = None) -> dict[str, Any] | None:
    key = _api_key()
    if not key:
        return None
    query = " ".join(part for part in [region, name, address] if part)
    try:
        response = requests.get(
            GOOGLE_TEXT_SEARCH_URL,
            params={"query": query, "key": key, "language": "ko"},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0] if results else None
    except Exception:
        return None


def get_google_place_photos(place_id: str | None = None, *, max_results: int = 5) -> list[dict[str, Any]]:
    key = _api_key()
    if not key or not place_id:
        return []
    try:
        response = requests.get(
            GOOGLE_DETAILS_URL,
            params={"place_id": place_id, "fields": "photos,name", "key": key, "language": "ko"},
            timeout=5,
        )
        response.raise_for_status()
        photos = response.json().get("result", {}).get("photos", [])
    except Exception:
        return []
    return [_photo_payload(photo) for photo in photos[:max_results] if photo.get("photo_reference")]


def get_google_photos_for_place(name: str, region: str, address: str | None = None) -> list[dict[str, Any]]:
    place = search_google_place(name, region, address)
    if not place:
        return []
    photos = place.get("photos") or []
    if photos:
        return [_photo_payload(photo) for photo in photos[:5] if photo.get("photo_reference")]
    return get_google_place_photos(place.get("place_id"))


def _photo_payload(photo: dict[str, Any]) -> dict[str, Any]:
    reference = photo.get("photo_reference")
    return {
        "url": build_photo_proxy_url(photo_reference=reference),
        "alt": "Google Places 음식점 대표 사진",
        "source": "google_places",
        "is_fallback": False,
        "attributions": photo.get("html_attributions") or [],
    }


def build_photo_proxy_url(photo_name: str | None = None, photo_reference: str | None = None, max_width: int = 800) -> str:
    params = []
    if photo_name:
        params.append(f"photo_name={quote(photo_name, safe='')}")
    if photo_reference:
        params.append(f"photo_reference={quote(photo_reference, safe='')}")
    params.append(f"max_width={int(max_width)}")
    return f"{_backend_public_url()}/places/photo?{'&'.join(params)}"


def fetch_google_photo(photo_name: str | None = None, photo_reference: str | None = None, max_width: int = 800) -> requests.Response | None:
    key = _api_key()
    if not key:
        return None
    params: dict[str, Any] = {"key": key, "maxwidth": max_width}
    if photo_reference:
        params["photo_reference"] = photo_reference
    elif photo_name:
        params["photo_reference"] = photo_name
    else:
        return None
    try:
        response = requests.get(GOOGLE_PHOTO_URL, params=params, timeout=10, stream=True, allow_redirects=True)
        if response.status_code >= 400:
            return None
        return response
    except Exception:
        return None
