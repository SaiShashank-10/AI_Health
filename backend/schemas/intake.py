"""
Patient Intake Schema — captures symptoms, history, preferences, and language.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import Modality


class PatientIntake(BaseModel):
    """
    Core Patient Intake Schema (Prototype).

    Captures everything needed to begin the clinical decision pipeline:
    demographics, symptoms (free text in any language), medical history,
    current medications, and the patient's preferred treatment modalities.
    """

    # ── Identity (pseudonymized) ────────────────────────────
    patient_hash: Optional[str] = Field(
        None,
        description="Pseudonymized patient ID (e.g., p_8fa21). Auto-generated if not provided.",
    )

    # ── Language ────────────────────────────────────────────
    language_pref: str = Field(
        "en",
        description="Primary language code (en, hi, ta, te, bn, mr)",
        examples=["en", "hi", "ta"],
    )

    # ── Demographics ────────────────────────────────────────
    age: int = Field(
        ...,
        ge=0,
        le=150,
        description="Patient age in years",
        examples=[42],
    )
    sex: str = Field(
        ...,
        description="Biological sex (M/F/Other) for clinical relevance",
        examples=["F", "M"],
    )

    # ── Symptoms ────────────────────────────────────────────
    symptom_text: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Raw user description of symptoms, in any supported language",
        examples=["Bukhad aur sardard", "Fever and headache for 3 days"],
    )
    duration_days: Optional[int] = Field(
        None,
        ge=0,
        description="Duration of primary complaint in days",
        examples=[3],
    )

    # ── Medical History ─────────────────────────────────────
    comorbidities: list[str] = Field(
        default_factory=list,
        description="Known pre-existing conditions",
        examples=[["hypertension", "diabetes"]],
    )
    medications: list[str] = Field(
        default_factory=list,
        description="Current medications",
        examples=[["amlodipine", "metformin"]],
    )
    allergies: list[str] = Field(
        default_factory=list,
        description="Known allergies",
        examples=[["penicillin"]],
    )

    # ── Preferences ─────────────────────────────────────────
    modality_preferences: list[str] = Field(
        default_factory=lambda: ["allopathy"],
        description="Requested medical systems",
        examples=[["allopathy", "ayurveda"]],
    )

    # ── Optional context ────────────────────────────────────
    family_history: list[str] = Field(
        default_factory=list,
        description="Relevant family medical history",
    )
    lifestyle_notes: Optional[str] = Field(
        None,
        description="Diet, exercise, stress level, etc.",
    )

    # ── Validators ──────────────────────────────────────────
    @field_validator("language_pref")
    @classmethod
    def validate_language(cls, v: str) -> str:
        supported = {"en", "hi", "ta", "te", "bn", "mr"}
        v = v.lower().strip()
        if v not in supported:
            raise ValueError(
                f"Unsupported language '{v}'. Supported: {sorted(supported)}"
            )
        return v

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in {"M", "F", "OTHER"}:
            raise ValueError("sex must be 'M', 'F', or 'Other'")
        return v

    @field_validator("modality_preferences")
    @classmethod
    def validate_modalities(cls, v: list[str]) -> list[str]:
        valid = {m.value for m in Modality}
        cleaned = []
        for m in v:
            m_lower = m.lower().strip()
            if m_lower in valid:
                cleaned.append(m_lower)
            else:
                # Be lenient — skip unrecognized but warn
                pass
        # Default to allopathy if nothing valid
        return cleaned if cleaned else ["allopathy"]


class IntakeResponse(BaseModel):
    """Response returned after intake submission."""
    session_id: str = Field(..., description="Unique session ID for this consultation")
    status: str = Field("processing", description="Pipeline status")
    message: str = Field("Intake received. Processing through agent pipeline...")
    patient_hash: str = Field(..., description="Pseudonymized patient ID")
