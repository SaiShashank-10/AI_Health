"""
FastAPI Application — REST API for the Telehealth Orchestrator.

Endpoints:
  POST /api/intake          — Submit patient intake, run full pipeline
  GET  /api/status/{id}     — Get pipeline status for a session
  GET  /api/recommendation/{id} — Get final recommendation
  POST /api/feedback        — Submit clinician feedback
  GET  /api/glossary/{lang} — Get glossary for a language
  GET  /api/languages       — List supported languages
  GET  /api/health          — Health check
  GET  /api/sessions        — List all sessions
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.schemas.intake import PatientIntake, IntakeResponse
from backend.schemas.recommendation import (
    CareRecommendation,
    PipelineStatusResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from backend.schemas.common import PipelineStatus
from backend.schemas.common import TextTranslationRequest, TextTranslationResponse
from backend.pipeline import (
    run_pipeline,
    store_session,
    get_session,
    get_all_sessions,
    store_audit_entry,
    get_audit_log,
)
from backend.knowledge.glossary import (
    get_glossary_for_language,
    get_all_supported_languages,
)
from backend.services.translation_service import translate_texts
from backend.services.input_validation import validate_intake_payload


# ═══════════════════════════════════════════════════════════════════
#  APP INITIALIZATION
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI Integrative Multilingual Telehealth Orchestrator — "
        "A Hybrid Clinical Decision Support & Care Navigation System "
        "Across Allopathic, Ayurvedic, Homeopathic, and Home-Remedial Practices."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
#  STATIC FILES — Serve Frontend
# ═══════════════════════════════════════════════════════════════════

# Determine frontend path relative to this file
_BACKEND_DIR = Path(__file__).resolve().parent
_FRONTEND_DIR = _BACKEND_DIR.parent / "frontend"

if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serve the frontend SPA."""
    index_path = _FRONTEND_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend not found. Visit /docs for API.</h1>")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    """Serve the Service Worker script from the root scope."""
    sw_path = _FRONTEND_DIR / "sw.js"
    if sw_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(path=sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service worker not found")


@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    """Serve the PWA Web App Manifest."""
    manifest_path = _FRONTEND_DIR / "manifest.json"
    if manifest_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(path=manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="Manifest not found")


# ═══════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "llm_provider": settings.LLM_PROVIDER,
        "supported_languages": settings.SUPPORTED_LANGUAGES,
        "supported_modalities": settings.SUPPORTED_MODALITIES,
    }


# ═══════════════════════════════════════════════════════════════════
#  PATIENT INTAKE — Run Full Pipeline
# ═══════════════════════════════════════════════════════════════════

@app.post(
    "/api/intake",
    response_model=IntakeResponse,
    tags=["Pipeline"],
    summary="Submit patient intake and run the full agent pipeline",
)
async def submit_intake(intake: PatientIntake):
    """
    Submit a patient intake to run through the full 8-agent pipeline.

    The pipeline executes:
    1. Normalization → 2. Triage → 3. Orchestrator →
    4. Allopathy/Ayurveda Specialists → 5. Safety Check →
    6. Synthesizer → 7. Translation

    Returns a session ID to retrieve the full recommendation.
    """
    # Validate every user-provided text field before running AI pipeline.
    validation = validate_intake_payload(intake)
    if not validation.is_valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid or low-quality input detected. Please provide clear symptom details.",
                "reasons": validation.reasons,
                "validation_confidence": validation.confidence,
                "model_used": validation.model_used,
            },
        )

    # Run the pipeline
    state = run_pipeline(intake)

    # Store the session
    store_session(state)

    # Determine response message based on status
    if state.status == PipelineStatus.COMPLETED:
        message = (
            f"Pipeline completed successfully. "
            f"{len(state.agent_traces)} agents executed. "
            f"Risk level: {state.risk_level.value if state.risk_level else 'unknown'}. "
            f"Use GET /api/recommendation/{state.session_id} for full results."
        )
    elif state.status == PipelineStatus.ERROR:
        message = (
            f"Pipeline completed with fallback. Error: {state.error}. "
            f"Partial results available via GET /api/recommendation/{state.session_id}."
        )
    else:
        message = "Processing..."

    return IntakeResponse(
        session_id=state.session_id,
        status=state.status.value,
        message=message,
        patient_hash=state.patient_hash,
    )


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE STATUS
# ═══════════════════════════════════════════════════════════════════

@app.get(
    "/api/status/{session_id}",
    response_model=PipelineStatusResponse,
    tags=["Pipeline"],
    summary="Get pipeline execution status",
)
async def get_pipeline_status(session_id: str):
    """Get the current status of a pipeline execution."""
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return PipelineStatusResponse(
        session_id=state.session_id,
        status=state.status,
        current_agent=state.current_agent,
        agents_completed=len([t for t in state.agent_traces if t.status.value == "completed"]),
        agents_total=len(state.agent_traces),
        message=state.error or "Pipeline completed" if state.status != PipelineStatus.PROCESSING else "Processing...",
    )


# ═══════════════════════════════════════════════════════════════════
#  RECOMMENDATION RETRIEVAL
# ═══════════════════════════════════════════════════════════════════

@app.get(
    "/api/recommendation/{session_id}",
    response_model=CareRecommendation,
    tags=["Pipeline"],
    summary="Get full care recommendation for a session",
)
async def get_recommendation(session_id: str):
    """
    Retrieve the complete care recommendation generated by the pipeline.

    Includes:
    - Risk assessment with justification
    - Care path with specialist routing
    - Plan segments from each modality (medications, lifestyle, evidence)
    - Safety warnings and contraindication checks
    - Multilingual translations
    - Full explainability data
    - Agent execution trace
    """
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not state.recommendation:
        raise HTTPException(
            status_code=202,
            detail="Pipeline is still processing. Try again shortly.",
        )

    return state.recommendation


def _build_final_report(recommendation: CareRecommendation) -> dict[str, Any]:
    """Build a concise, factual report from the persisted recommendation object."""
    primary_step = next(
        (step for step in recommendation.care_path if step.priority == "primary"),
        recommendation.care_path[0] if recommendation.care_path else None,
    )

    key_items: list[str] = []
    for segment in recommendation.plan_segments:
        for item in (segment.recommendations or []):
            if item not in key_items:
                key_items.append(item)
        for item in (segment.medications or []):
            if item not in key_items:
                key_items.append(item)
        for item in (segment.lifestyle or []):
            if item not in key_items:
                key_items.append(item)
    key_recommendations = key_items[:8]

    warnings = [
        {
            "severity": warning.severity,
            "message": warning.message,
            "resolution": warning.resolution,
        }
        for warning in recommendation.warnings
    ]

    top_evidence = sorted(
        recommendation.provenance,
        key=lambda ev: ((ev.reliability_tier or 99), -(ev.year or 0)),
    )[:5]
    evidence = [
        {
            "title": item.title,
            "source_type": item.source_type,
            "year": item.year,
            "reliability_tier": item.reliability_tier,
            "url": item.url,
        }
        for item in top_evidence
    ]

    doctor = recommendation.doctor_recommendation
    care_team = {
        "doctor_name": doctor.doctor_name if doctor else None,
        "specialty": doctor.specialty if doctor else None,
        "consultation_mode": doctor.consultation_mode if doctor else None,
        "next_available_window": doctor.next_available_window if doctor else None,
        "urgency_note": doctor.urgency_note if doctor else None,
    }

    return {
        "session_id": recommendation.session_id,
        "generated_at": recommendation.timestamp.isoformat(),
        "risk_level": recommendation.risk_level,
        "risk_confidence": recommendation.risk_confidence,
        "risk_score": recommendation.risk_score,
        "triage_justification": recommendation.triage_justification,
        "care_team": care_team,
        "primary_care_path": {
            "modality": primary_step.modality if primary_step else None,
            "specialist_type": primary_step.specialist_type if primary_step else None,
            "priority": primary_step.priority if primary_step else None,
            "reason": primary_step.reason if primary_step else None,
        },
        "key_recommendations": key_recommendations,
        "safety_warnings": warnings,
        "evidence": evidence,
        "summary": {
            "care_steps": len(recommendation.care_path),
            "plan_segments": len(recommendation.plan_segments),
            "warnings": len(recommendation.warnings),
            "sources": len(recommendation.provenance),
        },
    }


@app.get(
    "/api/final-report/{session_id}",
    tags=["Pipeline"],
    summary="Get concise final report with factual fields only",
)
async def get_final_report(session_id: str):
    """Return a concise report built from real recommendation data for UI and exports."""
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not state.recommendation:
        raise HTTPException(
            status_code=202,
            detail="Pipeline is still processing. Try again shortly.",
        )

    return _build_final_report(state.recommendation)


# ═══════════════════════════════════════════════════════════════════
#  CLINICIAN FEEDBACK
# ═══════════════════════════════════════════════════════════════════

@app.post(
    "/api/feedback",
    response_model=FeedbackResponse,
    tags=["Clinician"],
    summary="Submit clinician feedback on a care recommendation",
)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit clinician feedback (approve/reject/edit) on a care recommendation.
    Stored in the audit log for continuous improvement.
    """
    state = get_session(feedback.session_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{feedback.session_id}' not found",
        )

    # Validate action
    if feedback.action not in ("approve", "reject", "edit"):
        raise HTTPException(
            status_code=400,
            detail="Action must be 'approve', 'reject', or 'edit'",
        )

    # Store audit entry
    audit_entry = {
        "session_id": feedback.session_id,
        "clinician_id": feedback.clinician_id,
        "action": feedback.action,
        "target_modality": feedback.target_modality,
        "edited_recommendation": feedback.edited_recommendation,
        "rationale": feedback.rationale,
        "patient_hash": state.patient_hash,
        "risk_level": state.risk_level.value if state.risk_level else None,
    }
    audit_id = store_audit_entry(audit_entry)

    return FeedbackResponse(
        success=True,
        message=f"Feedback '{feedback.action}' recorded successfully for session {feedback.session_id}.",
        audit_id=audit_id,
    )


