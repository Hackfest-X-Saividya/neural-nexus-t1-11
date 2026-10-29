# CrimeSketchAI: Natural-Language Facial Refinement Backend

CrimeSketchAI is an AI-assisted criminal suspect facial sketch and composite refinement system. This module implements the **FastAPI Natural-Language Refinement Backend** with hardened dry-run refinement and a **read-only live Blender state inspector**.

It parses conversational natural-language adjustments from forensic interviewers (e.g., *"Make the nose slightly wider"*, *"Increase the chin prominence slightly"*, *"Make the cheekbones more prominent"*) and maps them strictly to verified 3D morph targets in MakeHuman Plugin for Blender (MPFB).

---

## 1. Safety Architecture & State Management

* **Read-Only Live State Inspection (`GET /state`):** Queries the live target stack from Blender via the official MPFB bridge (`127.0.0.1:9877`). Strictly read-only: uses `get_target_stack` exclusively and **never invokes `mpfb_set_targets`** or any mutating command.
* **No Cached Fallback on Live State Failure:** If Blender is disconnected, closed, or encounters an error, `GET /state` returns `source: "unavailable"` with detailed error diagnostic information. It **never** fabricates or substitutes cached reference values as live data.
* **Bounded Socket Timeouts:** All live-state Blender queries run with bounded thread-level timeouts (`BLENDER_TIMEOUT_SECONDS = 3.0`). A non-responsive or stopped Blender instance will never hang the FastAPI server.
* **Offline Dry-Run Refine (`POST /refine`):** Refinement simulations remain in **dry-run mode only**. It calculates proposed modifier adjustments without touching the 3D scene.
* **Cached Reference State in Refinement:** Dry-run refinement baseline values are explicitly marked as offline reference values derived from `controlled_test_log.json`. They are clearly distinguished from live Blender reads.
* **Rejection of Client-Asserted State:** Clients are strictly prohibited from submitting a `current_value` in requests. A client cannot claim or override the 3D model's state. Any request carrying `current_value` is rejected immediately and audited.
* **Bilateral Symmetry Integrity:** Bilateral features (`eye_size`, `cheekbone_prominence`) explicitly produce both `left` and `right` modifiers and target shape keys. Single-sided changes are never assumed to be automatically symmetric.
* **Dual Parser Architecture (Rule-Based & Local Ollama AI):** Supports deterministic regex rule-based parsing (default) alongside local neural interpretation via **Ollama (`qwen3:4b`)**.
* **Zero Cloud Dependency & Local Privacy:** Ollama requests run entirely on the local loopback (`http://127.0.0.1:11434`). No suspect descriptions or biometric data are ever sent to cloud AI services.
* **Never Trust Model Output (Strict Allowlist Validation):** Model responses are strictly validated against `VERIFIED_ALLOWLIST`. Malformed JSON, unknown feature proposals, invalid directions, or out-of-range magnitudes are immediately rejected.
* **No Silent Fallback on AI Mode:** When AI mode is requested (`parser_mode="ai"`), errors or Ollama unreachability result in immediate rejection with diagnostic details. The system never silently falls back to the rule-based parser without explicit audit trail.
* **Audit Logging:** Every incoming refinement request—whether approved or rejected—is logged to SQLite (`refinements.db`) with a UTC timestamp, case ID, parsed feature, proposed delta, parser mode used, and error messages.
* **Controlled Live Apply (`POST /apply`):** Controlled two-phase application of approved dry-run previews to the Blender `Human` character via the MPFB bridge `set_targets` command.
  - **Explicit Approval Required:** Requires `confirm_apply: true` and a valid `preview_log_id` with status `PREVIEW_READY`.
  - **Server-Side Modifier Integrity:** Modifiers are retrieved exclusively from the SQLite audit log; callers cannot inject arbitrary modifiers or values. Every modifier is re-validated against `VERIFIED_ALLOWLIST`.
  - **Hard Object Locking:** Locked strictly to character name `"Human"`.
  - **Atomic Replay Protection:** Prevents duplicate or concurrent execution of the same preview via SQLite primary key constraints.
  - **Pre-Mutation State Drift Check:** Aborts mutation if Blender target values changed since preview creation. Previews without live baseline data (`use_live_state=False`) are safely rejected.
  - **Immediate Read-Back Verification:** Queries live state post-mutation, verifying target feature values match within `0.001` and all unrelated features remain untouched.

