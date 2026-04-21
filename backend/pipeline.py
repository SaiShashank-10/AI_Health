"""
Pipeline Orchestration — chains all 8 agents in the correct sequence
with state management, error handling, and fallback to rule-only triage.

Flow:
  1. Normalization Agent
  2. Triage Agent
  3. Orchestrator Agent
  4. Specialist Agents (Allopathy, Ayurveda — parallel where possible)
  5. Safety & Conflict Agent
  6. Recommendation Synthesizer
  7. Translation Agent

State is managed via PipelineState dataclass passed between agents.
"""
from __future__ import annotations

import hashlib
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.schemas.common import (
    RiskLevel,
    Modality,
    DoshaType,
    SymptomObject,
    CareStep,
    PlanSegment,
    Warning,
    EvidenceSource,
    AgentTrace,
    AgentName,
    AgentStatus,
    PipelineStatus,
)
from backend.schemas.intake import PatientIntake
from backend.schemas.recommendation import CareRecommendation

# Agent imports
from backend.agents.normalization import normalize_intake
from backend.agents.triage import run_triage
from backend.agents.orchestrator import build_care_path
from backend.agents.allopathy import generate_allopathy_plan
from backend.agents.ayurveda import generate_ayurveda_plan
from backend.agents.safety import run_safety_checks
from backend.agents.synthesizer import synthesize_recommendation
from backend.agents.translation import translate_recommendation


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE STATE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PipelineState:
    """Mutable state passed through the pipeline."""
    # Identity
    session_id: str = ""
    patient_hash: str = ""
    intake: Optional[PatientIntake] = None

    # Pipeline status
    status: PipelineStatus = PipelineStatus.CREATED
    current_agent: Optional[str] = None
    error: Optional[str] = None

    # Agent outputs
    symptom_objects: list[SymptomObject] = field(default_factory=list)
    risk_level: Optional[RiskLevel] = None
    risk_confidence: float = 0.0
    risk_score: float = 0.0
    triage_justification: str = ""
    risk_factors: list[str] = field(default_factory=list)

    care_steps: list[CareStep] = field(default_factory=list)
    modality_rationale: list[str] = field(default_factory=list)

    plan_segments: list[PlanSegment] = field(default_factory=list)
    dominant_dosha: Optional[DoshaType] = None
    dosha_scores: dict[str, float] = field(default_factory=dict)

    warnings: list[Warning] = field(default_factory=list)
    checks_performed: list[str] = field(default_factory=list)

    # Final output
    recommendation: Optional[CareRecommendation] = None

    # Traces
    agent_traces: list[AgentTrace] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════
#  PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════

def _generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess_{uuid.uuid4().hex[:12]}"


def _generate_patient_hash(intake: PatientIntake) -> str:
    """Generate or use existing patient hash."""
    if intake.patient_hash:
        return intake.patient_hash
    raw = f"{intake.age}_{intake.sex}_{intake.symptom_text[:20]}_{datetime.utcnow().isoformat()}"
    return f"p_{hashlib.md5(raw.encode()).hexdigest()[:8]}"


