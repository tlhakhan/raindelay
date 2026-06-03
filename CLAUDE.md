# raindelay

Checks today's rain forecast and activates a tinytuya relay switch (irrigation rain delay controller) when forecasted precipitation exceeds a threshold. The relay auto-turns off at midnight via tinytuya's DPS 17 countdown timer. Safe to run multiple times in one day — the timer is recalculated each run.

## Project Structure

```
raindelay.py          # main script
raindelay.env.example # template for secrets/config (committed)
raindelay.env         # live secrets — gitignored, copy from example
requirements.txt
.gitignore
venv/                 # virtualenv — gitignored
```

## Environment Variables

All configuration comes from environment variables. Copy `raindelay.env.example` to `raindelay.env` and fill in your values.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LATITUDE` | yes | — | Location latitude (float) |
| `LONGITUDE` | yes | — | Location longitude (float) |
| `TIMEZONE` | yes | — | IANA timezone string (e.g. `America/New_York`) |
| `RAINFALL_THRESHOLD_INCHES` | no | `0.1` | Minimum forecasted inches to trigger relay |
| `TUYA_DEV_ID` | yes | — | Tinytuya device ID |
| `TUYA_IP` | yes | — | Device local IP address |
| `TUYA_LOCAL_KEY` | yes | — | Device local key |
| `TUYA_VERSION` | no | `3.5` | Tinytuya protocol version |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install tinytuya

cp raindelay.env.example raindelay.env
# edit raindelay.env with your values
```

## Running

```bash
source raindelay.env
source venv/bin/activate
python3 raindelay.py
```

## Relay Behavior

- **DPS 1** (`bool`): turns relay on/off
- **DPS 17** (`int`, seconds): countdown timer — relay auto-turns off after N seconds

When rain is forecast above threshold, the script:
1. Sets DPS 1 = `True` (relay on)
2. Sets DPS 17 = seconds remaining until local midnight

If rain is below threshold, no action is taken (relay stays in its current state).

Re-running the script when the relay is already on is safe — it refreshes the DPS 17 countdown to the correct remaining seconds.

## Systemd Deployment

Deploy the project to `/opt/raindelay/` (or any path — update the unit files accordingly).

**`/etc/systemd/system/raindelay.service`**
```ini
[Unit]
Description=Rain delay relay check
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/opt/raindelay/raindelay.env
ExecStart=/opt/raindelay/venv/bin/python3 /opt/raindelay/raindelay.py
StandardOutput=journal
StandardError=journal
```

**`/etc/systemd/system/raindelay.timer`**
```ini
[Unit]
Description=Run rain delay check daily at 3am

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now raindelay.timer

# View logs
journalctl -u raindelay.service
```

## APIs Used

- **Open-Meteo** (`api.open-meteo.com`) — free weather forecast, no API key needed. Uses `daily=precipitation_sum` with the configured `TIMEZONE`.
- No other external dependencies beyond `tinytuya`.

## Design Notes

- No `devices.json` needed — device credentials come entirely from env vars.
- Uses `zoneinfo.ZoneInfo` (Python 3.9+ stdlib) for DST-aware midnight calculation.
- No `subprocess`, no `requests` — pure stdlib HTTP + tinytuya Python API.
- Threshold defaults to 0.1 inches; set `RAINFALL_THRESHOLD_INCHES=0` to force activation for testing.