---

## 2. Verified Allowlist of 10 Facial Features

All mappings correspond 1-to-1 with MPFB's verified `target.json` catalogue:

| Feature | Display Name | MPFB Section | MPFB Category | Sided | Sides | Range | Step | Cached Reference | Target Shape Keys (Positive / Negative) |
|---|---|---|---|---|---|---|---|---|---|
| `nose_width` | nose width | `nose` | `nose-scale-horiz-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `+0.20` | `nose-scale-horiz-incr` / `nose-scale-horiz-decr` |
| `nose_height` | nose height | `nose` | `nose-scale-vert-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `+0.05` | `nose-scale-vert-incr` / `nose-scale-vert-decr` |
| `chin_width` | chin width | `chin` | `chin-width-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `-0.10` | `chin-width-incr` / `chin-width-decr` |
| `chin_prominence` | chin prominence | `chin` | `chin-prominent-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `+0.10` | `chin-prominent-incr` / `chin-prominent-decr` |
| `cheekbone_prominence` | cheekbone prominence | `cheek` | `cheek-bones-decr-incr` | Yes | `left`, `right` | `[-1.0, 1.0]` | `0.05` | `+0.15` | `l/r-cheek-bones-incr` / `l/r-cheek-bones-decr` |
| `eye_size` | eye size | `eyes` | `eye-scale-decr-incr` | Yes | `left`, `right` | `[-1.0, 1.0]` | `0.05` | `+0.10` | `l/r-eye-scale-incr` / `l/r-eye-scale-decr` |
| `forehead_size` | forehead size | `forehead` | `forehead-scale-vert-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `0.00` | `forehead-scale-vert-incr` / `forehead-scale-vert-decr` |
| `head_width` | head width | `head` | `head-scale-horiz-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `-0.15` | `head-scale-horiz-incr` / `head-scale-horiz-decr` |
| `head_height` | head height | `head` | `head-scale-vert-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `+0.10` | `head-scale-vert-incr` / `head-scale-vert-decr` |
| `mouth_width` | mouth width | `mouth` | `mouth-scale-horiz-decr-incr` | No | `unsided` | `[-1.0, 1.0]` | `0.05` | `-0.05` | `mouth-scale-horiz-incr` / `mouth-scale-horiz-decr` |

---

## 3. Windows Setup & Installation

### Prerequisites
* Python 3.10+ (using the existing virtual environment at `C:\Dept\MPFB MCP\mpfb-mcp\.venv`)
* Node.js v18+ and npm
* Local Ollama instance with `qwen3:4b` installed (`ollama pull qwen3:4b`)
* Windows 10/11 or Windows Server

### Environment Variables & Configuration
The backend is configurable via environment variables or default settings:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama HTTP service endpoint |
| `OLLAMA_MODEL` | `qwen3:4b` | Ollama model identifier |
| `OLLAMA_TIMEOUT_SECONDS` | `60.0` | Socket timeout for Ollama HTTP requests (adequate for local reasoning models) |
| `PARSER_MODE` | `rule_based` | Global default parser (`rule_based` or `ai`) |
| `BLENDER_TIMEOUT_SECONDS` | `3.0` | Socket timeout for MPFB Bridge live target reads |

### Running Backend Tests
Execute the pytest suite from the project directory:

```powershell
cd C:\Dept\CrimeSketchAI
& "C:\Dept\MPFB MCP\mpfb-mcp\.venv\Scripts\pytest.exe" -v
```

### Running Frontend Tests
Execute the Vitest suite in the `frontend` directory:

```powershell
cd C:\Dept\CrimeSketchAI\frontend
npm test
```

### Starting the FastAPI Backend Server
Launch the development server on `http://127.0.0.1:8000`:

