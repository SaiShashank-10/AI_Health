"""
Orchestrator Agent — routes the patient to the appropriate modality
specialist(s) based on risk level, symptom profile, and patient preferences.

Pipeline role:  THIRD agent (after Triage).
Input:          RiskLevel, list[SymptomObject], PatientIntake
Output:         care_path (list[CareStep])

Enforces:
  - Max 2 parallel modalities (unless clinician override)
  - Emergency → allopathy-only override
  - Patient modality preferences respected when safe
"""
from __future__ import annotations

from datetime import datetime

from backend.schemas.common import (
    RiskLevel,
    Modality,
    CareStep,
    SymptomObject,
    DoshaType,
    AgentTrace,
    AgentName,
    AgentStatus,
)
from backend.schemas.intake import PatientIntake
from backend.config import settings
from backend.services.doctor_recommender import infer_modality_scores


# ═══════════════════════════════════════════════════════════════════
#  MODALITY SELECTION LOGIC
# ═══════════════════════════════════════════════════════════════════

# Conditions that are best suited for specific modalities
MODALITY_STRENGTH: dict[str, dict[str, float]] = {
    "allopathy": {
        "chest pain": 1.0, "breathlessness": 1.0, "palpitations": 1.0,
        "fever": 0.9, "urinary tract infection": 0.95,
        "skin infection": 0.9, "diarrhea": 0.85, "vomiting": 0.85,
        "headache": 0.7, "hypertension": 0.9, "diabetes": 0.9,
        "cough": 0.7, "stomach pain": 0.7, "back pain": 0.6,
        "joint pain": 0.7, "anxiety": 0.7, "insomnia": 0.6,
        "rash": 0.8, "swelling": 0.7, "blurred vision": 0.9,
    },
    "ayurveda": {
        "joint pain": 0.85, "back pain": 0.8, "body pain": 0.8,
        "constipation": 0.85, "acidity": 0.85, "stomach pain": 0.7,
        "insomnia": 0.8, "anxiety": 0.75, "fatigue": 0.8,
        "weakness": 0.8, "cold": 0.7, "cough": 0.65,
        "headache": 0.6, "itching": 0.65, "loss of appetite": 0.75,
        "weight loss": 0.6, "fever": 0.5, "rash": 0.5,
        "hypertension": 0.6, "diabetes": 0.5, "dizziness": 0.6,
    },
    "homeopathy": {
        "rash": 0.7, "itching": 0.7, "anxiety": 0.65,
        "insomnia": 0.65, "cold": 0.6, "headache": 0.55,
        "joint pain": 0.5, "stomach pain": 0.5,
    },
    "home_remedial": {
        "cold": 0.7, "cough": 0.65, "sore throat": 0.7,
        "fever": 0.4, "headache": 0.4, "constipation": 0.6,
        "acidity": 0.55, "loss of appetite": 0.5, "fatigue": 0.5,
        "insomnia": 0.5,
    },
}

# Specialist type names per modality
SPECIALIST_NAMES: dict[str, str] = {
    "allopathy": "General Physician / Internal Medicine",
    "ayurveda": "Ayurvedic Vaidya (BAMS)",
    "homeopathy": "Homeopathic Physician (BHMS)",
    "home_remedial": "Home Remedial Advisor",
}


# ═══════════════════════════════════════════════════════════════════
#  CARE PATH BUILDING
# ═══════════════════════════════════════════════════════════════════

def _get_modality_scores(
    symptom_names: list[str],
    preferences: list[str],
) -> dict[str, float]:
    """
    Score each modality based on symptom-modality fit and patient preference.
    """
    scores: dict[str, float] = {}

    for modality, strength_map in MODALITY_STRENGTH.items():
        score = 0.0
        match_count = 0

        for symptom in symptom_names:
            if symptom in strength_map:
                score += strength_map[symptom]
                match_count += 1

        # Average score (normalized by symptom count)
        if match_count > 0:
            score = score / max(match_count, 1)
        else:
            score = 0.1  # Minimal default

        # Preference boost — patient-chosen modalities get a bonus
        if modality in preferences:
            score *= 1.3

        scores[modality] = round(score, 3)

    return scores


