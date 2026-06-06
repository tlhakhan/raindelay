#!/usr/bin/env python3
"""
Activates a tinytuya relay when today's forecasted rain exceeds a threshold.

Configuration via environment variables — see raindelay.env.example.
"""

import datetime
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zoneinfo

import tinytuya

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HTTP_TIMEOUT = 10
HTTP_RETRIES = 16
HTTP_RETRY_DELAY = 30  # seconds between attempts

NWS_USER_AGENT = "raindelay (github.com/tlhakhan/raindelay)"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        log.error("Required environment variable %s is not set", name)
        sys.exit(1)
    return value


LATITUDE = float(_require_env("LATITUDE"))
LONGITUDE = float(_require_env("LONGITUDE"))
TIMEZONE = _require_env("TIMEZONE")
RAINFALL_THRESHOLD_INCHES = float(os.environ.get("RAINFALL_THRESHOLD_INCHES", "0.1"))
TUYA_DEV_ID = _require_env("TUYA_DEV_ID")
TUYA_IP = _require_env("TUYA_IP")
TUYA_LOCAL_KEY = _require_env("TUYA_LOCAL_KEY")
TUYA_VERSION = float(os.environ.get("TUYA_VERSION", "3.5"))


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": NWS_USER_AGENT})
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            log.warning("HTTP attempt %d/%d failed (%s %s): %s", attempt, HTTP_RETRIES, e.code, e.reason, url)
        except (urllib.error.URLError, OSError) as e:
            log.warning("HTTP attempt %d/%d failed: %s", attempt, HTTP_RETRIES, e)
        if attempt < HTTP_RETRIES:
            log.info("Retrying in %d seconds...", HTTP_RETRY_DELAY)
            time.sleep(HTTP_RETRY_DELAY)
    log.error("Request failed after %d attempts: %s", HTTP_RETRIES, url)
    sys.exit(1)


def _parse_duration_hours(duration: str) -> float:
    """Parse an ISO 8601 duration like PT1H or PT6H into hours."""
    m = re.match(r"PT(\d+(?:\.\d+)?)H", duration)
    return float(m.group(1)) if m else 1.0


def get_nws_grid_url(lat: float, lon: float) -> str:
    data = _fetch_json(f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}")
    try:
        return data["properties"]["forecastGridData"]
    except (KeyError, TypeError) as e:
        log.error("Unexpected NWS /points response: %s", e)
        sys.exit(1)


def get_todays_precipitation(grid_url: str, timezone_str: str) -> float:
    data = _fetch_json(grid_url)
    tz = zoneinfo.ZoneInfo(timezone_str)
    now = datetime.datetime.now(tz)
    today_start = datetime.datetime.combine(now.date(), datetime.time.min, tzinfo=tz)
    today_end = today_start + datetime.timedelta(days=1)

    try:
        values = data["properties"]["quantitativePrecipitation"]["values"]
    except (KeyError, TypeError) as e:
        log.error("Unexpected NWS gridpoint response: %s", e)
        sys.exit(1)

    total_mm = 0.0
    for entry in values:
        try:
            valid_time_str, duration_str = entry["validTime"].split("/")
            start = datetime.datetime.fromisoformat(valid_time_str)
            if start.tzinfo is None:
                start = start.replace(tzinfo=datetime.timezone.utc)
            end = start + datetime.timedelta(hours=_parse_duration_hours(duration_str))
            if start < today_end and end > today_start:
                value = entry.get("value")
                if value is not None:
                    total_mm += value
        except (KeyError, ValueError, AttributeError):
            continue

    return total_mm / 25.4  # mm to inches


def seconds_until_local_midnight(timezone_str: str) -> int:
    tz = zoneinfo.ZoneInfo(timezone_str)
    now = datetime.datetime.now(tz)
    tomorrow = now.date() + datetime.timedelta(days=1)
    midnight = datetime.datetime.combine(tomorrow, datetime.time.min, tzinfo=tz)
    return max(1, int((midnight - now).total_seconds()))


def make_device() -> tinytuya.OutletDevice:
    return tinytuya.OutletDevice(
        dev_id=TUYA_DEV_ID,
        address=TUYA_IP,
        local_key=TUYA_LOCAL_KEY,
        version=TUYA_VERSION,
    )


def activate_relay(device: tinytuya.OutletDevice, secs: int) -> None:
    log.info("Setting relay ON with %d-second auto-off timer", secs)
    device.set_multiple_values({1: True, 17: secs})


def main() -> None:
    log.info(
        "Checking rain forecast — lat=%.4f lon=%.4f timezone=%s threshold=%.2f in",
        LATITUDE, LONGITUDE, TIMEZONE, RAINFALL_THRESHOLD_INCHES,
    )

    grid_url = get_nws_grid_url(LATITUDE, LONGITUDE)
    log.info("NWS grid: %s", grid_url)

    precip = get_todays_precipitation(grid_url, TIMEZONE)
    log.info("Today's forecast precipitation: %.2f inches", precip)

    if precip >= RAINFALL_THRESHOLD_INCHES:
        secs = seconds_until_local_midnight(TIMEZONE)
        log.info(
            "Rain threshold met (%.2f >= %.2f in). Activating relay, timer=%d s (%.1f h).",
            precip, RAINFALL_THRESHOLD_INCHES, secs, secs / 3600,
        )
        try:
            activate_relay(make_device(), secs)
        except Exception as e:
            log.error("Failed to activate relay: %s", e)
            sys.exit(1)
        log.info("Done.")
    else:
        log.info(
            "Rain below threshold (%.2f < %.2f in). No action taken.",
            precip, RAINFALL_THRESHOLD_INCHES,
        )


if __name__ == "__main__":
    main()
