"""
Recommendation Output Schema — the final structured output of the pipeline.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.common import (
    RiskLevel,
    Modality,
    CareStep,
    PlanSegment,
    Warning,
    EvidenceSource,
    AgentTrace,
    PipelineStatus,
)


class Explainability(BaseModel):
    """Explainability breakdown for the recommendation."""
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Factors that influenced the risk assessment",
    )
    risk_adjustments: list[str] = Field(
        default_factory=list,
        description="Adjustments made to the initial risk score",
    )
    contraindication_checks: list[str] = Field(
        default_factory=list,
        description="Contraindication checks performed",
    )
    modality_selection_rationale: list[str] = Field(
        default_factory=list,
        description="Why specific modalities were selected",
    )
    rule_triggers: list[str] = Field(
        default_factory=list,
        description="Safety rules that were triggered",
    )


class TranslationOutput(BaseModel):
    """Localized text for a specific language."""
    language_code: str = Field(..., description="Language code (e.g., hi, ta)")
    language_name: str = Field(..., description="Language name (e.g., Hindi, Tamil)")
    summary: str = Field(..., description="Translated summary of the care plan")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Translated recommendation items",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Translated warning messages",
    )


class ModalityDoctorTypeRecommendation(BaseModel):
    """Best-fit doctor type recommendation for a specific modality."""
    modality: Modality = Field(..., description="Target medical modality")
    doctor_type: str = Field(..., description="Recommended doctor type for this modality")
    rationale: str = Field(..., description="Why this doctor type fits the current profile")
    suitability_score: float = Field(..., ge=0.0, le=1.0, description="Suitability score")
    recommended: bool = Field(False, description="Whether this modality is actively recommended")


class DoctorRecommendation(BaseModel):
    """Single automated doctor assignment for premium workflow."""
    assignment_id: str = Field(..., description="Unique assignment identifier")
    doctor_name: str = Field(..., description="Assigned doctor display name")
    specialty: str = Field(..., description="Assigned specialty")
    consultation_mode: str = Field(..., description="teleconsult | in-person | hybrid")
    next_available_window: str = Field(..., description="Suggested consultation window")
    urgency_note: str = Field(..., description="Triage-aware urgency guidance")
    automation_locked: bool = Field(
        True,
        description="True when assignment is system-locked with no patient-side options",
    )
    premium_feature: str = Field(
        "premium_auto_assignment",
        description="Premium capability tag",
    )
    best_modality: Optional[Modality] = Field(
        None,
        description="Best overall modality for doctor assignment based on patient profile",
    )
    modality_recommendations: list[ModalityDoctorTypeRecommendation] = Field(
        default_factory=list,
        description="Profile-based doctor type recommendations for each modality",
    )


class CareRecommendation(BaseModel):
    """
    Complete Recommendation Output — the final product of the full agent pipeline.

    Contains risk assessment, care path, plan segments from each modality,
    safety warnings, evidence provenance, multilingual translations,
    and full explainability data.
    """

    # ── Session & Meta ──────────────────────────────────────
    session_id: str = Field(..., description="Session identifier")
    patient_hash: str = Field(..., description="Pseudonymized patient ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pipeline_status: PipelineStatus = Field(PipelineStatus.COMPLETED)

    # ── Risk Assessment ─────────────────────────────────────
    risk_level: RiskLevel = Field(
        ...,
        description="Triage risk: emergent | urgent | routine | self-care",
    )
    risk_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the risk assessment",
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Model-assisted risk score on a 0-100 scale",
    )
    triage_justification: str = Field(
        "",
        description="Plain-text explanation of why this risk level was assigned",
    )

    # ── Care Path ───────────────────────────────────────────
    care_path: list[CareStep] = Field(
        default_factory=list,
        description="Ordered list of modality consultation steps",
    )

    # ── Plan Segments ───────────────────────────────────────
    plan_segments: list[PlanSegment] = Field(
        default_factory=list,
        description="Detailed plan from each consulted modality specialist",
    )

    # ── Safety & Warnings ───────────────────────────────────
    warnings: list[Warning] = Field(
        default_factory=list,
        description="Interaction / contraindication warnings",
    )

    # ── Provenance ──────────────────────────────────────────
    provenance: list[EvidenceSource] = Field(
        default_factory=list,
        description="All evidence sources cited, with reliability tiers",
    )

    # ── Translations ────────────────────────────────────────
    translations: list[TranslationOutput] = Field(
        default_factory=list,
        description="Localized versions of the care plan",
    )

    # ── Premium Automation ─────────────────────────────────
    doctor_recommendation: Optional[DoctorRecommendation] = Field(
        None,
        description="Single automated doctor assignment (no patient-side choice list)",
    )

    # ── Explainability ──────────────────────────────────────
    explainability: Explainability = Field(
        default_factory=Explainability,
        description="Transparency data: what triggered each decision",
    )

    # ── Pipeline Trace ──────────────────────────────────────
    agent_trace: list[AgentTrace] = Field(
        default_factory=list,
        description="Execution log for each agent in the pipeline",
    )


class PipelineStatusResponse(BaseModel):
    """Lightweight status check response."""
    session_id: str
    status: PipelineStatus
    current_agent: Optional[str] = None
    agents_completed: int = 0
    agents_total: int = 0
    message: str = ""


class FeedbackRequest(BaseModel):
    """Clinician feedback submission."""
    session_id: str = Field(..., description="Session to provide feedback on")
    clinician_id: Optional[str] = Field(None, description="Clinician identifier")
    action: str = Field(
        ...,
        description="approve | reject | edit",
    )
    target_modality: Optional[str] = Field(
        None,
        description="Which modality's plan segment to act on",
    )
    edited_recommendation: Optional[str] = Field(
        None,
        description="New text if editing a recommendation",
    )
    rationale: Optional[str] = Field(
        None,
        description="Clinician's reason for the action",
    )


class FeedbackResponse(BaseModel):
    """Response after feedback submission."""
    success: bool
    message: str
    audit_id: str
