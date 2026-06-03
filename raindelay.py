#!/usr/bin/env python3
"""
Activates a tinytuya relay when today's forecasted rain exceeds a threshold.

Configuration via environment variables — see raindelay.env.example.
"""

import datetime
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
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


def get_todays_precipitation(lat: float, lon: float, timezone: str) -> float:
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum",
        "precipitation_unit": "inch",
        "timezone": timezone,
        "forecast_days": 1,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read())
        return float(data["daily"]["precipitation_sum"][0])
    except urllib.error.HTTPError as e:
        log.error("Weather API failed (HTTP %s): %s", e.code, e.reason)
        sys.exit(1)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        log.error("Unexpected weather API response: %s", e)
        sys.exit(1)


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

    precip = get_todays_precipitation(LATITUDE, LONGITUDE, TIMEZONE)
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
