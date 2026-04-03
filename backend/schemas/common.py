"""
Shared enums, base models, and common types used across all schemas.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
#  ENUMS
# ═══════════════════════════════════════════════════════════════════

class RiskLevel(str, Enum):
    """Risk stratification levels for triage."""
    EMERGENT = "emergent"
    URGENT = "urgent"
    ROUTINE = "routine"
    SELF_CARE = "self-care"


class Modality(str, Enum):
    """Supported medical system modalities."""
    ALLOPATHY = "allopathy"
    AYURVEDA = "ayurveda"
    HOMEOPATHY = "homeopathy"
    HOME_REMEDIAL = "home_remedial"


class ReliabilityTier(str, Enum):
    """Evidence reliability classification."""
    A = "A"          # RCT / meta-analysis
    B = "B"          # Observational studies
    T = "T"          # Traditional textual reference
    CAUTION = "Caution"  # Conflicting evidence


class Severity(str, Enum):
    """Symptom severity levels."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class DoshaType(str, Enum):
    """Ayurvedic dosha types."""
    VATA = "vata"
    PITTA = "pitta"
    KAPHA = "kapha"
    VATA_PITTA = "vata-pitta"
    PITTA_KAPHA = "pitta-kapha"
    VATA_KAPHA = "vata-kapha"
    TRIDOSHA = "tridosha"


class AgentName(str, Enum):
    """Names of all agents in the pipeline."""
    NORMALIZATION = "normalization"
    TRIAGE = "triage"
    ORCHESTRATOR = "orchestrator"
    ALLOPATHY = "allopathy_specialist"
    AYURVEDA = "ayurveda_specialist"
    HOMEOPATHY = "homeopathy_specialist"
    HOME_REMEDIAL = "home_remedial_agent"
    SAFETY = "safety_conflict"
    SYNTHESIZER = "recommendation_synthesizer"
    TRANSLATION = "translation_agent"
    FEEDBACK = "feedback_agent"


class AgentStatus(str, Enum):
    """Status of an agent in the pipeline."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class PipelineStatus(str, Enum):
    """Overall pipeline status."""
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    AWAITING_REVIEW = "awaiting_review"


# ═══════════════════════════════════════════════════════════════════
#  SHARED MODELS
# ═══════════════════════════════════════════════════════════════════

class SymptomObject(BaseModel):
    """Normalized symptom representation."""
    name: str = Field(..., description="Standardized symptom name (English)")
    original_text: str = Field(..., description="Original text from patient")
    icd_code: Optional[str] = Field(None, description="ICD-10 code if mapped")
    snomed_code: Optional[str] = Field(None, description="SNOMED CT code if mapped")
    severity: Severity = Field(Severity.MODERATE, description="Assessed severity")
    body_system: Optional[str] = Field(None, description="Affected body system")
    dosha_tag: Optional[DoshaType] = Field(None, description="Ayurvedic dosha association")
    duration_days: Optional[int] = Field(None, description="Duration in days")


class CareStep(BaseModel):
    """A single step in the care path."""
    step_number: int = Field(..., description="Order in the care path")
    modality: Modality = Field(..., description="Medical system for this step")
    specialist_type: str = Field(..., description="Type of specialist to consult")
    reason: str = Field(..., description="Why this step is recommended")
    priority: str = Field("primary", description="primary or complementary")
    is_parallel: bool = Field(False, description="Can run in parallel with another step")


class EvidenceSource(BaseModel):
    """A citation with reliability tier."""
    title: str = Field(..., description="Source title")
    source_type: str = Field(..., description="e.g., WHO Guideline, AYUSH Pharmacopeia")
    reliability_tier: ReliabilityTier = Field(..., description="Evidence quality tier")
    reference_id: Optional[str] = Field(None, description="e.g., DOI, ISBN, guideline ID")
    year: Optional[int] = Field(None, description="Publication year")
    summary: Optional[str] = Field(None, description="Brief summary of the evidence")


class PlanSegment(BaseModel):
    """A modality-specific plan segment."""
    modality: Modality = Field(..., description="Medical system")
    title: str = Field(..., description="Plan segment title")
    recommendations: list[str] = Field(default_factory=list, description="List of recommendations")
    medications: list[str] = Field(default_factory=list, description="Suggested medications/remedies")
    lifestyle: list[str] = Field(default_factory=list, description="Lifestyle suggestions")
    follow_up: Optional[str] = Field(None, description="Follow-up instructions")
    evidence: list[EvidenceSource] = Field(default_factory=list, description="Supporting evidence")
    priority_label: str = Field("primary", description="primary or complementary")
    confidence: float = Field(0.0, description="Confidence score 0-1")


class Warning(BaseModel):
    """Safety warning or contraindication."""
    rule_id: str = Field(..., description="Safety rule identifier")
    severity: str = Field(..., description="high / medium / low")
    message: str = Field(..., description="Human-readable warning")
    affected_modalities: list[Modality] = Field(default_factory=list)
    resolution: Optional[str] = Field(None, description="Suggested resolution")


class AgentTrace(BaseModel):
    """Trace/log entry for a single agent's execution."""
    agent_name: AgentName = Field(..., description="Which agent")
    status: AgentStatus = Field(..., description="Execution status")
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    duration_ms: Optional[int] = Field(None, description="Execution time in ms")
    input_summary: Optional[str] = Field(None, description="Brief input description")
    output_summary: Optional[str] = Field(None, description="Brief output description")
    error: Optional[str] = Field(None, description="Error message if failed")


class AuditEntry(BaseModel):
    """Clinician feedback / audit record."""
    session_id: str
    clinician_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str = Field(..., description="approve / reject / edit")
    target_modality: Optional[Modality] = None
    original_recommendation: Optional[str] = None
    edited_recommendation: Optional[str] = None
    rationale: Optional[str] = None