def run_pipeline(intake: PatientIntake) -> PipelineState:
    """
    Execute the full agent pipeline.

    This is the main entry point. It runs all agents in sequence,
    manages state between them, and handles errors with fallback.

    Args:
        intake: Validated PatientIntake from the API.

    Returns:
        PipelineState with all results and the final CareRecommendation.
    """
    state = PipelineState(
        session_id=_generate_session_id(),
        patient_hash=_generate_patient_hash(intake),
        intake=intake,
        status=PipelineStatus.PROCESSING,
        started_at=datetime.utcnow(),
    )

    try:
        # ── AGENT 1: Normalization ─────────────────────────
        state.current_agent = AgentName.NORMALIZATION.value
        state.symptom_objects, trace = normalize_intake(intake)
        state.agent_traces.append(trace)

        # ── AGENT 2: Triage ────────────────────────────────
        state.current_agent = AgentName.TRIAGE.value
        (
            state.risk_level,
            state.risk_confidence,
            state.triage_justification,
            state.risk_factors,
            state.risk_score,
            trace,
        ) = run_triage(intake, state.symptom_objects)
        state.agent_traces.append(trace)

        # ── AGENT 3: Orchestrator ──────────────────────────
        state.current_agent = AgentName.ORCHESTRATOR.value
        (
            state.care_steps,
            state.modality_rationale,
            trace,
        ) = build_care_path(intake, state.symptom_objects, state.risk_level)
        state.agent_traces.append(trace)

        # ── AGENTS 4-5: Specialist Agents ──────────────────
        # Determine which modalities to call based on care path
        modalities_to_call = {step.modality for step in state.care_steps}

        # Allopathy Specialist
        if Modality.ALLOPATHY in modalities_to_call:
            state.current_agent = AgentName.ALLOPATHY.value
            is_primary = any(
                s.modality == Modality.ALLOPATHY and s.priority == "primary"
                for s in state.care_steps
            )
            allo_plan, trace = generate_allopathy_plan(
                intake, state.symptom_objects, state.risk_level,
                is_primary=is_primary,
            )
            state.plan_segments.append(allo_plan)
            state.agent_traces.append(trace)

        # Ayurveda Specialist
        if Modality.AYURVEDA in modalities_to_call:
            state.current_agent = AgentName.AYURVEDA.value
            is_primary = any(
                s.modality == Modality.AYURVEDA and s.priority == "primary"
                for s in state.care_steps
            )
            ayur_plan, dosha, scores, trace = generate_ayurveda_plan(
                intake, state.symptom_objects, state.risk_level,
                is_primary=is_primary,
            )
            state.plan_segments.append(ayur_plan)
            state.dominant_dosha = dosha
            state.dosha_scores = scores
            state.agent_traces.append(trace)

        # Homeopathy (stub — Phase 4)
        if Modality.HOMEOPATHY in modalities_to_call and settings.ENABLE_HOMEOPATHY:
            state.agent_traces.append(AgentTrace(
                agent_name=AgentName.HOMEOPATHY,
                status=AgentStatus.SKIPPED,
                input_summary="Homeopathy not yet implemented (Phase 4)",
                output_summary="Skipped",
            ))

        # Home Remedial (stub — Phase 4)
        if Modality.HOME_REMEDIAL in modalities_to_call and settings.ENABLE_HOME_REMEDIAL:
            state.agent_traces.append(AgentTrace(
                agent_name=AgentName.HOME_REMEDIAL,
                status=AgentStatus.SKIPPED,
                input_summary="Home remedial not yet implemented (Phase 4)",
                output_summary="Skipped",
            ))

        # ── AGENT 6: Safety & Conflict ─────────────────────
        state.current_agent = AgentName.SAFETY.value
        (
            state.warnings,
            state.checks_performed,
            trace,
        ) = run_safety_checks(
            intake, state.symptom_objects, state.plan_segments, state.risk_level,
        )
        state.agent_traces.append(trace)

        # ── AGENT 7: Recommendation Synthesizer ────────────
        state.current_agent = AgentName.SYNTHESIZER.value
        recommendation, trace = synthesize_recommendation(
            session_id=state.session_id,
            patient_hash=state.patient_hash,
            intake=intake,
            symptom_objects=state.symptom_objects,
            risk_level=state.risk_level,
            risk_confidence=state.risk_confidence,
            risk_score=state.risk_score,
            triage_justification=state.triage_justification,
            risk_factors=state.risk_factors,
            care_steps=state.care_steps,
            plan_segments=state.plan_segments,
            warnings=state.warnings,
            modality_rationale=state.modality_rationale,
            checks_performed=state.checks_performed,
            agent_traces=state.agent_traces,
        )
        state.agent_traces.append(trace)

        # ── AGENT 8: Translation ───────────────────────────
        state.current_agent = AgentName.TRANSLATION.value
        target_langs = (
            [intake.language_pref]
            if intake.language_pref != "en"
            else ["hi"]  # Default to Hindi if English
        )
        # Always include at least Hindi + the patient's language
        if "hi" not in target_langs:
            target_langs.append("hi")

        translations, trace = translate_recommendation(
            recommendation, target_langs
        )
        recommendation.translations = translations
        recommendation.agent_trace = state.agent_traces + [trace]
        state.agent_traces.append(trace)

        # ── COMPLETE ───────────────────────────────────────
        state.recommendation = recommendation
        state.status = PipelineStatus.COMPLETED
        state.current_agent = None
        state.completed_at = datetime.utcnow()

    except Exception as e:
        # Fallback: try rule-only triage if pipeline fails
        state.error = str(e)
        state.status = PipelineStatus.ERROR
        state = _fallback_triage(state, intake, str(e))

    return state


# ═══════════════════════════════════════════════════════════════════
#  FALLBACK — RULE-ONLY TRIAGE
# ═══════════════════════════════════════════════════════════════════

