"""
Normalization Agent — maps free-text patient symptoms (in any supported
language) to structured SymptomObject instances.

Pipeline role:  FIRST agent in the chain.
Input:          Raw PatientIntake
Output:         list[SymptomObject]

Uses the glossary for multilingual term detection and transliteration,
then maps to ICD-10 / SNOMED codes and Ayurvedic dosha tags.
"""
from __future__ import annotations

import re
from datetime import datetime

from backend.schemas.common import (
    SymptomObject,
    Severity,
    DoshaType,
    AgentTrace,
    AgentName,
    AgentStatus,
)
from backend.schemas.intake import PatientIntake
from backend.knowledge.glossary import detect_language_terms, MEDICAL_GLOSSARY


# ═══════════════════════════════════════════════════════════════════
#  SIMULATED ICD-10 / SNOMED CODE MAPPINGS
# ═══════════════════════════════════════════════════════════════════

ICD10_MAP: dict[str, str] = {
    "fever": "R50.9",
    "headache": "R51",
    "cough": "R05",
    "cold": "J00",
    "sore throat": "J02.9",
    "body pain": "M79.3",
    "joint pain": "M25.50",
    "chest pain": "R07.9",
    "stomach pain": "R10.9",
    "back pain": "M54.9",
    "nausea": "R11.0",
    "vomiting": "R11.10",
    "diarrhea": "R19.7",
    "constipation": "K59.00",
    "dizziness": "R42",
    "fatigue": "R53.83",
    "weakness": "R53.1",
    "breathlessness": "R06.00",
    "palpitations": "R00.2",
    "swelling": "R60.9",
    "rash": "R21",
    "itching": "L29.9",
    "burning sensation": "R20.8",
    "insomnia": "G47.00",
    "anxiety": "F41.9",
    "loss of appetite": "R63.0",
    "weight loss": "R63.4",
    "excessive thirst": "R63.1",
    "frequent urination": "R35.0",
    "blurred vision": "H53.8",
}

SNOMED_MAP: dict[str, str] = {
    "fever": "386661006",
    "headache": "25064002",
    "cough": "49727002",
    "cold": "82272006",
    "sore throat": "162397003",
    "body pain": "279069000",
    "joint pain": "57676002",
    "chest pain": "29857009",
    "stomach pain": "21522001",
    "back pain": "161891005",
    "nausea": "422587007",
    "vomiting": "422400008",
    "diarrhea": "62315008",
    "constipation": "14760008",
    "dizziness": "404640003",
    "fatigue": "84229001",
    "weakness": "13791008",
    "breathlessness": "267036007",
    "palpitations": "80313002",
    "swelling": "65124004",
    "rash": "271807003",
    "itching": "418290006",
    "burning sensation": "90673000",
    "insomnia": "193462001",
    "anxiety": "48694002",
    "loss of appetite": "79890006",
    "weight loss": "89362005",
    "excessive thirst": "17173007",
    "frequent urination": "162116003",
    "blurred vision": "111516008",
}


# ═══════════════════════════════════════════════════════════════════
#  BODY SYSTEM MAPPING
# ═══════════════════════════════════════════════════════════════════

BODY_SYSTEM_MAP: dict[str, str] = {
    "fever": "General / Systemic",
    "headache": "Neurological",
    "cough": "Respiratory",
    "cold": "Respiratory / ENT",
    "sore throat": "ENT",
    "body pain": "Musculoskeletal",
    "joint pain": "Musculoskeletal",
    "chest pain": "Cardiovascular / Respiratory",
    "stomach pain": "Gastrointestinal",
    "back pain": "Musculoskeletal",
    "nausea": "Gastrointestinal",
    "vomiting": "Gastrointestinal",
    "diarrhea": "Gastrointestinal",
    "constipation": "Gastrointestinal",
    "dizziness": "Neurological / ENT",
    "fatigue": "General / Systemic",
    "weakness": "General / Systemic",
    "breathlessness": "Respiratory / Cardiovascular",
    "palpitations": "Cardiovascular",
    "swelling": "General / Vascular",
    "rash": "Dermatological",
    "itching": "Dermatological",
    "burning sensation": "General / Dermatological",
    "insomnia": "Neurological / Psychiatric",
    "anxiety": "Psychiatric",
    "loss of appetite": "Gastrointestinal / General",
    "weight loss": "General / Endocrine",
    "excessive thirst": "Endocrine",
    "frequent urination": "Urological / Endocrine",
    "blurred vision": "Ophthalmological",
}


# ═══════════════════════════════════════════════════════════════════
#  DOSHA TAG MAPPING (Ayurvedic association)
# ═══════════════════════════════════════════════════════════════════

