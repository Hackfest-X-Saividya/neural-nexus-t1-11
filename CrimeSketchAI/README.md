# CrimeSketchAI: Forensic Facial Composite & 3D Biometric Reconstruction Studio

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Blender](https://img.shields.io/badge/Blender-5.2-E87D0D.svg?style=flat&logo=blender)](https://www.blender.org)
[![MPFB2](https://img.shields.io/badge/MPFB-2.0.2-4B6EAF.svg?style=flat)](http://mpfb.net)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen3%3A4B-000000.svg?style=flat&logo=ollama)](https://ollama.com)
[![Pytest](https://img.shields.io/badge/Pytest-174%20Passed-green.svg?style=flat)](https://docs.pytest.org)
[![Vitest](https://img.shields.io/badge/Vitest-29%20Passed-green.svg?style=flat)](https://vitest.dev)
[![WCAG AA](https://img.shields.io/badge/A11y-WCAG%202.1%20AA%20Compliant-blue.svg?style=flat)](https://www.w3.org/WAI/WCAG21/quickref/)

**CrimeSketchAI** is an AI-assisted forensic facial composite and 3D biometric reconstruction studio. It bridges the gap between subjective eyewitness testimony and accurate 3D anatomical modeling by interpreting conversational, natural-language witness descriptions (e.g., *"A suspect with a broad nose, prominent cheekbones, an afro, and a wide jaw"*) and translating them into verifiable, mathematically bounded 3D morph targets in **Blender 5.2** via the **MakeHuman Plugin for Blender (MPFB)**.

The system features a **1-Click "Generate & Apply"** workflow with strict pre-mutation state drift checks, server-side allowlist validation, bilateral symmetry preservation, immediate read-back verification, an immutable SQLite chain-of-custody audit trail, and a headless forensic pencil sketch rendering pipeline producing **1024 × 1024 monochrome graphite portraits**.

---

## Table of Contents

1. [Architecture & System Overview](#1-architecture--system-overview)
2. [Core Forensic Capabilities](#2-core-forensic-capabilities)
   - [38 Verified Facial Geometry Controls](#38-verified-facial-geometry-controls)
   - [Hairstyle & Eyebrow Customization](#hairstyle--eyebrow-customization)
   - [1-Click Generate & Apply Workflow](#1-click-generate--apply-workflow)
   - [Forensic Pencil Sketch Rendering Pipeline](#forensic-pencil-sketch-rendering-pipeline)
   - [Chain-of-Custody Audit Trail](#chain-of-custody-audit-trail)
3. [Prerequisites](#3-prerequisites)
4. [Step-by-Step Setup Guide](#4-step-by-step-setup-guide)
   - [Step 1: Install Blender 5.2](#step-1-install-blender-52)
   - [Step 2: Install & Configure the MPFB Add-on](#step-2-install--configure-the-mpfb-add-on)
   - [Step 3: Create the 3D Character ("Human")](#step-3-create-the-3d-character-human)
   - [Step 4: Start the MPFB Socket Bridge](#step-4-start-the-mpfb-socket-bridge)
   - [Step 5: Setup Local Ollama AI](#step-5-setup-local-ollama-ai)
   - [Step 6: Setup & Run FastAPI Backend](#step-6-setup--run-fastapi-backend)
   - [Step 7: Setup & Run React Frontend](#step-7-setup--run-react-frontend)
5. [Witness Prompting Guide & Examples](#5-witness-prompting-guide--examples)
6. [REST API Reference](#6-rest-api-reference)
7. [Safety & Forensic Integrity Protocol](#7-safety--forensic-integrity-protocol)
8. [Automated Test Suites](#8-automated-test-suites)
9. [Troubleshooting & FAQs](#9-troubleshooting--faqs)

---

## 1. Architecture & System Overview

CrimeSketchAI operates as a three-tier local architecture ensuring **100% data privacy** (no facial data or testimony leaves the forensic workstation).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            WITNESS INTERVIEW                                │
│          "A suspect with an afro, prominent cheekbones, and a wide jaw"     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            REACT 18 + TYPESCRIPT STUDIO FRONTEND (Port 5173)                │
│  • Obsidian / Slate Dark Theme (WCAG 2.1 AA Compliant)                      │
│  • Segmented Reference & Parser Toggles (Live Bridge vs. Cached Baseline)   │
│  • Real-Time Target Delta Diff & Read-Back Verification Display             │
│  • Interactive 1024×1024 Forensic Pencil Sketch Viewer & Downloader         │
│  • Searchable Forensic Audit Trail (SQLite Chain of Custody)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP REST JSON
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 FASTAPI REFINEMENT BACKEND (Port 8000)                      │
│  • POST /refine : Dry-run semantic/rule parsing and delta computation       │
│  • POST /apply  : Anti-drift check, allowlist validation, socket execution   │
│  • POST /render-sketch : Staging, Workbench cavity render, graphite filter  │
│  • GET  /state  : Read-only live morph target stack inspection              │
│  • GET  /logs   : SQLite audit query filterable by Case ID                  │
└───────────────────┬─────────────────────────────────────┬───────────────────┘
                    │                                     │
         HTTP (127.0.0.1:11434)             Raw TCP Socket (127.0.0.1:9877)
                    ▼                                     ▼
┌───────────────────────────────────┐ ┌───────────────────────────────────────┐
│     LOCAL OLLAMA AI PARSER        │ │    BLENDER 5.2 + MPFB BRIDGE SERVER   │
│  • Model: Qwen3:4B                │ │  • Active Scene Object: "Human"       │
│  • Context-aware semantic parsing │ │  • JSON-RPC Socket Server (Port 9877) │
│  • Strict JSON Schema validation  │ │  • 38 Target Controls + Asset Library │
│  • Zero cloud data leakage        │ │  • Workbench Engine (Cavity Shading)  │
└───────────────────────────────────┘ └───────────────────────────────────────┘
```

---

## 2. Core Forensic Capabilities

### 38 Verified Facial Geometry Controls

Every facial control corresponds 1-to-1 with a verified entry in MPFB's underlying `target.json` catalog. Bounded within `[-1.0, 1.0]` with default `±0.05` steps:

| Anatomical Region | Feature Identifier | Sided | Target Shape Keys (Positive / Negative) |
|---|---|---|---|
| **Mouth & Lips** | `mouth_width` | No | `mouth-scale-horiz-incr` / `mouth-scale-horiz-decr` |
| | `mouth_height` | No | `mouth-scale-vert-incr` / `mouth-scale-vert-decr` |
| | `mouth_upperlip_volume` | No | `mouth-upperlip-volume-incr` / `mouth-upperlip-volume-decr` |
| | `mouth_lowerlip_volume` | No | `mouth-lowerlip-volume-incr` / `mouth-lowerlip-volume-decr` |
| | `mouth_cupids_bow` | No | `mouth-cupidsbow-incr` / `mouth-cupidsbow-decr` |
| | `philtrum_depth` | No | `mouth-philtrum-volume-incr` / `mouth-philtrum-volume-decr` |
| | `laugh_lines` | No | `mouth-laugh-lines-out` / `mouth-laugh-lines-in` |
| | `dimples` | No | `mouth-dimples-out` / `mouth-dimples-in` |
| | `mouth_corner_turn` | No | `mouth-angles-up` / `mouth-angles-down` |
| **Nose** | `nose_width` | No | `nose-scale-horiz-incr` / `nose-scale-horiz-decr` |
| | `nose_height` | No | `nose-scale-vert-incr` / `nose-scale-vert-decr` |
| | `nasal_bridge_hump` | No | `nose-hump-incr` / `nose-hump-decr` |
| | `nasal_bridge_curve` | No | `nose-curve-convex` / `nose-curve-concave` |
| | `nostril_width` | No | `nose-nostrils-width-incr` / `nose-nostrils-width-decr` |
| | `nose_tip_width` | No | `nose-point-width-incr` / `nose-point-width-decr` |
| | `nose_tip_angle` | No | `nose-point-up` / `nose-point-down` |
| | `septum_angle` | No | `nose-septumangle-decr` / `nose-septumangle-incr` |
| **Eyes & Eyelids** | `eye_size` | Yes (L/R) | `l/r-eye-scale-incr` / `l/r-eye-scale-decr` |
| | `eye_spacing` | No | `eyes-spacing-incr` / `eyes-spacing-decr` |
| | `eye_slant` | Yes (L/R) | `l/r-eye-angles-up` / `l/r-eye-angles-down` |
| | `eyelid_upper_fold` | Yes (L/R) | `l/r-eye-upperlid-fold-in` / `l/r-eye-upperlid-fold-out` |
| | `eyelid_lower_hooded`| Yes (L/R) | `l/r-eye-lowerlid-fold-in` / `l/r-eye-lowerlid-fold-out` |
| | `eye_bag_depth` | Yes (L/R) | `l/r-eye-bag-incr` / `l/r-eye-bag-decr` |
| **Chin & Jaw** | `chin_width` | No | `chin-width-incr` / `chin-width-decr` |
| | `chin_prominence` | No | `chin-prominent-incr` / `chin-prominent-decr` |
| | `chin_height` | No | `chin-scale-vert-incr` / `chin-scale-vert-decr` |
| | `chin_cleft` | No | `chin-cleft-incr` / `chin-cleft-decr` |
| | `jaw_width` | No | `jaw-width-incr` / `jaw-width-decr` |
| | `jaw_angle` | No | `jaw-angle-up` / `jaw-angle-down` |
| | `jaw_squareness` | No | `jaw-square-incr` / `jaw-square-decr` |
| | `double_chin` | No | `chin-doublechin-incr` / `chin-doublechin-decr` |
| **Cheeks & Temples**| `cheekbone_prominence`| Yes (L/R) | `l/r-cheek-bones-incr` / `l/r-cheek-bones-decr` |
| | `cheek_fullness` | Yes (L/R) | `l/r-cheek-volume-incr` / `l/r-cheek-volume-decr` |
| | `temple_depth` | Yes (L/R) | `l/r-temple-in` / `l/r-temple-out` |
| **Ears** | `ear_protrusion` | Yes (L/R) | `l/r-ear-rot-incr` / `l/r-ear-rot-decr` |
| | `earlobe_size` | Yes (L/R) | `l/r-ear-lobe-scale-incr` / `l/r-ear-lobe-scale-decr` |
| **Forehead & Head** | `forehead_size` | No | `forehead-scale-vert-incr` / `forehead-scale-vert-decr` |
| | `forehead_slope` | No | `forehead-slope-forward` / `forehead-slope-backward` |
| | `head_width` | No | `head-scale-horiz-incr` / `head-scale-horiz-decr` |
| | `head_height` | No | `head-scale-vert-incr` / `head-scale-vert-decr` |

---

### Hairstyle & Eyebrow Customization

Witnesses frequently recall distinctive hair and eyebrow profiles. CrimeSketchAI includes verified asset libraries loaded via MPFB asset equip calls:

* **Hairstyles**:
  * `afro01` (Afro / natural textured curls)
  * `bob01` / `bob02` (Short & medium bob cuts)
  * `braid01` (Braided hair)
  * `long01` (Long straight hair)
  * `ponytail01` (Tied back ponytail)
  * `short01` through `short04` (Neat cropped, side-part, and layered cuts)
  * `bald` (Clean removal of existing hair assets)
* **Eyebrows**:
  * `eyebrow001` through `eyebrow012` (Thin, thick, arched, flat, curved, and bushier variants)

---

### 1-Click Generate & Apply Workflow

Rather than requiring the investigator to navigate multiple preview and confirmation screens, CrimeSketchAI provides a seamless **1-Click "Generate & Apply"** button:
1. **Semantic / Rule Parsing**: Converts input text into target deltas.
2. **Pre-Mutation State Drift Check**: Queries Blender port 9877 to verify the character's active target values match the baseline.
3. **Atomic Socket Mutation**: Dispatches `set_targets` JSON-RPC over the bridge to mutate the 3D character `Human`.
4. **Immediate Read-Back Verification**: Reads back target values from Blender, verifying that proposed features match within `±0.001` tolerance and unrelated features were unaffected.
5. **UI Update**: Renders the comparison diff table, status pills, and marks the SQLite audit record as `APPLIED`.

---

### Forensic Pencil Sketch Rendering Pipeline

Renders an authentic, monochrome forensic pencil-sketch portrait from the live 3D character in Blender:
1. **Camera Staging**: Positions an 85mm focal-length portrait lens framed directly at the character's facial bounding volume.
2. **Cavity Shading**: Renders via Blender's Workbench engine with dual-pass cavity shading (ridges and valleys) to capture fine anatomical contours.
3. **Graphite Post-Processing**:
   - Inverts the raw image and applies a Gaussian blur mask ($r=5$).
   - Computes a mathematical color dodge line art layer: $\text{Dodge} = \text{clip}\left(\frac{\text{Raw} \times 255}{255 - \text{Blur}}, 0, 255\right)$.
   - Blends line art ($65\%$) with soft tonal shading ($35\%$) to preserve 3D volume.
   - Enforces a pure `#FFFFFF` forensic background mask.
   - Applies $1.15\times$ contrast boost simulating 2B/4B forensic graphite pencils.
4. **Output**: Generates a standard $1024 \times 1024$ PNG image saved in `sketches/` and displayed directly in the UI.

---

### Chain-of-Custody Audit Trail

Forensic software must provide reproducible audit trails for legal admissibility. Every request is stored in SQLite (`refinements.db`):
* Incremental log ID and UTC timestamp
* Forensic Case Identifier (e.g., `CASE-2026-001`)
* Raw eyewitness input text
* Parser mode (`ai` vs `rule_based`) and Ollama model (`qwen3:4b`)
* Target modifier details, pre-values, deltas, and post-values
* Verification status (`PASSED (±0.001)` vs `FAILED`)

---

## 3. Prerequisites

* **Operating System**: Windows 10/11 (PowerShell 5.1 or PowerShell 7)
* **Blender**: Version **5.2** (or 4.2+) installed at `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
* **MPFB Add-on**: **MPFB2** (MakeHuman Plugin for Blender v2.0.2+)
* **Python**: Version **3.10** or higher
* **Node.js**: Version **v18+** and npm
* **Ollama**: Local instance with `qwen3:4b` model installed

---

## 4. Step-by-Step Setup Guide

### Step 1: Install Blender 5.2

1. Download Blender 5.2 from the official website: [https://www.blender.org/download/](https://www.blender.org/download/)
2. Run the installer and install to the default location:
   ```text
   C:\Program Files\Blender Foundation\Blender 5.2\
   ```
3. Launch Blender once to complete initial preferences initialization, then close it.

---

### Step 2: Install & Configure the MPFB Add-on

1. Download the latest **MPFB2** add-on zip (`mpfb2.zip`) from [http://mpfb.net](http://mpfb.net) or [https://github.com/makehumancommunity/mpfb2](https://github.com/makehumancommunity/mpfb2).
2. Open Blender 5.2.
3. In the top menu, go to **Edit** → **Preferences** → **Add-ons**.
4. Click the **Install...** (or arrow icon in top right) and select the downloaded `mpfb2.zip` file.
5. In the add-on search bar, type `MPFB` and check the box to **enable** **MakeHuman Plugin for Blender (MPFB)**.
6. **Download MPFB System Assets**:
   - In the Blender 3D Viewport, press `N` to open the right sidebar.
   - Click on the **MPFB** tab.
   - Expand the **Operations** / **Assets** section.
   - Click **Download system assets** (downloads base body meshes, targets, and clothes/hair).

---

### Step 3: Create the 3D Character ("Human")

CrimeSketchAI enforces hard object-name safety locking to prevent accidental corruption of other scene objects. The target character must be named **`Human`**.

1. In Blender, in the 3D Viewport sidebar under **MPFB** tab:
   - Click **Create human** → **New human**.
   - Choose a baseline human (e.g. *Generic neutral adult human*).
   - Click **Create**.
2. In the top-right **Outliner** panel:
   - Locate the generated human mesh object.
   - Double-click the object and rename it to exactly:
     ```text
     Human
     ```
   *(Note: Ensure the active mesh object name is `Human`, capitalized exactly as shown).*
3. Save your Blender project file for easy reload (e.g., `C:\Dept\CrimeSketchAI\workspace.blend`).

---

### Step 4: Start the MPFB Socket Bridge

The MPFB Socket Bridge allows CrimeSketchAI's backend to communicate with Blender over a local JSON-RPC socket.

1. In the Blender 3D Viewport sidebar (`N` panel), select the **MPFB** tab.
2. Scroll to the **Developer** or **Socket Server** section.
3. Configure the bridge settings:
   - **Host**: `127.0.0.1`
   - **Port**: `9877`
4. Click the button:
   ```text
   [ Start MPFB Bridge ]
   ```
5. You should see a confirmation notification in Blender:
   ```text
   Socket server started on 127.0.0.1:9877
   ```
> **Important:** Keep Blender open in the background with the bridge running while using CrimeSketchAI.

---

### Step 5: Setup Local Ollama AI

1. Download and install Ollama from [https://ollama.com/download/windows](https://ollama.com/download/windows).
2. Open a PowerShell terminal and pull the Qwen 3 4B parameter model:
   ```powershell
   ollama pull qwen3:4b
   ```
3. Verify that Ollama is serving requests on `http://127.0.0.1:11434`:
   ```powershell
   curl http://127.0.0.1:11434/api/tags
   ```
   *(You should see `qwen3:4b` in the returned JSON list).*

---

### Step 6: Setup & Run FastAPI Backend

1. Open PowerShell and navigate to the `CrimeSketchAI` project root:
   ```powershell
   cd C:\Dept\CrimeSketchAI
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install backend dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Verify backend configuration in `backend/config.py` (or create a `.env` file):
   ```ini
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=qwen3:4b
   OLLAMA_TIMEOUT_SECONDS=180.0
   MPFB_BRIDGE_HOST=127.0.0.1
   MPFB_BRIDGE_PORT=9877
   BLENDER_TIMEOUT_SECONDS=3.0
   ```
5. Start the FastAPI Uvicorn server:
   ```powershell
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
6. Verify backend health in your browser or curl:
   ```text
   http://127.0.0.1:8000/health
   ```
   Interactive Swagger docs are available at:
   ```text
   http://127.0.0.1:8000/docs
   ```

---

### Step 7: Setup & Run React Frontend

1. Open a new PowerShell terminal and navigate to the `frontend` folder:
   ```powershell
   cd C:\Dept\CrimeSketchAI\frontend
   ```
2. Install npm dependencies:
   ```powershell
   npm install
   ```
3. Start the Vite development server:
   ```powershell
   npm run dev
   ```
4. Open your browser and navigate to:
   ```text
   http://localhost:5173
   ```
5. Confirm that the top status pills show:
   - **Backend API**: `Online (v0.1.0)`
   - **Blender 5.2 Bridge**: `Connected (Human)`

---

## 5. Witness Prompting Guide & Examples

CrimeSketchAI accepts natural-language witness observations in plain English.

### Single-Feature Commands
* *"Make the nose slightly wider."*
* *"Increase the chin prominence slightly."*
* *"Make the cheekbones more prominent."*
* *"Make the eyes slightly larger."*
* *"Add a prominent dorsal hump to the nose."*
* *"Make the lips fuller with a defined cupid's bow."*

### Multi-Feature Witness Descriptions
* *"A person with a broad nose, prominent cheekbones, a slightly pointed chin, small eyes, and a narrow face."*
* *"Suspect has hooded eyelids with bags under their eyes, thin lips, and a square jaw."*
* *"Make the head narrower, the forehead taller, and give them protruding ears."*

### Hairstyle & Eyebrow Styling
* *"A suspect with an afro and a wide jaw."*
* *"Change the hairstyle to a bob cut and thin curved eyebrows."*
* *"Make the suspect bald with bushy eyebrows."*
* *"A person with a neat side-parted haircut, thin arched eyebrows, and high cheekbones."*

---

## 6. REST API Reference

### `GET /health`
Returns connection status across the database, Blender socket bridge, and Ollama service.
```json
{
  "status": "healthy",
  "app_name": "CrimeSketchAI Refinement Backend",
  "version": "0.1.0",
  "allowlist_count": 38,
  "data_source_mode": "live_blender",
  "database_connected": true,
  "ollama_available": true,
  "ollama_model": "qwen3:4b"
}
```

### `GET /state?character_name=Human`
Queries active morph targets directly from Blender over port 9877 without mutating state.

### `POST /refine`
Performs dry-run semantic interpretation. Returns proposed modifiers, target shape keys, and delta values.
```json
{
  "text": "Make the nose slightly wider.",
  "case_id": "CASE-2026-001",
  "character_name": "Human",
  "parser_mode": "ai",
  "use_live_state": true
}
```

### `POST /apply`
Applies an approved dry-run preview directly to the Blender `Human` character. Performs pre-mutation drift checks and post-mutation read-back verification.
```json
{
  "preview_log_id": 42,
  "case_id": "CASE-2026-001",
  "character_name": "Human",
  "confirm_apply": true
}
```

### `POST /render-sketch`
Executes the headless 85mm portrait camera staging, cavity shading pass, and PIL graphite filter.
```json
{
  "character_name": "Human",
  "case_id": "CASE-2026-001"
}
```
**Response**:
```json
{
  "status": "SUCCESS",
  "image_url": "/sketches/sketch_20261028_CASE-2026-001_34d74d.png",
  "filename": "sketch_20261028_CASE-2026-001_34d74d.png",
  "width": 1024,
  "height": 1024,
  "filesize_bytes": 355305,
  "character_name": "Human",
  "case_id": "CASE-2026-001"
}
```

### `GET /logs?limit=25&case_id=CASE-2026-001`
Retrieves chain-of-custody audit logs from SQLite.

---

## 7. Safety & Forensic Integrity Protocol

1. **Character Locking**: All mutations are strictly hard-locked to target object `"Human"`. Requests targeting other objects or attempting wildcard mutations are rejected.
2. **Anti-Drift Protection**: If Blender target values were modified out-of-band between the dry-run preview and apply request, `/apply` halts and rejects the mutation.
3. **Bounded Morph Targets**: Every modifier proposal is strictly clamped to `[-1.0, 1.0]`. If a witness requests a change beyond anatomical boundaries, the modifier is clamped and a warning is logged.
4. **Read-Back Verification**: Post-mutation verification checks that the new live Blender value matches the expected value within $\pm 0.001$, confirming zero socket transmission error.
5. **Zero Cloud Biometrics**: All parsing (Ollama) and rendering (Blender + PIL) run 100% on local loopback addresses (`127.0.0.1`).

---

## 8. Automated Test Suites

### Backend Pytest Suite (174 Tests)
Validates parser accuracy, asset catalogs, allowlist validation, Ollama timeouts, bridge socket communications, pre-mutation checks, read-back verification, and sketch filtering:
```powershell
cd C:\Dept\CrimeSketchAI
pytest -v
```
Output:
```text
======================= 174 passed in 5.93s =======================
```

### Frontend Vitest Suite (29 Tests)
Validates UI rendering, single-button workflow, comparison diff tables, sketch canvas, accessibility attributes, and audit history:
```powershell
cd C:\Dept\CrimeSketchAI\frontend
npm test
```
Output:
```text
Test Files  5 passed (5)
     Tests  29 passed (29)
```

---

## 9. Troubleshooting & FAQs

### Q: Blender Bridge status shows "Disconnected" or "Connection Refused (127.0.0.1:9877)"
* **Solution**: Ensure Blender is open. In the sidebar (`N` panel) under **MPFB** tab → **Developer / Socket Server**, verify the port is `9877` and click **Start MPFB Bridge**. The console should confirm the socket server is running.

### Q: Error: "Object 'Human' not found in Blender scene"
* **Solution**: CrimeSketchAI enforces strict character locking. In the Blender Outliner, verify that your base human character mesh is named exactly `Human` (case-sensitive).

### Q: Ollama request times out or takes longer than expected
* **Solution**: The backend default timeout is set to `180.0` seconds in `backend/config.py` to allow reasoning models to run smoothly on CPUs. If you have an NVIDIA GPU, ensure Ollama detects CUDA:
  ```powershell
  ollama run qwen3:4b "Hello"
  ```

### Q: How do I export or download the rendered forensic sketch?
* **Solution**: In the React frontend, when you click **Generate Sketch**, the rendered $1024 \times 1024$ PNG appears in the right panel with a one-click **Download** button. Files are also stored permanently in `CrimeSketchAI/sketches/`.

---

## License

This software is developed for academic, research, and authorized forensic investigative workflows under the HackFest 2026 NeuraCrime ecosystem.