def _select_modalities(
    scores: dict[str, float],
    risk_level: RiskLevel,
    preferences: list[str],
    max_parallel: int,
) -> list[tuple[str, str]]:
    """
    Select which modalities to include in the care path.

    Returns list of (modality, priority) tuples.
    priority = "primary" or "complementary"
    """
    # Emergency override: allopathy only
    if risk_level == RiskLevel.EMERGENT:
        return [("allopathy", "primary")]

    # Filter to enabled modalities
    enabled = {"allopathy", "ayurveda"}  # MVP + Phase 2
    if settings.ENABLE_HOMEOPATHY:
        enabled.add("homeopathy")
    if settings.ENABLE_HOME_REMEDIAL:
        enabled.add("home_remedial")

    # Filter scores to enabled and sort descending
    filtered = {
        k: v for k, v in scores.items()
        if k in enabled and v > 0.15
    }
    sorted_modalities = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

    if not sorted_modalities:
        return [("allopathy", "primary")]

    selected: list[tuple[str, str]] = []

    # The top-scoring modality is always primary
    top_modality = sorted_modalities[0][0]
    selected.append((top_modality, "primary"))

    # For urgent cases — primarily allopathy, others complementary
    if risk_level == RiskLevel.URGENT and top_modality != "allopathy":
        # Ensure allopathy is included as primary for urgent
        selected = [("allopathy", "primary")]
        if top_modality != "allopathy":
            selected.append((top_modality, "complementary"))
    else:
        # Add preferred modalities as complementary (up to max_parallel)
        for modality, score in sorted_modalities[1:]:
            if len(selected) >= max_parallel:
                break
            if modality in preferences or score > 0.5:
                selected.append((modality, "complementary"))

    # Ensure at least one patient-preferred modality is included
    selected_mods = {s[0] for s in selected}
    for pref in preferences:
        if pref in enabled and pref not in selected_mods and len(selected) < max_parallel:
            selected.append((pref, "complementary"))

    return selected


# ═══════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR FUNCTION
# ═══════════════════════════════════════════════════════════════════

def build_care_path(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
) -> tuple[list[CareStep], list[str], AgentTrace]:
    """
    Build the optimal care path for the patient.

    Args:
        intake: Original patient intake.
        symptom_objects: Normalized symptoms.
        risk_level: Risk level from triage.

    Returns:
        (care_steps, modality_rationale, agent_trace)
    """
    started_at = datetime.utcnow()
    rationale: list[str] = []

    symptom_names = [s.name for s in symptom_objects]
    inferred_scores, inferred_preferences, recommendation_rationale, model_used = infer_modality_scores(
        intake=intake,
        symptom_objects=symptom_objects,
        risk_level=risk_level,
    )
    preferences = inferred_preferences[: settings.MAX_PARALLEL_MODALITIES]

    # Step 1: Score all modalities
    modality_scores = _get_modality_scores(symptom_names, preferences)
    rationale.append(f"AI-inferred treatment priorities: {preferences} (model={model_used})")
    rationale.append(f"Profile analysis summary: {recommendation_rationale}")
    rationale.append(f"Raw AI modality scores: {inferred_scores}")

    # Step 2: Select modalities based on risk and preferences
    selected = _select_modalities(
        modality_scores,
        risk_level,
        preferences,
        settings.MAX_PARALLEL_MODALITIES,
    )
    rationale.append(
        f"Selected modalities: {selected} "
        f"(max_parallel={settings.MAX_PARALLEL_MODALITIES})"
    )

    # Step 3: Build CareStep objects
    care_steps: list[CareStep] = []
    for idx, (modality, priority) in enumerate(selected):
        # Determine specialist type
        specialist = SPECIALIST_NAMES.get(modality, "General Practitioner")

        # Determine if acute symptoms need specific specialist
        if modality == "allopathy":
            specialist = _get_allopathy_specialist(symptom_names, risk_level)

        # Reason text
        score = modality_scores.get(modality, 0)
        reason = _build_step_reason(
            modality, priority, score, symptom_names, risk_level, preferences
        )

        step = CareStep(
            step_number=idx + 1,
            modality=Modality(modality),
            specialist_type=specialist,
            reason=reason,
            priority=priority,
            is_parallel=(idx > 0 and priority == "complementary"),
        )
        care_steps.append(step)

        rationale.append(
            f"Step {idx+1}: {modality} ({priority}) → {specialist}"
        )

    # Step 4: Emergency override annotation
    if risk_level == RiskLevel.EMERGENT:
        rationale.append(
            "EMERGENCY OVERRIDE: All modalities restricted to allopathy. "
            "Patient must seek immediate emergency care."
        )

    completed_at = datetime.utcnow()
    trace = AgentTrace(
        agent_name=AgentName.ORCHESTRATOR,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=f"risk={risk_level.value}, symptoms={symptom_names}, "
                      f"prefs={preferences}",
        output_summary=f"{len(care_steps)} care step(s): "
                       f"{[(s.modality.value, s.priority) for s in care_steps]}",
    )

    return care_steps, rationale, trace