def _fallback_triage(
    state: PipelineState,
    intake: PatientIntake,
    error_msg: str,
) -> PipelineState:
    """
    Fallback to rule-only triage if the full pipeline fails.
    Provides a minimal but safe recommendation.
    """
    try:
        # Try normalization + triage at minimum
        if not state.symptom_objects:
            state.symptom_objects, trace = normalize_intake(intake)
            state.agent_traces.append(trace)

        if state.risk_level is None:
            (
                state.risk_level,
                state.risk_confidence,
                state.triage_justification,
                state.risk_factors,
                trace,
            ) = run_triage(intake, state.symptom_objects)
            state.agent_traces.append(trace)

        # Build minimal recommendation
        from backend.schemas.recommendation import Explainability, DoctorRecommendation

        fallback_doctor = DoctorRecommendation(
            assignment_id=f"DOC-FALLBACK-{state.session_id[-4:].upper()}",
            doctor_name="Assigned General Medicine Specialist",
            specialty="General Medicine",
            consultation_mode="teleconsult",
            next_available_window="Scheduled consult: within 24 hours",
            urgency_note="Fallback mode enabled; physician review is recommended.",
            automation_locked=True,
            premium_feature="premium_auto_assignment",
            best_modality=None,
            modality_recommendations=[],
        )

        state.recommendation = CareRecommendation(
            session_id=state.session_id,
            patient_hash=state.patient_hash,
            timestamp=datetime.utcnow(),
            pipeline_status=PipelineStatus.ERROR,
            risk_level=state.risk_level,
            risk_confidence=state.risk_confidence,
            risk_score=state.risk_score,
            triage_justification=(
                f"{state.triage_justification} "
                f"[FALLBACK MODE: Full pipeline encountered an error: {error_msg}. "
                f"Only triage results are available. Please consult a physician.]"
            ),
            care_path=state.care_steps,
            plan_segments=state.plan_segments,
            warnings=state.warnings,
            provenance=[],
            translations=[],
            doctor_recommendation=fallback_doctor,
            explainability=Explainability(
                risk_factors=state.risk_factors,
                risk_adjustments=[f"FALLBACK: Pipeline error — {error_msg}"],
                contraindication_checks=[],
                modality_selection_rationale=[],
                rule_triggers=[],
            ),
            agent_trace=state.agent_traces,
        )
        state.status = PipelineStatus.ERROR

    except Exception:
        # If even fallback fails, set minimal error state
        state.status = PipelineStatus.ERROR
        state.recommendation = None

    state.completed_at = datetime.utcnow()
    return state


# ═══════════════════════════════════════════════════════════════════
#  IN-MEMORY SESSION STORE
# ═══════════════════════════════════════════════════════════════════

# Simple in-memory store for prototype (swap to DB in production)
_session_store: dict[str, PipelineState] = {}


def store_session(state: PipelineState) -> None:
    """Store a pipeline state by session ID."""
    _session_store[state.session_id] = state


def get_session(session_id: str) -> Optional[PipelineState]:
    """Retrieve a pipeline state by session ID."""
    return _session_store.get(session_id)


def get_all_sessions() -> list[str]:
    """List all session IDs."""
    return list(_session_store.keys())


# Audit log for clinician feedback
_audit_log: list[dict] = []
_DATA_DIR = Path(__file__).resolve().parent / "data"
_AUDIT_FILE = _DATA_DIR / "audit_log.jsonl"


def _load_audit_log_from_disk() -> list[dict]:
    """Load persisted audit entries from disk if present."""
    if not _AUDIT_FILE.exists():
        return []

    entries: list[dict] = []
    try:
        for line in _AUDIT_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return entries


def _append_audit_entry_to_disk(entry: dict) -> None:
    """Append one audit entry to the JSONL file."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with _AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # Keep runtime behavior even if disk persistence fails.
        pass


_audit_log = _load_audit_log_from_disk()


def store_audit_entry(entry: dict) -> str:
    """Store an audit entry and return its ID."""
    audit_id = f"audit_{uuid.uuid4().hex[:8]}"
    entry["audit_id"] = audit_id
    entry["timestamp"] = datetime.utcnow().isoformat()
    _audit_log.append(entry)
    _append_audit_entry_to_disk(entry)
    return audit_id


def get_audit_log() -> list[dict]:
    """Return all audit entries."""
    return _audit_log