# ═══════════════════════════════════════════════════════════════════
#  GLOSSARY & LANGUAGES
# ═══════════════════════════════════════════════════════════════════

@app.get(
    "/api/glossary/{lang_code}",
    tags=["Reference"],
    summary="Get medical glossary for a specific language",
)
async def get_glossary(lang_code: str):
    """
    Retrieve the medical terminology glossary translated to the
    specified language code (hi, ta, te, bn, mr).
    """
    if lang_code not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang_code}'. "
                   f"Supported: {settings.SUPPORTED_LANGUAGES}",
        )

    glossary = get_glossary_for_language(lang_code)
    return {
        "language_code": lang_code,
        "total_terms": len(glossary),
        "glossary": glossary,
    }


@app.get(
    "/api/languages",
    tags=["Reference"],
    summary="List all supported languages",
)
async def list_languages():
    """List all supported languages with codes and native names."""
    return {
        "supported_languages": get_all_supported_languages(),
        "default": settings.DEFAULT_LANGUAGE,
    }


@app.post(
    "/api/translate/text",
    response_model=TextTranslationResponse,
    tags=["System"],
    summary="Translate a batch of text snippets using the medical glossary",
)
async def translate_text_batch(payload: TextTranslationRequest):
    """Translate arbitrary text snippets into a supported language."""
    lang_code = payload.language_code.lower().strip()
    if lang_code not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{lang_code}'. Supported: {settings.SUPPORTED_LANGUAGES}",
        )

    translated_texts = translate_texts(payload.texts, lang_code)
    return TextTranslationResponse(
        language_code=lang_code,
        translated_texts=translated_texts,
    )


# ═══════════════════════════════════════════════════════════════════
#  SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@app.get(
    "/api/sessions",
    tags=["System"],
    summary="List all active sessions",
)
async def list_sessions():
    """List all session IDs in the system."""
    sessions = get_all_sessions()
    session_summaries = []
    for sid in sessions:
        state = get_session(sid)
        if state:
            session_summaries.append({
                "session_id": sid,
                "patient_hash": state.patient_hash,
                "status": state.status.value,
                "risk_level": state.risk_level.value if state.risk_level else None,
                "agents_completed": len(state.agent_traces),
                "created_at": state.started_at.isoformat() if state.started_at else None,
            })
    return {"total_sessions": len(sessions), "sessions": session_summaries}


@app.get(
    "/api/audit",
    tags=["Clinician"],
    summary="Get the clinician audit log",
)
async def get_audit():
    """Retrieve the complete clinician feedback audit log."""
    log = get_audit_log()
    return {"total_entries": len(log), "audit_log": log}


# ═══════════════════════════════════════════════════════════════════
#  RUN CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL,
    )