# ═══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _get_allopathy_specialist(
    symptom_names: list[str], risk_level: RiskLevel
) -> str:
    """Determine the best allopathic specialist based on symptoms."""
    if risk_level == RiskLevel.EMERGENT:
        return "Emergency Medicine Physician"

    # Map dominant symptom to specialist
    specialist_map = {
        "chest pain": "Cardiologist",
        "palpitations": "Cardiologist",
        "breathlessness": "Pulmonologist",
        "cough": "Pulmonologist / General Physician",
        "headache": "Neurologist / General Physician",
        "joint pain": "Orthopedist / Rheumatologist",
        "back pain": "Orthopedist",
        "stomach pain": "Gastroenterologist",
        "acidity": "Gastroenterologist",
        "diarrhea": "Gastroenterologist / General Physician",
        "rash": "Dermatologist",
        "itching": "Dermatologist",
        "skin infection": "Dermatologist",
        "anxiety": "Psychiatrist",
        "insomnia": "Psychiatrist / Sleep Medicine",
        "blurred vision": "Ophthalmologist",
        "frequent urination": "Urologist / Endocrinologist",
        "excessive thirst": "Endocrinologist",
        "urinary tract infection": "Urologist / General Physician",
    }

    for symptom in symptom_names:
        if symptom in specialist_map:
            return specialist_map[symptom]

    return "General Physician / Internal Medicine"


def _build_step_reason(
    modality: str,
    priority: str,
    score: float,
    symptom_names: list[str],
    risk_level: RiskLevel,
    preferences: list[str],
) -> str:
    """Build a human-readable reason for this care path step."""
    parts: list[str] = []

    if priority == "primary":
        parts.append(f"Primary care pathway via {modality}")
    else:
        parts.append(f"Complementary consultation via {modality}")

    # Why this modality
    if modality in preferences:
        parts.append("(patient preferred)")

    if risk_level == RiskLevel.EMERGENT:
        parts.append("— Emergency override: allopathy mandatory")
    elif risk_level == RiskLevel.URGENT:
        parts.append("— Urgent care recommended within 24 hours")

    relevant_symptoms = [
        s for s in symptom_names
        if s in MODALITY_STRENGTH.get(modality, {})
    ]
    if relevant_symptoms:
        parts.append(
            f"for symptoms: {', '.join(relevant_symptoms[:3])}"
        )

    parts.append(f"(match score: {score:.2f})")

    return " ".join(parts)
