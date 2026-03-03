"""
Coros Training Hub API client.

Auth mechanism: MD5-hashed password + accessToken header.
Sleep/HRV endpoints are placeholders — confirm via Proxyman SSL decryption.
See docs/discover-endpoints.md for instructions.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from models import HRVRecord, SleepPhases, SleepRecord, StoredAuth

# ---------------------------------------------------------------------------
# Endpoint constants — update after Proxyman capture
# ---------------------------------------------------------------------------

ENDPOINTS = {
    "login": "/account/login",
    "sleep": "/sleep/query",    # TODO: confirm via Proxyman with SSL decryption
    "hrv": "/hrv/query",        # TODO: confirm via Proxyman with SSL decryption
}

BASE_URLS = {
    "eu": "https://teamapi.coros.com",
    "us": "https://us.teamapi.coros.com",
}

AUTH_FILE = Path.home() / ".config" / "coros-mcp" / "auth.json"
TOKEN_TTL_MS = 24 * 60 * 60 * 1000  # 24 hours in milliseconds


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------

def _save_auth(auth: StoredAuth) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(auth.model_dump_json())
    AUTH_FILE.chmod(0o600)


def _load_auth() -> Optional[StoredAuth]:
    if not AUTH_FILE.exists():
        return None
    try:
        data = json.loads(AUTH_FILE.read_text())
        return StoredAuth(**data)
    except Exception:
        return None


def _is_token_valid(auth: StoredAuth) -> bool:
    now_ms = int(time.time() * 1000)
    return (now_ms - auth.timestamp) < TOKEN_TTL_MS


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _md5(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()


def _base_url(region: str) -> str:
    return BASE_URLS.get(region, BASE_URLS["eu"])


async def login(email: str, password: str, region: str = "eu") -> StoredAuth:
    """Authenticate against Coros API and persist the token."""
    url = _base_url(region) + ENDPOINTS["login"]
    payload = {
        "account": email,
        "accountType": 2,
        "pwd": _md5(password),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        body = resp.json()

    # Coros wraps response in {"result": "0000", "message": "OK", "data": {...}}
    if body.get("result") != "0000":
        raise ValueError(f"Coros login failed: {body.get('message', 'unknown error')}")

    data = body.get("data", {})
    auth = StoredAuth(
        access_token=data["accessToken"],
        user_id=data["userId"],
        region=region,
        timestamp=int(time.time() * 1000),
    )
    _save_auth(auth)
    return auth


def get_stored_auth() -> Optional[StoredAuth]:
    """Return stored auth if it exists and is not expired."""
    auth = _load_auth()
    if auth and _is_token_valid(auth):
        return auth
    return None


# ---------------------------------------------------------------------------
# API headers
# ---------------------------------------------------------------------------

def _auth_headers(auth: StoredAuth) -> dict:
    return {
        "Content-Type": "application/json",
        "accesstoken": auth.access_token,
        "yfheader": json.dumps({"userId": auth.user_id}),
    }


# ---------------------------------------------------------------------------
# Sleep data
# ---------------------------------------------------------------------------

async def fetch_sleep(auth: StoredAuth, start_day: str, end_day: str) -> list[SleepRecord]:
    """
    Fetch sleep data for a date range.

    Parameters
    ----------
    start_day, end_day : str
        Dates in YYYYMMDD format.

    NOTE: Endpoint is a placeholder — confirm path via Proxyman.
    """
    url = _base_url(auth.region) + ENDPOINTS["sleep"]
    params = {
        "userId": auth.user_id,
        "startDay": start_day,
        "endDay": end_day,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=_auth_headers(auth))
        resp.raise_for_status()
        body = resp.json()

    if body.get("result") != "0000":
        raise ValueError(f"Coros sleep API error: {body.get('message', 'unknown error')}")

    records: list[SleepRecord] = []
    for item in body.get("data", {}).get("list", []):
        records.append(_parse_sleep_item(item))
    return records


def _parse_sleep_item(item: dict) -> SleepRecord:
    """
    Parse a single sleep record from API response.

    Field mapping is speculative — update after confirming endpoint.
    Common Coros field names based on observed API patterns.
    """
    phases = SleepPhases(
        deep_minutes=item.get("deepSleepMinutes") or item.get("deepSleep"),
        light_minutes=item.get("lightSleepMinutes") or item.get("lightSleep"),
        rem_minutes=item.get("remSleepMinutes") or item.get("remSleep"),
        awake_minutes=item.get("awakeSleepMinutes") or item.get("awakeSleep"),
    )
    return SleepRecord(
        date=str(item.get("date", "")),
        total_duration_minutes=item.get("totalSleepMinutes") or item.get("totalSleep"),
        phases=phases,
        sleep_start=item.get("sleepStartTime") or item.get("startTime"),
        sleep_end=item.get("sleepEndTime") or item.get("endTime"),
        quality_score=item.get("sleepScore") or item.get("score"),
    )


# ---------------------------------------------------------------------------
# HRV data
# ---------------------------------------------------------------------------

async def fetch_hrv(auth: StoredAuth, start_day: str, end_day: str) -> list[HRVRecord]:
    """
    Fetch HRV data for a date range.

    NOTE: Endpoint is a placeholder — confirm path via Proxyman.
    """
    url = _base_url(auth.region) + ENDPOINTS["hrv"]
    params = {
        "userId": auth.user_id,
        "startDay": start_day,
        "endDay": end_day,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=_auth_headers(auth))
        resp.raise_for_status()
        body = resp.json()

    if body.get("result") != "0000":
        raise ValueError(f"Coros HRV API error: {body.get('message', 'unknown error')}")

    records: list[HRVRecord] = []
    for item in body.get("data", {}).get("list", []):
        records.append(_parse_hrv_item(item))
    return records


def _parse_hrv_item(item: dict) -> HRVRecord:
    """
    Parse a single HRV record from API response.

    Field mapping is speculative — update after confirming endpoint.
    """
    return HRVRecord(
        date=str(item.get("date", "")),
        rmssd_avg=item.get("rmssdAvg") or item.get("avgRmssd") or item.get("nightAvg"),
        hrv_index=item.get("hrvIndex") or item.get("score"),
        rmssd_min=item.get("rmssdMin") or item.get("minRmssd"),
        rmssd_max=item.get("rmssdMax") or item.get("maxRmssd"),
    )
