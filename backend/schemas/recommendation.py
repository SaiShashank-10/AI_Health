"""
Recommendation Output Schema — the final structured output of the pipeline.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.common import (
    RiskLevel,
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