DOSHA_MAP: dict[str, DoshaType] = {
    "fever": DoshaType.PITTA,
    "headache": DoshaType.VATA_PITTA,
    "cough": DoshaType.KAPHA,
    "cold": DoshaType.KAPHA,
    "sore throat": DoshaType.KAPHA,
    "body pain": DoshaType.VATA,
    "joint pain": DoshaType.VATA,
    "chest pain": DoshaType.VATA_PITTA,
    "stomach pain": DoshaType.PITTA,
    "back pain": DoshaType.VATA,
    "nausea": DoshaType.PITTA,
    "vomiting": DoshaType.PITTA,
    "diarrhea": DoshaType.PITTA,
    "constipation": DoshaType.VATA,
    "dizziness": DoshaType.VATA,
    "fatigue": DoshaType.KAPHA,
    "weakness": DoshaType.VATA,
    "breathlessness": DoshaType.KAPHA,
    "palpitations": DoshaType.VATA,
    "swelling": DoshaType.KAPHA,
    "rash": DoshaType.PITTA,
    "itching": DoshaType.KAPHA,
    "burning sensation": DoshaType.PITTA,
    "insomnia": DoshaType.VATA,
    "anxiety": DoshaType.VATA,
    "loss of appetite": DoshaType.KAPHA,
    "weight loss": DoshaType.VATA,
    "excessive thirst": DoshaType.PITTA,
    "frequent urination": DoshaType.VATA_KAPHA,
    "blurred vision": DoshaType.PITTA,
}


# ═══════════════════════════════════════════════════════════════════
#  SEVERITY INFERENCE
# ═══════════════════════════════════════════════════════════════════

SEVERITY_KEYWORDS: dict[str, Severity] = {
    # Severe / critical indicators
    "severe": Severity.SEVERE,
    "extreme": Severity.SEVERE,
    "unbearable": Severity.SEVERE,
    "excruciating": Severity.SEVERE,
    "worst": Severity.SEVERE,
    "intense": Severity.SEVERE,
    "very bad": Severity.SEVERE,
    "bahut": Severity.SEVERE,        # Hindi: very
    "bahut zyada": Severity.SEVERE,  # Hindi: very much
    "critical": Severity.CRITICAL,
    "emergency": Severity.CRITICAL,
    # Mild indicators
    "mild": Severity.MILD,
    "slight": Severity.MILD,
    "little": Severity.MILD,
    "thoda": Severity.MILD,          # Hindi: a little
    "halka": Severity.MILD,          # Hindi: light/mild
    "minor": Severity.MILD,
    # Moderate is the default
    "moderate": Severity.MODERATE,
}


def _infer_severity(symptom_text: str, duration_days: int | None) -> Severity:
    """Infer severity from text cues and symptom duration."""
    text_lower = symptom_text.lower()

    # Check keyword-based severity
    for keyword, level in SEVERITY_KEYWORDS.items():
        if keyword in text_lower:
            return level

    # Duration-based escalation
    if duration_days is not None:
        if duration_days >= 14:
            return Severity.SEVERE
        elif duration_days >= 7:
            return Severity.MODERATE
        elif duration_days <= 1:
            return Severity.MILD

    return Severity.MODERATE


# ═══════════════════════════════════════════════════════════════════
#  MAIN NORMALIZATION FUNCTION
# ═══════════════════════════════════════════════════════════════════

def normalize_intake(intake: PatientIntake) -> tuple[list[SymptomObject], AgentTrace]:
    """
    Normalize raw patient intake into structured SymptomObjects.

    1. Detect medical terms from the symptom_text (any language/script)
    2. Map each term to ICD-10, SNOMED, body system, dosha tag
    3. Infer severity from text cues and duration
    4. Return structured symptom objects + agent trace

    Args:
        intake: The raw PatientIntake from the user.

    Returns:
        (symptom_objects, agent_trace)
    """
    started_at = datetime.utcnow()

    # Step 1: Detect medical terms from multilingual input
    detected_terms = detect_language_terms(intake.symptom_text)

    # Step 2: Also check for direct English terms in comorbidities
    # (these are conditions, not symptoms, but useful for context)
    for condition in intake.comorbidities:
        terms = detect_language_terms(condition)
        for t in terms:
            if t not in detected_terms:
                detected_terms.append(t)

    # Step 3: Build SymptomObject for each detected term
    symptom_objects: list[SymptomObject] = []
    severity = _infer_severity(intake.symptom_text, intake.duration_days)

    for term in detected_terms:
        # Skip comorbidity-only terms (they aren't acute symptoms)
        comorbidity_terms = {"diabetes", "hypertension", "asthma",
                            "arthritis", "thyroid disorder", "anemia"}
        if term in comorbidity_terms and term not in intake.symptom_text.lower():
            continue

        symptom_obj = SymptomObject(
            name=term,
            original_text=intake.symptom_text,
            icd_code=ICD10_MAP.get(term),
            snomed_code=SNOMED_MAP.get(term),
            severity=severity,
            body_system=BODY_SYSTEM_MAP.get(term, "General"),
            dosha_tag=DOSHA_MAP.get(term),
            duration_days=intake.duration_days,
        )
        symptom_objects.append(symptom_obj)

    # Step 4: If no terms detected, create a generic entry
    if not symptom_objects:
        symptom_objects.append(SymptomObject(
            name="unspecified_symptom",
            original_text=intake.symptom_text,
            icd_code="R68.89",  # Other general symptoms
            snomed_code=None,
            severity=severity,
            body_system="General",
            dosha_tag=None,
            duration_days=intake.duration_days,
        ))

    completed_at = datetime.utcnow()
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    trace = AgentTrace(
        agent_name=AgentName.NORMALIZATION,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        input_summary=f"symptom_text='{intake.symptom_text[:80]}', "
                      f"lang={intake.language_pref}",
        output_summary=f"Detected {len(symptom_objects)} symptom(s): "
                       f"{[s.name for s in symptom_objects]}",
    )

    return symptom_objects, trace
