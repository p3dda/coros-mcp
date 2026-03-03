"""
Coros MCP Server — Sleep & HRV data via the unofficial Coros Training Hub API.

Usage:
    python server.py

MCP config (Claude Code):
    claude mcp add coros \\
      -e COROS_EMAIL=you@example.com \\
      -e COROS_PASSWORD=yourpass \\
      -e COROS_REGION=eu \\
      -- python /path/to/coros-mcp/server.py
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastmcp import FastMCP

import coros_api

load_dotenv()

mcp = FastMCP("coros-mcp")


# ---------------------------------------------------------------------------
# Tool: authenticate_coros
# ---------------------------------------------------------------------------

@mcp.tool()
async def authenticate_coros(
    email: str,
    password: str,
    region: str = "eu",
) -> dict:
    """
    Authenticate with the Coros Training Hub API and store the access token.

    Credentials can also be provided via COROS_EMAIL, COROS_PASSWORD, and
    COROS_REGION environment variables (loaded from .env).

    Parameters
    ----------
    email : str
        Coros account email address.
    password : str
        Coros account password (plain text — hashed with MD5 before sending).
    region : str
        "eu" (default) or "us".

    Returns
    -------
    dict with keys: authenticated, user_id, region, message
    """
    try:
        auth = await coros_api.login(email, password, region)
        return {
            "authenticated": True,
            "user_id": auth.user_id,
            "region": auth.region,
            "message": f"Token stored at {coros_api.AUTH_FILE}",
        }
    except Exception as exc:
        return {
            "authenticated": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Tool: check_coros_auth
# ---------------------------------------------------------------------------

@mcp.tool()
async def check_coros_auth() -> dict:
    """
    Check whether a valid Coros access token is stored locally.

    Returns
    -------
    dict with keys: authenticated, user_id, region, expires_in_hours (approx)
    """
    auth = coros_api.get_stored_auth()
    if auth is None:
        return {
            "authenticated": False,
            "message": "No valid token found. Call authenticate_coros first.",
        }

    import time
    age_ms = int(time.time() * 1000) - auth.timestamp
    remaining_ms = coros_api.TOKEN_TTL_MS - age_ms
    remaining_hours = round(remaining_ms / 3_600_000, 1)

    return {
        "authenticated": True,
        "user_id": auth.user_id,
        "region": auth.region,
        "expires_in_hours": remaining_hours,
    }


# ---------------------------------------------------------------------------
# Tool: get_sleep_data
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_sleep_data(date: str, days: int = 1) -> dict:
    """
    Retrieve sleep data from Coros for one or more days.

    NOTE: The sleep endpoint is currently a placeholder. Confirm the correct
    path via Proxyman SSL decryption (see docs/discover-endpoints.md).

    Parameters
    ----------
    date : str
        Start date in YYYYMMDD format (e.g. "20240315").
    days : int
        Number of days to fetch (1–30). Default: 1.

    Returns
    -------
    dict with keys: records (list of sleep records), count
    Each record contains: date, total_duration_minutes, phases
    (deep/light/rem/awake), sleep_start, sleep_end, quality_score.
    """
    auth = coros_api.get_stored_auth()
    if auth is None:
        return {
            "error": "Not authenticated. Call authenticate_coros first.",
            "records": [],
        }

    days = max(1, min(days, 30))
    start_dt = datetime.strptime(date, "%Y%m%d")
    end_dt = start_dt + timedelta(days=days - 1)
    end_day = end_dt.strftime("%Y%m%d")

    try:
        records = await coros_api.fetch_sleep(auth, date, end_day)
        return {
            "records": [r.model_dump() for r in records],
            "count": len(records),
            "date_range": f"{date} – {end_day}",
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "hint": "If you get a 404, the sleep endpoint path needs updating. "
                    "See docs/discover-endpoints.md for Proxyman instructions.",
            "records": [],
        }


# ---------------------------------------------------------------------------
# Tool: get_hrv_data
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_hrv_data(date: str, days: int = 1) -> dict:
    """
    Retrieve HRV data from Coros for one or more days.

    NOTE: The HRV endpoint is currently a placeholder. Confirm the correct
    path via Proxyman SSL decryption (see docs/discover-endpoints.md).

    Parameters
    ----------
    date : str
        Start date in YYYYMMDD format (e.g. "20240315").
    days : int
        Number of days to fetch (1–30). Default: 1.

    Returns
    -------
    dict with keys: records (list of HRV records), count
    Each record contains: date, rmssd_avg (ms), hrv_index (0-100),
    rmssd_min, rmssd_max.
    """
    auth = coros_api.get_stored_auth()
    if auth is None:
        return {
            "error": "Not authenticated. Call authenticate_coros first.",
            "records": [],
        }

    days = max(1, min(days, 30))
    start_dt = datetime.strptime(date, "%Y%m%d")
    end_dt = start_dt + timedelta(days=days - 1)
    end_day = end_dt.strftime("%Y%m%d")

    try:
        records = await coros_api.fetch_hrv(auth, date, end_day)
        return {
            "records": [r.model_dump() for r in records],
            "count": len(records),
            "date_range": f"{date} – {end_day}",
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "hint": "If you get a 404, the HRV endpoint path needs updating. "
                    "See docs/discover-endpoints.md for Proxyman instructions.",
            "records": [],
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
