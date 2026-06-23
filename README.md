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

## GitHub Actions Deployment

The workflow at [`.github/workflows/raindelay.yml`](.github/workflows/raindelay.yml) runs daily at 3am and can be triggered manually via the Actions tab.

Because the Tuya relay is on a local network, a Raspberry Pi on the same LAN acts as a [Tailscale subnet router](https://tailscale.com/kb/1019/subnets/) so the GitHub-hosted runner can reach it.

### Raspberry Pi setup (one-time)

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Enable IP forwarding
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf

# Advertise your LAN subnet (adjust to match your network)
sudo tailscale up --advertise-routes=192.168.4.0/22 --accept-routes
```

Then in the [Tailscale admin console](https://login.tailscale.com/admin/machines):
- Approve the advertised subnet route for the Pi under the machine's settings.
- Under **Settings → ACL**, declare the `tag:ci` tag:
  ```json
  "tagOwners": { "tag:ci": [] }
  ```
- Under **Settings → OAuth clients**, create an OAuth client for the ephemeral runner:
  1. Go to **Settings → OAuth clients → Generate OAuth client**.
  2. Give it a description (e.g. `github-actions-raindelay`).
  3. Under **Scopes**, enable **Auth keys** → **Write** — this allows the client to create ephemeral auth keys so the runner can register as a Tailscale node.
  4. Click **Generate client**. Copy the **Client ID** and **Client secret** immediately — the secret is shown only once.
  5. Save both values as GitHub Secrets `TS_OAUTH_CLIENT_ID` and `TS_OAUTH_CLIENT_SECRET` (see below).

### GitHub Secrets and Variables

Under repo → **Settings → Secrets and variables → Actions**:

**Secrets** (encrypted):

| Secret | Description |
|---|---|
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID |
| `TS_OAUTH_CLIENT_SECRET` | Tailscale OAuth client secret |
| `LATITUDE` | Location latitude |
| `LONGITUDE` | Location longitude |
| `TUYA_DEV_ID` | Tinytuya device ID |
| `TUYA_IP` | Device local IP address |
| `TUYA_LOCAL_KEY` | Device local key |

**Variables** (plain text, visible — use the Variables tab):

| Variable | Description |
|---|---|
| `TIMEZONE` | IANA timezone string (e.g. `America/New_York`) |

### Cron timing

The schedule `0 8 * * *` fires at 08:00 UTC. Adjust for your timezone:

| Timezone | Standard offset | Cron for 3am |
|---|---|---|
| ET | UTC−5 | `0 8 * * *` |
| CT | UTC−6 | `0 9 * * *` |
| MT | UTC−7 | `0 10 * * *` |
| PT | UTC−8 | `0 11 * * *` |

During daylight saving time, subtract 1 hour from the UTC value (e.g. ET DST → `0 7 * * *`).

## APIs

- [NWS](https://api.weather.gov) — free, no API key required (US only)
