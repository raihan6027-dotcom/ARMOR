# ARMOR Backend — AI Safety Gateway

FastAPI orchestration layer for **ARMOR** (AI-Aware Identity Protection).
It connects the frontend to the AI models, consent/permission, a deterministic
policy engine, and a decision engine, following the ARMOR pipeline:

```
IDENTIFY → VERIFY → ANALYZE (intent + risk) → CONSENT/PERMISSION → POLICY → DECIDE → PROTECT
```

Core principle: **IDENTITY → CONSENT → TRUST**. The AI produces *information*;
the deterministic **policy engine** produces the authoritative verdict
(`ALLOW` / `REVIEW` / `DENY`). LLM output is never the final decision, and any
uncertainty (undetermined risk, unverified identity, AI unavailable) fails safe
to `REVIEW` — never a silent `ALLOW`.

## Architecture

```
Frontend ─▶ FastAPI ─┬─▶ Identity AI  (InsightFace/ArcFace + official_face_registry.pkl)
                     ├─▶ Intent AI    (Gemini, structured JSON)
                     └─▶ Risk AI      (Gemini, structured JSON)
                              │
                     Consent / Permission (MySQL)
                              │
                     Policy Engine (deterministic)  ──▶  Decision + reason  ──▶  History
```

Layers (module layout preserved from the original repo and extended):

| Layer | Location |
|---|---|
| Routers | `app/<module>/router.py` (auth, identity, permission, intent, risk, consent, decision, requests, logs) |
| Schemas | `app/schema/` (+ `common.py` for canonical enums & AI-output normalizers) |
| Services | `app/services/` (identity, permission, consent, decision/orchestration) |
| AI clients | `app/ai/` (`gemini_client`, `identity_client`, `registry`, `client` façade) |
| Policy | `app/policy/engine.py` (deterministic rules) |
| Models / DB | `app/models/`, `app/db/database.py` |
| Core | `app/core/` (config, security, logging, exceptions) |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (use: source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
cp .env.example .env            # then edit .env
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for interactive Swagger UI.

### Configuration (`.env`)

| Key | Purpose |
|---|---|
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/armor` (deploy) or `sqlite:///./armor.db` (local) |
| `JWT_SECRET` | Secret for signing access tokens (use a long random string) |
| `CORS_ORIGINS` | Comma-separated frontend origins, or `*` |
| `GEMINI_API_KEY` | Gemini key for intent/risk analysis. **Empty ⇒ safe deterministic fallback** |
| `GEMINI_MODEL` | Gemini model id (default matches the team notebook) |
| `MODEL_DIR` | Folder holding `official_face_registry.pkl` (the pre-deployment face model) |
| `FACE_MATCH_THRESHOLD` | Cosine threshold for a positive face match (default `0.40`) |

Secrets and model/biometric files are **never** committed (see `.gitignore`).

### Using MySQL

This machine had no MySQL server, so local dev runs on SQLite; the code and all
5 tables are verified MySQL-compatible. To run on MySQL:

```sql
CREATE DATABASE armor CHARACTER SET utf8mb4;
```

```bash
# in .env
DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/armor
```

Tables are auto-created on startup. (`cryptography` is included for MySQL 8 auth.)

## AI integration

- **Identity** — `app/ai/registry.py` loads `official_face_registry.pkl`
  (6,114 identities) and matches via cosine similarity; `app/ai/identity_client.py`
  turns an uploaded image into a 512-D ArcFace embedding with InsightFace
  (`buffalo_l`, downloaded on first use). Validated at **90.5% top-1** on the
  provided test-query embeddings.
- **Intent / Risk** — `app/ai/gemini_client.py` sends image + subject + prompt to
  Gemini and parses structured JSON. Gemini's own `decision` is captured as
  **advisory only**; the policy engine re-derives the verdict.
- **Fallback** — with no `GEMINI_API_KEY` (or on any AI failure), intent is
  classified by keywords and risk by a conservative heuristic, and the system
  keeps returning safe decisions.

## API summary

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/auth/register`, `/auth/login`, `/auth/me` | POST/POST/GET | – | Accounts + JWT |
| `/identity/enroll`, `/identity/verify` | POST | ✔ | Enroll / verify a face |
| `/identity/profile`, `/identity/lock` | GET/POST | ✔ | Profile / protect an identity |
| `/permissions` | GET/POST | ✔ | Read / set per-action permissions |
| `/ai/analyze-intent` · `/analyze/intent` | POST | – | Intent analysis |
| `/risk` · `/analyze/risk` | POST | – | Risk analysis |
| `/consent/request`, `/consent/status/{id}`, `/consent/respond` | POST/GET/POST | – | Consent lifecycle |
| `/decision` | POST | – | Stateless policy evaluation |
| **`/requests`** | **POST** | ✔ | **Full orchestration pipeline** (main entry point) |
| `/requests`, `/logs` | GET | ✔ | Decision history |

### `POST /requests` (the gateway)

Request: `{ "identity_id": "...", "prompt": "...", "image": "<base64?>" }` + `Authorization: Bearer <token>`.
Runs authenticate → verify identity → intent (AI) → permission → consent → risk
(AI) → **policy** → decision → persist. Returns a structured decision:

```json
{
  "request_id": "REQ-001",
  "identity": { "identity_id": "ARMOR-OTHER", "verified": false, "target": "OTHER" },
  "intent":   { "label": "COMMERCIAL_USE", "confidence": 0.4, "ai_available": false },
  "consent":  { "status": "UNKNOWN" },
  "risk":     { "score": 80, "level": "HIGH", "ai_available": false },
  "permission": "REVIEW",
  "decision": { "action": "REVIEW", "reason_code": "HIGH_RISK_REVIEW",
                "reason": "High risk usage requires the identity owner's review or consent." }
}
```

Errors use a consistent envelope: `{ "error": { "code": "...", "message": "..." } }`.

## Testing

```bash
pytest -q
```

46 tests: policy unit rules, AI-output normalization, auth, identity match math,
intent/risk, consent, permission, `/decision`, and the three canonical E2E
scenarios through `/requests` (SELF+personal→ALLOW, OTHER+commercial→REVIEW,
OTHER+impersonation→DENY). Tests run fully offline (no Gemini key, no model
download) on the deterministic fallback path.

## Security notes

- Passwords hashed with bcrypt; access via JWT bearer tokens.
- Secrets and biometric artifacts kept out of git.
- Logs record decision metadata only — never passwords, keys, or raw images.
- AI failure never escalates privilege: it degrades to `REVIEW`/`DENY`.
