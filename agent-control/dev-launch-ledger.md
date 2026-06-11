# Dev E2E Failure Ledger

Path-unblocker ledger for [`dev-launch-debug`](../docs/builder-os-folder-contract.md). Durable project memory — do **not** put this in `scratch/`.

## Current Target Path

**App:** arthor-image-service  
**Path:** HMAC-signed `POST /images/hero-candidates/generate` → poll `GET /images/hero-candidates/{run_id}` until `status: complete` with 3 URLs  
**Goal:** W21-H-D deploy smoke — hero-candidates reachable for arthor-ai consumer wire-up (W21-H-C)

## Status

- [x] App boots
- [x] Env vars load
- [x] Auth works (HMAC `X-Arthor-Signature`)
- [x] DB connects (local Docker `arthor-image-pg` on `:5440`)
- [x] Main happy path completes (3 hero URLs uploaded to R2)
- [ ] Webhooks/callbacks work — N/A (hero-candidates is poll-only; no callback)
- [x] Logs are clean enough to debug

---

## W21-H-D smoke run (2026-06-11)

**Branch:** `pod/w21-h-hero-candidates`  
**pytest:** `tests/test_hero_candidates.py` — 4 passed  
**Base URL for arthor-ai:** `http://127.0.0.1:8010` (local uvicorn; use staging URL when deployed)

### Prerequisites brought up

1. Start Docker Desktop (if down).
2. Start local Postgres: `docker start arthor-image-pg` (host port **5440**, db `arthor_image`).
3. `.env` needs `DATABASE_URL`, `FASTAPI_ARTHOR_SHARED_SECRET`, provider keys. R2 keys in `.env` may be empty placeholders — override from `~/arthor-ai/.env` for smoke (see commands below).

### Commands

```bash
cd ~/arthor-image-service
source .venv/bin/activate
pytest tests/test_hero_candidates.py -q

# Start API (merges R2 creds from arthor-ai when local .env R2_* are blank)
python - <<'PY'
import os
from pathlib import Path

def load_env(path: Path, *, overwrite=frozenset()):
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip()
        if k in overwrite or k not in os.environ:
            os.environ[k] = v
        elif not os.environ.get(k):
            os.environ[k] = v

R2_KEYS = frozenset({"R2_ACCOUNT_ID","R2_ACCESS_KEY_ID","R2_SECRET_ACCESS_KEY","R2_BUCKET_NAME","R2_ENDPOINT_URL","R2_BUCKET"})
load_env(Path(".env"))
load_env(Path("../arthor-ai/.env"), overwrite=R2_KEYS)
if os.environ.get("R2_ACCOUNT_ID"):
    os.environ["R2_ENDPOINT_URL"] = f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
if os.environ.get("R2_BUCKET_NAME"):
    os.environ["R2_BUCKET"] = os.environ["R2_BUCKET_NAME"]
import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=8010)
PY
```

### HMAC smoke (canonical payload from tests)

Uses `_build_hero_request()` in `tests/test_hero_candidates.py`. For local smoke, set `"default_provider_hint": "openai_image"` when Gemini free-tier quota is exhausted.

```bash
python - <<'PY'
import json, time, uuid, httpx
from app.auth.hmac import sign_body
from app.config import get_settings
from tests.test_hero_candidates import _build_hero_request

BASE = "http://127.0.0.1:8010"
secret = get_settings().fastapi_arthor_shared_secret
payload = _build_hero_request(idem_key=f"hero-smoke-{uuid.uuid4()}")
payload["default_provider_hint"] = "openai_image"
raw = json.dumps(payload).encode()
headers = {"X-Arthor-Signature": sign_body(secret, raw), "Content-Type": "application/json"}
get_sig = sign_body(secret, b"")

post = httpx.post(f"{BASE}/images/hero-candidates/generate", content=raw, headers=headers, timeout=60)
print("POST", post.status_code, post.json())
run_id = post.json()["agent_run_id"]
for _ in range(120):
    poll = httpx.get(f"{BASE}/images/hero-candidates/{run_id}", headers={"X-Arthor-Signature": get_sig})
    body = poll.json()
    if body.get("status") == "complete" and len(body.get("urls") or []) == 3:
        print("OK", json.dumps(body, indent=2))
        break
    if body.get("status") == "failed":
        raise SystemExit(body)
    time.sleep(5)
PY
```

### Verified run

| Field | Value |
|-------|-------|
| `agent_run_id` | `f0b33e73-06cb-4d24-bf0b-510cfcf98a8e` |
| Poll result | `status: complete`, 3 URLs (`variant_index` 0–2) |
| Provider | `openai_image` (Gemini default blocked by free-tier quota) |
| R2 prefix | `hero-candidates/{run_id}/{0,1,2}.png` |

---

## Blockers fixed this session

### 001 - Hero slot 1920×1080 unsupported by providers

Status: Fixed  
Severity: Blocker  
Step: Background worker after POST 202  
Expected: 3 generated + uploaded assets  
Actual: `UnknownModelVersion` / OpenAI `Invalid size '1920x1080'`  
Fix: Hero slot dimensions → **1536×1024** (`app/payload/hero_models.py`); cost tables include `(1920, 1080)` for future asset-pack parity  
Retest result: Smoke green with OpenAI

### 002 - Local Postgres container stopped

Status: Fixed  
Severity: Blocker  
Step: uvicorn lifespan / DB pool  
Expected: asyncpg connects  
Actual: `Connection refused` on `:5440`  
Fix: `docker start arthor-image-pg`  
Retest result: Pool OK

### 003 - R2 creds blank in service `.env`

Status: Workaround  
Severity: Blocker for real uploads  
Step: R2 client init  
Expected: `services.r2` set  
Actual: Empty `R2_*` placeholders in `.env` blocked merge from arthor-ai  
Fix: Override R2 keys from `~/arthor-ai/.env` at uvicorn launch (see command above)  
Retest result: R2 uploads OK

---

## Deferred Issues

### D001 - Gemini free-tier quota exhausted for default hero provider

Reason deferred: Account/env limit (`limit: 0` for `gemini-2.5-flash-preview-image`); not a code bug  
Evidence: Asset metadata error on run `5bda5877-2028-4d53-8842-1284d79770db`  
Suggested follow-up: Enable billing/quota on `GOOGLE_API_KEY`, or have arthor-ai pass `default_provider_hint: openai_image` until Gemini quota restored

### D002 - Populate R2_* in arthor-image-service `.env`

Reason deferred: Secrets live in arthor-ai today; empty placeholders in service `.env` confuse startup  
Suggested follow-up: Copy R2 block from arthor-ai `.env` or document merge script in README