```powershell
cd C:\Dept\CrimeSketchAI
& "C:\Dept\MPFB MCP\mpfb-mcp\.venv\Scripts\uvicorn.exe" backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive Swagger documentation will be available at:  
👉 **http://127.0.0.1:8000/docs**

### Starting the React Frontend (Vite)
In a separate PowerShell window, start the frontend development server:

```powershell
cd C:\Dept\CrimeSketchAI\frontend
npm run dev
```

The user interface will be accessible at:  
👉 **http://localhost:5173** (or `http://127.0.0.1:5173`)

---

## 4. API Endpoints & Example Requests

### A. Health Check (`GET /health`)
Verifies service health, database connectivity, and active allowlist count.

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```

**Example Response:**
```json
{
  "status": "healthy",
  "app_name": "CrimeSketchAI Refinement Backend",
  "version": "0.1.0",
  "allowlist_count": 10,
  "allowlist_features": [
    "nose_width", "nose_height", "chin_width", "chin_prominence",
    "cheekbone_prominence", "eye_size", "forehead_size",
    "head_width", "head_height", "mouth_width"
  ],
  "mode": "dry_run",
  "data_source_mode": "offline_cached_reference",
  "database_connected": true,
  "parser_mode": "rule_based",
  "ollama_model": "qwen3:4b",
  "ollama_available": true
}
```

---

### B. Live Model Target State (`GET /state`)
Retrieves the real-time target stack from the live Blender `Human` model via the verified MPFB-MCP bridge (`get_target_stack`).

* **Query Parameters:** `character_name` (optional, default `"Human"`).
* **Guarantees:**
  - Strictly read-only; **never** alters the 3D scene or invokes mutating tools.
  - Zero-fallback policy: if Blender is closed, unreachable, or returns an error, the endpoint responds with `source: "unavailable"` and explicit error details. Cached values are **never** substituted as live data.
  - Non-blocking socket timeout: bounded by `BLENDER_TIMEOUT_SECONDS` (default: 3.0s).

#### Example 1: Successful Live Blender Inspection
**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/state?character_name=Human" -Method Get
```

**Response (`source: "live_blender"`):**
```json
{
  "connection_available": true,
  "character_name": "Human",
  "source": "live_blender",
  "timestamp_utc": "2026-10-28T12:30:00.000000Z",
  "error_details": null,
  "features": {
    "nose_width": {
      "feature_id": "nose_width",
      "display_name": "nose width",
      "value": 0.20,
      "left_value": null,
      "right_value": null,
      "is_symmetric": true,
      "target_identifiers": [
        "nose:nose-scale-horiz-decr-incr:unsided"
      ]
    },
    "cheekbone_prominence": {
      "feature_id": "cheekbone_prominence",
      "display_name": "cheekbone prominence",
      "value": 0.15,
      "left_value": 0.15,
      "right_value": 0.15,
      "is_symmetric": true,
      "target_identifiers": [
        "cheek:cheek-bones-decr-incr:left",
        "cheek:cheek-bones-decr-incr:right"
      ]
    },
    "chin_prominence": {
      "feature_id": "chin_prominence",
      "display_name": "chin prominence",
      "value": 0.10,
      "left_value": null,
      "right_value": null,
      "is_symmetric": true,
      "target_identifiers": [
        "chin:chin-prominent-decr-incr:unsided"
      ]
    }
  }
}
```

#### Example 2: Blender Bridge Closed or Unreachable
When the bridge port `9877` is closed or Blender is not running, the endpoint cleanly reports the unavailability:

