# CardPointe Debug Harness

Standalone troubleshooting harness for CardPointe Integrated Terminal API connectivity/auth.

- No Odoo imports.
- Direct HTTP calls with `requests`.
- Structured report file written per run to:
  - `tools/cardpointe_debug/RESULTS_<YYYYMMDD_HHMMSS>.txt`

## Setup

```bash
cd /workspace/odoo
python -m venv .venv
source .venv/bin/activate
pip install -r tools/cardpointe_debug/requirements.txt
cp tools/cardpointe_debug/.env.example .env
# edit .env with real secrets/tokens if available
```

## Commands

```bash
python tools/cardpointe_debug/cardpointe_probe.py --help
python tools/cardpointe_debug/cardpointe_probe.py ping
python tools/cardpointe_debug/cardpointe_probe.py sale_noauth
python tools/cardpointe_debug/cardpointe_probe.py sale_apikey
python tools/cardpointe_debug/cardpointe_probe.py sale_bearer
python tools/cardpointe_debug/cardpointe_probe.py oauth_token
python tools/cardpointe_debug/cardpointe_probe.py sale_oauth
python tools/cardpointe_debug/cardpointe_probe.py compare_hosts
python tools/cardpointe_debug/cardpointe_probe.py full
```

## Interpreting outcomes

- **401 Unauthorized**: endpoint reached, auth scheme/token is missing/invalid/expired.
- **400 Bad Request**: auth likely accepted, but payload fields/values are invalid.
- **404 Not Found**: wrong host/path/version.
- **Connection closed / RemoteDisconnected**: upstream/proxy/TLS edge closed socket before response.

## Safety

- `Authorization` is redacted in report logs.
- OAuth/client/API secrets are redacted from environment snapshot.
- Response body is truncated to 2000 chars.
- TLS verification defaults to `true`; can be disabled only for troubleshooting.
