"""
FastAPI Application for CrimeSketchAI Natural-Language Refinement.
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models.schemas import (
    RefinementRequest,
    RefinementResponse,
    RefinementApplyRequest,
    RefinementApplyResponse,
    HealthResponse,
    FeatureInfo,
    LiveStateResponse,
    SketchRenderRequest,
    SketchRenderResponse
)
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST
from backend.storage.database import Database
from backend.service.refinement_service import RefinementService
from backend.service.blender_state_service import BlenderStateService
from backend.service.blender_mutation_service import BlenderMutationService
from backend.service.sketch_render_service import SketchRenderService
from backend.parser.ollama_parser import OllamaRefinementParser

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for AI Crime Suspect Facial Sketch Natural-Language Refinement & Live State Inspection."
)

# Enable CORS restricted to frontend development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

db = Database(settings.DATABASE_PATH)
state_service = BlenderStateService()
ai_parser = OllamaRefinementParser()
refinement_service = RefinementService(db=db, state_service=state_service, ai_parser=ai_parser)
mutation_service = BlenderMutationService(db=db, state_service=state_service)
sketch_service = SketchRenderService()
# Backwards compatibility alias
service = refinement_service

# Mount sketches directory for static file serving
settings.SKETCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/sketches", StaticFiles(directory=str(settings.SKETCH_OUTPUT_DIR)), name="sketches")

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": "dry_run",
        "state_model": "offline_cached_reference",
        "live_inspection_available": True,
        "default_parser_mode": settings.PARSER_MODE,
        "ollama_model": settings.OLLAMA_MODEL,
        "docs_url": "/docs",
        "message": "CrimeSketchAI Natural-Language Refinement API. Uses offline verified reference values for refinement; /state provides read-only live Blender inspection."
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    db_connected = False
    try:
        with refinement_service.db.get_connection() as conn:
            conn.execute("SELECT 1")
            db_connected = True
    except Exception:
        db_connected = False

    ollama_ok = False
    try:
        ollama_ok = refinement_service.ai_parser.client.check_health()
    except Exception:
        ollama_ok = False

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        allowlist_count=len(VERIFIED_ALLOWLIST),
        allowlist_features=list(VERIFIED_ALLOWLIST.keys()),
        mode="dry_run",
        data_source_mode="offline_cached_reference",
        database_connected=db_connected,
        parser_mode=settings.PARSER_MODE,
        ollama_model=settings.OLLAMA_MODEL,
        ollama_available=ollama_ok
    )

@app.get("/features", response_model=List[FeatureInfo], tags=["Features"])
def list_allowlisted_features():
    """Returns the explicit allowlist of verified facial features and their target mappings."""
    features = []
    for f in VERIFIED_ALLOWLIST.values():
        features.append(FeatureInfo(
            feature_id=f.feature_id,
            display_name=f.display_name,
            section=f.section,
            category=f.category,
            is_sided=f.is_sided,
            sides=list(f.sides),
            adjustment_step=f.adjustment_step,
            min_value=f.min_value,
            max_value=f.max_value,
            reference_value=f.reference_value,
            baseline_value=f.reference_value,
            value_source="cached_reference",
            target_identifiers=list(f.target_identifiers),
            positive_targets=list(f.positive_targets),
            negative_targets=list(f.negative_targets),
            description=f.description,
            example_increase=f"Increase the {f.display_name} slightly.",
            example_decrease=f"Make the {f.display_name} slightly smaller."
        ))
    return features

@app.get("/state", response_model=LiveStateResponse, tags=["State"])
def get_live_state(
    character_name: Optional[str] = Query("Human", description="Name of character in Blender to inspect")
):
    """
    Read-only inspection endpoint that retrieves the live target stack from Blender
    via MPFB-MCP's get_target_stack tool.
    
    Returns live values for the verified allowlisted features if connected, or unavailable
    status with diagnostic errors if Blender is closed or unreachable. Never substitutes
    cached reference values on failure.
    """
    return state_service.get_live_state(character_name=character_name)

@app.post("/refine", response_model=RefinementResponse, tags=["Refinement"])
def dry_run_refine(request: RefinementRequest):
    """
    Parses natural language refinement commands and generates a dry-run preview.
    
    Strictly dry-run: identifies the target category and proposed delta without
    modifying Blender or calling MPFB mutation tools.
    Caller-supplied 'current_value' is forbidden and rejected.
    """
    response = refinement_service.process_dry_run(request)
    return response

@app.post("/apply", response_model=RefinementApplyResponse, tags=["Mutation"])
def apply_refinement(request: RefinementApplyRequest):
    """
    Applies an approved dry-run preview to the Blender character 'Human' via MPFB-MCP.
    
    Safety constraints enforced:
    - Character must be strictly 'Human'.
    - Explicit confirmation ('confirm_apply: true') is mandatory.
    - Modifiers are loaded exclusively from the server-side audit log of a 'PREVIEW_READY' preview.
    - Every modifier is re-validated against VERIFIED_ALLOWLIST.
    - Previews generated without live state (use_live_state=False) are rejected.
    - Atomic replay protection ensures each preview can only be applied once.
    - Pre-mutation live drift check verifies no changes occurred since preview.
    - Post-mutation live read-back verifies target matches within 0.001 and unrelated features are unchanged.
    """
    return mutation_service.apply_refinement(request)

@app.get("/logs", tags=["Audit Logs"])
def get_audit_logs(
    limit: int = Query(20, ge=1, le=100, description="Max entries to return"),
    case_id: Optional[str] = Query(None, description="Filter by case ID")
):
    """Retrieve audit records of all refinement requests (accepted and rejected)."""
    return refinement_service.db.get_logs(limit=limit, case_id=case_id)

@app.post("/render-sketch", response_model=SketchRenderResponse, tags=["Sketch"])
def render_sketch(request: SketchRenderRequest):
    """
    Renders a clean monochrome forensic pencil-sketch portrait from the actual,
    currently applied Blender character 'Human' (including facial geometry, hair, and eyebrows).
    
    Uses an 85mm portrait camera setup, strips MakeHuman helper geometry, leverages
    Workbench cavity/outline shading, and applies a forensic graphite filter to
    output a 1024x1024 PNG on a clean white background.
    """
    return sketch_service.render_sketch(request)