**Response (`source: "unavailable"`):**
```json
{
  "connection_available": false,
  "character_name": "Human",
  "source": "unavailable",
  "timestamp_utc": "2026-10-28T12:30:00.000000Z",
  "error_details": "Cannot connect to MPFB bridge at 127.0.0.1:9877. Ensure Blender is running and MPFB Bridge server is active.",
  "features": null
}
```

---

### C. List Allowlisted Features (`GET /features`)
Returns definitions, boundaries, and cached reference values for all 10 features.

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/features" -Method Get
```

---

### D. Dry-Run Refine (`POST /refine`)
Parses a natural-language refinement command and generates a dry-run modifier adjustment preview.

* **State Modes:**
  - `use_live_state: false` *(default)*: Uses offline verified reference baselines. Fully offline; does not poll Blender.
  - `use_live_state: true`: Reads live target stack from Blender (`BlenderStateService`). Computes adjustment deltas against the live 3D model.
* **Parser Modes:**
  - `parser_mode: "rule_based"` *(default)*: Deterministic regular expression parser matching explicit keywords.
  - `parser_mode: "ai"`: Local neural parsing via Ollama (`qwen3:4b`). Interprets conversational prompts into structured JSON, validated strictly against the 10 allowlisted features. Rejects malformed JSON, out-of-scope modifications, or unreachable Ollama instances without silent fallback.
* **Guarantees:**
  - **Zero mutation:** Never modifies the 3D scene or invokes `mpfb_set_targets`.
  - **Zero silent fallback:** If `use_live_state: true` and Blender is unavailable or returns an error, the request is rejected with `status: "REJECTED"`. Cached reference values are **never** substituted for live data.
  - **Bilateral asymmetry preservation:** Bilateral features read both left and right values, calculate adjustments independently, preserve existing asymmetry differences, and enforce individual boundary clamping.
  - **Client-asserted state forbidden:** Any caller-supplied `current_value` is rejected immediately.

#### Example 1: Cached Reference Mode (`use_live_state: false`)
**PowerShell:**
```powershell
$body = @{
    text = "Make the nose slightly wider."
    case_id = "CASE-2026-001"
    character_name = "Human"
    use_live_state = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/refine" -Method Post -Body $body -ContentType "application/json"
```

**Response (`PREVIEW_READY`):**
```json
{
  "status": "PREVIEW_READY",
  "mode": "dry_run",
  "case_id": "CASE-2026-001",
  "input_text": "Make the nose slightly wider.",
  "feature_id": "nose_width",
  "display_name": "nose width",
  "reference_value": 0.20,
  "current_value": 0.20,
  "value_source": "cached_reference",
  "is_live_blender_value": false,
  "reference_note": "Value is an offline cached reference value from the verified baseline; this is NOT a live Blender socket read.",
  "adjustment_delta": 0.05,
  "proposed_delta": 0.05,
  "proposed_value": 0.25,
  "is_boundary_clamped": false,
  "boundary_warning": null,
  "target_identifier": "nose:nose-scale-horiz-decr-incr:unsided",
  "target_identifiers": [
    "nose:nose-scale-horiz-decr-incr:unsided"
  ],
  "target_shapekeys": [
    "nose-scale-horiz-incr"
  ],
  "proposed_payload": {
    "name": "Human",
    "modifiers": [
      {
        "section": "nose",
        "category": "nose-scale-horiz-decr-incr",
        "side": "unsided",
        "value": 0.25
      }
    ],
    "symmetry": false,
    "prune": true,
    "refit": false
  },
  "message": "Dry-run preview: nose width will be increased by +0.05 from cached reference +0.20 to proposed +0.25 across target(s) [nose:nose-scale-horiz-decr-incr:unsided] on character 'Human'. (Note: Uses offline cached reference value, NOT a live Blender read).",
  "error_message": null,
  "log_id": 1
}
```

#### Example 2: Live Blender Mode (`use_live_state: true`)
When Blender currently holds `nose-scale-horiz-decr-incr = +0.20`:

**PowerShell:**
```powershell
$body = @{
    text = "Make the nose slightly wider."
    case_id = "CASE-LIVE-001"
    character_name = "Human"
    use_live_state = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/refine" -Method Post -Body $body -ContentType "application/json"
```

**Response (`PREVIEW_READY`):**
```json
{
  "status": "PREVIEW_READY",
  "mode": "dry_run",
  "case_id": "CASE-LIVE-001",
  "input_text": "Make the nose slightly wider.",
  "feature_id": "nose_width",
  "display_name": "nose width",
  "reference_value": 0.20,
  "current_value": 0.20,
  "value_source": "live_blender",
  "is_live_blender_value": true,
  "reference_note": "Observed from live Blender model 'Human' target stack; NOT cached reference.",
  "adjustment_delta": 0.05,
  "proposed_delta": 0.05,
  "proposed_value": 0.25,
  "is_boundary_clamped": false,
  "boundary_warning": null,
  "target_identifier": "nose:nose-scale-horiz-decr-incr:unsided",
  "target_identifiers": [
    "nose:nose-scale-horiz-decr-incr:unsided"
  ],
  "target_shapekeys": [
    "nose-scale-horiz-incr"
  ],
  "proposed_payload": {
    "name": "Human",
    "modifiers": [
      {
        "section": "nose",
        "category": "nose-scale-horiz-decr-incr",
        "side": "unsided",
        "value": 0.25
      }
    ],
    "symmetry": false,
    "prune": true,
    "refit": false
  },
  "message": "Live dry-run preview: nose width will be increased by +0.05 from live Blender value +0.20 to proposed +0.25 across target(s) [nose:nose-scale-horiz-decr-incr:unsided] on character 'Human'. (Data source: live Blender target stack)."
}
```

#### Example 3: Bilateral Live Refinement with Preserved Asymmetry
If the character's cheekbones have an asymmetric sculpt (Left = 0.10, Right = 0.25):

**PowerShell:**
```powershell
$body = @{
    text = "Make the cheekbones more prominent."
    case_id = "CASE-ASYM-001"
    use_live_state = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/refine" -Method Post -Body $body -ContentType "application/json"
```

**Response (`PREVIEW_READY` with Asymmetry Preserved):**
```json
{
  "status": "PREVIEW_READY",
  "feature_id": "cheekbone_prominence",
  "value_source": "live_blender",
  "is_live_blender_value": true,
  "left_current_value": 0.10,
  "right_current_value": 0.25,
  "left_proposed_value": 0.15,
  "right_proposed_value": 0.30,
  "is_symmetric": false,
  "proposed_payload": {
    "name": "Human",
    "modifiers": [
      {
        "section": "cheek",
        "category": "cheek-bones-decr-incr",
        "side": "left",
        "value": 0.15
      },
      {
        "section": "cheek",
        "category": "cheek-bones-decr-incr",
        "side": "right",
        "value": 0.30
      }
    ]
  },
  "message": "Live dry-run preview: cheekbone prominence will be increased by +0.05 from live Blender asymmetric values (left: +0.10, right: +0.25, diff: +0.15) to proposed (left: +0.15, right: +0.30) across target(s) [cheek:cheek-bones-decr-incr:left, cheek:cheek-bones-decr-incr:right] on character 'Human'. Preserved bilateral asymmetry."
}
```

#### Example 4: Rejection When Live Blender State Is Unavailable (Zero Fallback)
When `use_live_state: true` and the bridge port `9877` is closed:

**Response (`REJECTED`):**
```json
{
  "status": "REJECTED",
  "mode": "dry_run",
  "case_id": "CASE-FAIL-001",
  "input_text": "Make the nose slightly wider.",
  "value_source": "unavailable",
  "is_live_blender_value": false,
  "reference_note": "Live Blender state read failed; cached reference values were NOT substituted.",
  "message": "Refinement rejected: Live Blender state unavailable: Cannot connect to MPFB Bridge at 127.0.0.1:9877. Preview rejected because use_live_state=True and live state cannot be verified.",
  "error_message": "Live Blender state unavailable: Cannot connect to MPFB Bridge at 127.0.0.1:9877. Preview rejected because use_live_state=True and live state cannot be verified."
}
```

#### Example 5: Rejection of Client-Supplied `current_value`
**Request:**
```json
{
  "text": "Make the nose slightly wider.",
  "case_id": "CASE-2026-003",
  "current_value": 0.95
}
```

**Response (`REJECTED`):**
```json
{
  "status": "REJECTED",
  "mode": "dry_run",
  "case_id": "CASE-2026-003",
  "input_text": "Make the nose slightly wider.",
  "message": "Refinement rejected: Caller-supplied 'current_value' is rejected. Clients cannot assert or override 3D model state. All dry-run calculations strictly use verified cached reference values or live Blender state via use_live_state=True.",
  "error_message": "Caller-supplied 'current_value' is rejected. Clients cannot assert or override 3D model state. All dry-run calculations strictly use verified cached reference values or live Blender state via use_live_state=True.",
  "log_id": 3
}
```

#### Example 6: Refinement via Local Ollama AI Parser (`parser_mode: "ai"`)
Natural-language instruction interpreted locally using Ollama (`qwen3:4b`):

**PowerShell:**
```powershell
$body = @{
    text = "Could you give him a noticeably wider nose?"
    case_id = "CASE-AI-001"
    character_name = "Human"
    parser_mode = "ai"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/refine" -Method Post -Body $body -ContentType "application/json"
```

**Response (`PREVIEW_READY`):**
```json
{
  "status": "PREVIEW_READY",
  "mode": "dry_run",
  "case_id": "CASE-AI-001",
  "input_text": "Could you give him a noticeably wider nose?",
  "feature_id": "nose_width",
  "display_name": "nose width",
  "reference_value": 0.20,
  "current_value": 0.20,
  "value_source": "cached_reference",
  "is_live_blender_value": false,
  "adjustment_delta": 0.08,
  "proposed_delta": 0.08,
  "proposed_value": 0.28,
  "is_boundary_clamped": false,
  "boundary_warning": null,
  "target_identifier": "nose:nose-scale-horiz-decr-incr:unsided",
  "target_identifiers": [
    "nose:nose-scale-horiz-decr-incr:unsided"
  ],
  "target_shapekeys": [
    "nose-scale-horiz-incr"
  ],
  "parser_mode": "ai",
  "parser_model": "qwen3:4b",
  "proposed_payload": {
    "name": "Human",
    "modifiers": [
      {
        "section": "nose",
        "category": "nose-scale-horiz-decr-incr",
        "side": "unsided",
        "value": 0.28
      }
    ],
    "symmetry": false,
    "prune": true,
    "refit": false
  },
  "message": "Dry-run preview: nose width will be increased by +0.08 from cached reference +0.20 to proposed +0.28 across target(s) [nose:nose-scale-horiz-decr-incr:unsided] on character 'Human'. (Note: Uses offline cached reference value, NOT a live Blender read).",
  "log_id": 4
}
```

#### Example 7: AI Rejection When Ollama Unreachable (Zero Silent Fallback)
When `parser_mode: "ai"` is requested but Ollama is offline or unresponsive, the request is rejected immediately with an explicit audit log and diagnostic error message:

**Response (`REJECTED`):**
```json
{
  "status": "REJECTED",
  "mode": "dry_run",
  "case_id": "CASE-AI-ERR-001",
  "input_text": "Make the chin wider.",
  "parser_mode": "ai",
  "parser_model": "qwen3:4b",
  "message": "Refinement rejected: AI parser error: Cannot connect to Ollama at http://127.0.0.1:11434. Ensure Ollama service is running.",
  "error_message": "AI parser error: Cannot connect to Ollama at http://127.0.0.1:11434. Ensure Ollama service is running.",
  "log_id": 5
}
```

---

### E. Audit Logs (`GET /logs`)
Retrieves SQLite records of all refinement requests and rejections.

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/logs?case_id=CASE-2026-001" -Method Get
```

---

### F. Live Refinement Apply (`POST /apply`)
Applies a previously validated and recorded dry-run preview (`PREVIEW_READY`) to the live Blender character named `Human` using the verified MPFB bridge `set_targets` command.

* **Safety Checks Enforced Before Mutation:**
  1. Character object locked strictly to `"Human"`.
  2. Explicit user confirmation required (`confirm_apply: true`).
  3. Preview audit record must exist and have status `PREVIEW_READY`.
  4. Preview must have been generated in live mode (`use_live_state=True`) with captured baseline metrics. Previews from offline cached mode are rejected.
  5. Atomic replay protection check ensures the preview has not already been claimed or applied.
  6. Server-side modifier retrieval: Modifiers are loaded exclusively from SQLite audit details, never accepted from caller payload.
  7. Modifiers re-validated against `VERIFIED_ALLOWLIST` (bounds `[-1.0, 1.0]`, allowed sides, valid category).
  8. Pre-mutation state drift verification: Live Blender target values are read immediately before mutation. If the target feature or any unrelated allowlisted feature has changed since preview creation, the operation is aborted.
* **Bridge Execution:**
  - Invokes `set_targets` with `name="Human"`, `symmetry=False`, `prune=True`, `refit=False`.
  - For bilateral asymmetric features, applies left and right target sliders independently without overwriting the opposite side.
* **Post-Mutation Read-Back Verification:**
  - Live target stack is re-read from Blender immediately after mutation.
  - Verifies target feature values match expected proposed values within `0.001`.
  - Verifies all other allowlisted features remained unchanged within `0.001`.
  - If read-back fails, status is marked `APPLY_FAILED` and audited.

#### Example 1: Successful Apply Request
**PowerShell:**
```powershell
$body = @{
    preview_log_id = 1
    case_id = "CASE-LIVE-001"
    character_name = "Human"
    confirm_apply = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/apply" -Method Post -Body $body -ContentType "application/json"
```

**Response (`APPLIED`):**
```json
{
  "status": "APPLIED",
  "apply_log_id": 2,
  "preview_log_id": 1,
  "case_id": "CASE-LIVE-001",
  "character_name": "Human",
  "feature_id": "nose_width",
  "display_name": "nose width",
  "previous_value": 0.20,
  "applied_value": 0.25,
  "left_previous_value": null,
  "right_previous_value": null,
  "left_applied_value": null,
  "right_applied_value": null,
  "verified": true,
  "drift_checked": true,
  "modifiers_applied": [
    {
      "section": "nose",
      "category": "nose-scale-horiz-decr-incr",
      "side": "unsided",
      "value": 0.25
    }
  ],
  "message": "Successfully applied and verified changes to nose width on character 'Human' in Blender. Read-back confirmed target values and confirmed all unrelated features remained unchanged.",
  "error_message": null
}
```

#### Example 2: Replay Protection Rejection
If a client attempts to apply the same `preview_log_id` a second time:

**Response (`APPLY_FAILED`):**
```json
{
  "status": "APPLY_FAILED",
  "apply_log_id": 3,
  "preview_log_id": 1,
  "case_id": "CASE-LIVE-001",
  "character_name": "Human",
  "verified": false,
  "drift_checked": false,
  "message": "Refinement application rejected: Application rejected: Preview #1 has already been claimed or applied (status: APPLIED at 2026-10-28T12:35:00.000000Z). Previews cannot be applied more than once (replay protection).",
  "error_message": "Application rejected: Preview #1 has already been claimed or applied (status: APPLIED at 2026-10-28T12:35:00.000000Z). Previews cannot be applied more than once (replay protection)."
}
```

---

## 5. File Structure

```
C:\Dept\CrimeSketchAI\
├── controlled_test_log.json         # Pre-test and post-test Blender target log
├── requirements.txt                 # Backend Python package requirements
├── README.md                        # Documentation and API guide
├── refinements.db                   # SQLite database (auto-generated)
├── backend\
│   ├── __init__.py
│   ├── config.py                    # Environment, timeout, CORS, and bridge host/port settings
│   ├── main.py                      # FastAPI app and route handlers (/health, /features, /refine, /apply, /logs, /state)
│   ├── models\
│   │   ├── __init__.py
│   │   └── schemas.py               # Pydantic schemas (refinement, apply, features, live state)
│   ├── parser\
│   │   ├── __init__.py
│   │   ├── feature_catalog.py       # 10 allowlisted features & MPFB metadata
│   │   ├── refinement_parser.py     # Deterministic regex & direction rule-based parser
│   │   ├── ollama_client.py         # Local Ollama HTTP client with timeout, error handling & health probe
│   │   └── ollama_parser.py         # Neural refinement parser with strict JSON validation & allowlist enforcement
│   ├── storage\
│   │   ├── __init__.py
│   │   └── database.py              # SQLite storage engine with atomic replay protection
│   └── service\
│       ├── __init__.py
│       ├── blender_state_service.py # Read-only Blender bridge live target inspector with bounded timeout
│       ├── blender_mutation_service.py # Controlled live Blender applicator with 10 safety checkpoints
│       └── refinement_service.py    # Dual-parser dry-run pipeline and boundary clamp logic
├── frontend\
│   ├── package.json                 # React 19, Vite, TypeScript, Vitest
│   ├── vite.config.ts               # Vite & Vitest configuration
│   ├── tsconfig.app.json            # Strict TypeScript configuration
│   └── src\
│       ├── api\
│       │   └── client.ts            # Type-safe API client & error normalizer
│       ├── types\
│       │   └── api.ts               # Complete TypeScript API models (including parser modes & Ollama health)
│       ├── components\
│       │   ├── Header.tsx           # Header with real-time Blender, API & Ollama connection status
│       │   ├── RefinementForm.tsx   # Command input, parser selector (Rule vs AI), character select & mode toggle
│       │   ├── PreviewPanel.tsx     # Accurate 3D preview, bilateral metrics, clamping alerts & parser badge
│       │   └── AuditHistory.tsx     # SQLite audit log viewer with filtering and inspection
│       ├── test\
│       │   ├── setup.ts             # Vitest test setup with @testing-library/jest-dom
│       │   ├── App.test.tsx         # End-to-end status and refinement integration tests
│       │   ├── PreviewPanel.test.tsx# Tests for previews, bilateral display, rejections, clamping
│       │   ├── RefinementForm.test.tsx # Form input, mode selection, example chips, no-mutation check
│       │   └── AuditHistory.test.tsx# Audit log filtering and accordion inspection tests
│       ├── App.tsx                  # Main workspace coordinator
│       ├── App.css                  # Restrained dark theme design system
│       └── index.css                # Base CSS resets and CSS custom properties
└── tests\
    ├── __init__.py
    ├── test_parser.py               # 23 tests: rule-based command syntax, directions, magnitudes
    ├── test_service.py              # 9 tests: state hardening, caller rejection, bilateral, clamping, whitespace, audit value_source
    ├── test_api.py                  # 8 tests: HTTP integration tests, state audit, audit logs
    ├── test_live_state.py           # 9 tests: live reads, asymmetry, timeouts, errors, no-mutation audit
    ├── test_live_refinement.py      # 11 tests: live refinement previews, asymmetry preservation, zero-fallback
    ├── test_ollama_parser.py        # 28 tests: client, timeout vs connection errors, conversational JSON extraction, allowlist, no silent fallback
    └── test_apply.py                # 16 tests: live application safety, state drift, replay protection, verification read-back (104 total backend tests)
```
