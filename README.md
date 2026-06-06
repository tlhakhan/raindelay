# raindelay

Checks today's rain forecast and activates a tinytuya relay switch (irrigation rain delay controller) when forecasted precipitation exceeds a configurable threshold. The relay auto-turns off at local midnight via tinytuya's DPS 17 countdown timer. Safe to run multiple times per day — the timer is recalculated on each run.

## Requirements

- Python 3.9+
- A tinytuya-compatible relay device on your local network
- Device credentials (ID, IP, local key) from `python3 -m tinytuya wizard`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp raindelay.env.example raindelay.env
# edit raindelay.env with your values
```

## Configuration

All configuration is via environment variables. See [`raindelay.env.example`](raindelay.env.example) for the full list.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LATITUDE` | yes | — | Location latitude |
| `LONGITUDE` | yes | — | Location longitude |
| `TIMEZONE` | yes | — | IANA timezone (e.g. `America/New_York`) |
| `RAINFALL_THRESHOLD_INCHES` | no | `0.1` | Inches of forecast rain to trigger relay |
| `TUYA_DEV_ID` | yes | — | Tinytuya device ID |
| `TUYA_IP` | yes | — | Device local IP |
| `TUYA_LOCAL_KEY` | yes | — | Device local key |
| `TUYA_VERSION` | no | `3.5` | Tinytuya protocol version |

## Usage

```bash
source raindelay.env
python3 raindelay.py
```

## Systemd Deployment

See [CLAUDE.md](CLAUDE.md) for systemd service and timer unit examples (runs daily at 3am).

## APIs

- [NWS](https://api.weather.gov) — free, no API key required (US only)
