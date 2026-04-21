"""
Doctor recommendation analysis helpers.

This module converts the full intake profile into an AI-driven treatment
direction and specialty recommendation. It uses a deterministic clinical
heuristic by default and can optionally blend in a Hugging Face zero-shot
classifier when the dependency is available.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Optional
from difflib import SequenceMatcher

from backend.config import settings
from backend.schemas.common import CareStep, Modality, RiskLevel, SymptomObject, Warning
from backend.schemas.intake import PatientIntake

try:
    from transformers import pipeline as hf_pipeline  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    hf_pipeline = None


MODALITY_LABELS = [
    Modality.ALLOPATHY.value,
    Modality.AYURVEDA.value,
    Modality.HOMEOPATHY.value,
    Modality.HOME_REMEDIAL.value,
]

DOCTOR_TYPE_BY_MODALITY = {
    Modality.ALLOPATHY: "Internal Medicine / General Physician",
    Modality.AYURVEDA: "BAMS Physician (Kayachikitsa / Panchakarma Specialist)",
    Modality.HOMEOPATHY: "BHMS Homeopathic Physician (Constitutional Care)",
    Modality.HOME_REMEDIAL: "Family Medicine / Lifestyle Medicine Physician",
}

SPECIALTY_KEYWORDS: dict[str, dict[str, float]] = {
    "cardiology": {
        "chest pain": 4.0,
        "palpitation": 3.0,
        "syncope": 3.5,
        "heart": 3.0,
        "cardiac": 4.0,
        "hypertension": 2.0,
        "blood pressure": 2.0,
        "bp": 1.5,
    },
    "neurology": {
        "seizure": 4.0,
        "focal weakness": 4.0,
        "speech": 3.0,
        "vision loss": 3.0,
        "stroke": 4.0,
        "migraine": 2.5,
        "headache": 2.0,
        "dizziness": 1.5,
        "vertigo": 1.5,
    },
    "pulmonology": {
        "breath": 4.0,
        "dyspnea": 4.0,
        "wheeze": 3.0,
        "asthma": 3.5,
        "copd": 3.5,
        "cough": 2.0,
        "respiratory": 3.0,
    },
    "gastroenterology": {
        "abdominal": 3.0,
        "abdomen": 3.0,
        "gastric": 3.0,
        "stomach": 3.0,
        "nausea": 2.5,
        "vomiting": 2.5,
        "diarrhea": 2.0,
        "constipation": 1.5,
    },
    "orthopedics": {
        "joint": 3.0,
        "back pain": 3.0,
        "arthritis": 4.0,
        "musculoskeletal": 3.0,
        "fracture": 4.0,
        "swelling": 1.5,
    },
    "endocrinology": {
        "diabetes": 4.0,
        "thyroid": 4.0,
        "sugar": 3.0,
        "endocrine": 3.0,
        "weight loss": 1.5,
        "fatigue": 1.5,
    },
    "obgyn": {
        "pregnancy": 4.0,
        "menstrual": 3.0,
        "gyne": 3.5,
        "obstetric": 3.5,
        "pelvic": 2.0,
    },
    "general": {
        "fever": 2.5,
        "infection": 2.5,
        "viral": 1.5,
        "chills": 1.5,
        "weakness": 1.0,
        "fatigue": 1.0,
    },
}

MODALITY_KEYWORDS: dict[Modality, dict[str, float]] = {
    Modality.ALLOPATHY: {
        "chest pain": 4.0,
        "breath": 4.0,
        "dyspnea": 4.0,
        "palpitation": 3.5,
        "syncope": 3.5,
        "fever": 2.5,
        "infection": 2.5,
        "diabetes": 2.5,
        "thyroid": 2.5,
        "hypertension": 2.5,
        "medication": 1.5,
        "allergy": 1.5,
        "high-risk": 2.0,
        "red flag": 2.0,
    },
    Modality.AYURVEDA: {
        "joint pain": 3.0,
        "back pain": 3.0,
        "acidity": 3.0,
        "constipation": 3.0,
        "fatigue": 2.5,
        "insomnia": 2.5,
        "stress": 2.0,
        "lifestyle": 1.5,
        "digestive": 1.5,
        "vegetarian": 1.0,
    },
    Modality.HOMEOPATHY: {
        "cold": 2.5,
        "cough": 2.5,
        "allergy": 2.0,
        "itching": 2.0,
        "rash": 2.0,
        "anxiety": 2.0,
        "insomnia": 2.0,
        "mild": 1.5,
    },
    Modality.HOME_REMEDIAL: {
        "cold": 3.0,
        "cough": 2.5,
        "fever": 2.0,
        "headache": 1.5,
        "hydration": 1.5,
        "rest": 1.5,
        "sleep": 1.5,
        "self-care": 2.0,
        "home": 1.0,
    },
}


@dataclass(slots=True)
class DoctorInference:
    """Normalized doctor recommendation generated from the intake profile."""

    ranked_modalities: list[str]
    modality_scores: dict[str, float]
    primary_specialty: str
    primary_domain: str
    confidence: float
    rationale: list[str]
    model_used: str


def _clean_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _join_terms(*parts: object) -> str:
    collected: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, str):
            collected.append(part)
        elif isinstance(part, (list, tuple, set)):
            collected.extend(str(item) for item in part if item)
        else:
            collected.append(str(part))
    return _clean_text(" ".join(collected))


def _keyword_score(text: str, keyword_weights: dict[str, float]) -> tuple[float, list[str]]:
    """
    Score text against weighted keywords using exact + character-level fuzzy matching.

    The fuzzy path makes each character sequence in user input meaningful,
    improving robustness to typos and transliteration drift.
    """
    score = 0.0
    matches: list[str] = []
    text_tokens = [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]

    def ngram_tokens(tokens: list[str], n: int) -> list[str]:
        if n <= 1:
            return tokens
        return [" ".join(tokens[i : i + n]) for i in range(max(0, len(tokens) - n + 1))]

    for keyword, weight in keyword_weights.items():
        keyword_l = keyword.lower()
        if keyword_l in text:
            score += weight
            matches.append(keyword)
            continue

        key_parts = [p for p in keyword_l.split() if p]
        if not text_tokens or not key_parts:
            continue

        # Compare keyword to text windows with same token length.
        windows = ngram_tokens(text_tokens, len(key_parts))
        best_ratio = 0.0
        for window in windows:
            ratio = SequenceMatcher(None, window, keyword_l).ratio()
            if ratio > best_ratio:
                best_ratio = ratio

        if best_ratio >= 0.86:
            # High-confidence fuzzy hit.
            score += weight * 0.85
            matches.append(f"{keyword}~")
        elif best_ratio >= 0.78:
            # Partial fuzzy hit; lower contribution to avoid false positives.
            score += weight * 0.45
            matches.append(f"{keyword}≈")

    return score, matches


def _extract_profile_text(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_factors: Optional[list[str]] = None,
    care_steps: Optional[list[CareStep]] = None,
    warnings: Optional[list[Warning]] = None,
) -> str:
    symptom_text = " ".join(
        [
            intake.symptom_text,
            *[symptom.name for symptom in symptom_objects],
            *[symptom.original_text for symptom in symptom_objects],
        ]
    )
    history_text = _join_terms(
        intake.comorbidities,
        intake.medications,
        intake.allergies,
        intake.family_history,
        intake.lifestyle_notes,
    )
    care_text = _join_terms(
        risk_factors,
        [step.specialist_type for step in care_steps or []],
        [step.reason for step in care_steps or []],
        [warning.message for warning in warnings or []],
        [warning.resolution for warning in warnings or []],
    )
    demographic_text = f"age {intake.age} sex {intake.sex} duration {intake.duration_days or 0} days"
    return _join_terms(symptom_text, history_text, care_text, demographic_text)


@lru_cache(maxsize=1)
def _load_classifier():
    if hf_pipeline is None or not settings.ENABLE_HF_DOCTOR_RECOMMENDER:
        return None

    try:
        return hf_pipeline("zero-shot-classification", model=settings.HF_DOCTOR_RECOMMENDER_MODEL)
    except Exception:
        return None


def _apply_hf_boost(text: str, modality_scores: dict[str, float], rationale: list[str]) -> str:
    classifier = _load_classifier()
    if classifier is None:
        rationale.append("Hugging Face classifier unavailable; using clinical heuristic analysis.")
        return "clinical-heuristic"

    try:
        result = classifier(
            text[:4000],
            candidate_labels=MODALITY_LABELS,
            multi_label=False,
        )
    except Exception:
        rationale.append("Hugging Face classifier could not score the profile; heuristic fallback used.")
        return "clinical-heuristic"

    hf_scores = {label: 0.0 for label in MODALITY_LABELS}
    for label, score in zip(result["labels"], result["scores"]):
        hf_scores[str(label)] = float(score)

    rationale.append(f"Hugging Face modality signal: {hf_scores}")
    for modality in MODALITY_LABELS:
        modality_scores[modality] = round(
            min(1.0, modality_scores.get(modality, 0.0) * 0.65 + hf_scores.get(modality, 0.0) * 0.35),
            3,
        )

    return settings.HF_DOCTOR_RECOMMENDER_MODEL


def infer_modality_scores(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
    risk_factors: Optional[list[str]] = None,
    care_steps: Optional[list[CareStep]] = None,
    warnings: Optional[list[Warning]] = None,
) -> tuple[dict[str, float], list[str], str, str]:
    """Score each modality from the full profile and return the ranking."""
    analysis_text = _extract_profile_text(intake, symptom_objects, risk_factors, care_steps, warnings)
    rationale: list[str] = [
        "Analyzed age, sex, symptom text, symptom objects, comorbidities, medications, allergies, family history, duration, and lifestyle notes.",
    ]

    modality_scores: dict[str, float] = {modality.value: 0.12 for modality in Modality}

    for modality, keyword_map in MODALITY_KEYWORDS.items():
        score, matches = _keyword_score(analysis_text, keyword_map)
        if matches:
            modality_scores[modality.value] += min(0.55, score / 12.0)
            rationale.append(f"{modality.value} matched signals: {', '.join(matches[:6])}")

    symptom_blob = _join_terms([symptom.name for symptom in symptom_objects], [symptom.original_text for symptom in symptom_objects])
    comorbidity_blob = _join_terms(intake.comorbidities)
    medication_blob = _join_terms(intake.medications)
    allergy_blob = _join_terms(intake.allergies)
    lifestyle_blob = _join_terms(intake.lifestyle_notes)

    if any(token in symptom_blob for token in ["fever", "chest pain", "breath", "dyspnea", "syncope", "seizure", "stroke"]):
        modality_scores[Modality.ALLOPATHY.value] += 0.2
        rationale.append("Acute/red-flag symptom pattern strongly favored allopathy.")

    if any(token in symptom_blob for token in ["joint pain", "back pain", "constipation", "acidity", "fatigue", "insomnia", "stress"]):
        modality_scores[Modality.AYURVEDA.value] += 0.12
        rationale.append("Chronic symptom pattern supported Ayurvedic evaluation.")

    if any(token in symptom_blob for token in ["cold", "cough", "rash", "itching", "anxiety", "insomnia"]):
        modality_scores[Modality.HOMEOPATHY.value] += 0.08
        rationale.append("Constitutional / recurrent symptom pattern supported homeopathic evaluation.")

    if any(token in symptom_blob for token in ["cold", "cough", "fever", "headache", "fatigue"]):
        modality_scores[Modality.HOME_REMEDIAL.value] += 0.08
        rationale.append("Low-acuity symptom pattern supported home-remedial guidance.")

    if intake.age < 18:
        modality_scores[Modality.ALLOPATHY.value] += 0.08
        rationale.append("Pediatric age profile shifted preference toward specialist clinical review.")
    elif intake.age >= 65:
        modality_scores[Modality.ALLOPATHY.value] += 0.08
        rationale.append("Older age profile increased the need for conservative clinical oversight.")

    if intake.sex.upper() == "F" and any(token in symptom_blob for token in ["pregnancy", "menstrual", "pelvic", "obstetric", "gyne"]):
        modality_scores[Modality.ALLOPATHY.value] += 0.12
        rationale.append("Female reproductive / pregnancy cues favored gynecology-informed review.")

    if intake.duration_days is not None:
        if intake.duration_days >= 14:
            modality_scores[Modality.AYURVEDA.value] += 0.06
            modality_scores[Modality.HOMEOPATHY.value] += 0.04
            rationale.append("Longer duration suggested chronic-care modalities.")
        elif intake.duration_days <= 3:
            modality_scores[Modality.ALLOPATHY.value] += 0.05
            modality_scores[Modality.HOME_REMEDIAL.value] += 0.03
            rationale.append("Short-duration presentation favored acute care and self-care support.")

    if comorbidity_blob or medication_blob or allergy_blob:
        modality_scores[Modality.ALLOPATHY.value] += 0.08
        rationale.append("Existing conditions, medications, or allergies increased the need for physician-led review.")

    if lifestyle_blob:
        if any(token in lifestyle_blob for token in ["vegetarian", "stress", "sleep", "exercise", "diet"]):
            modality_scores[Modality.AYURVEDA.value] += 0.04
            modality_scores[Modality.HOME_REMEDIAL.value] += 0.03
            rationale.append("Lifestyle context supported holistic and self-care advice.")

    if risk_level == RiskLevel.EMERGENT:
        modality_scores[Modality.ALLOPATHY.value] += 0.35
        rationale.append("Emergent risk forced an allopathy-first recommendation.")
    elif risk_level == RiskLevel.URGENT:
        modality_scores[Modality.ALLOPATHY.value] += 0.22
        rationale.append("Urgent risk prioritized conventional physician review.")
    elif risk_level == RiskLevel.SELF_CARE:
        modality_scores[Modality.HOME_REMEDIAL.value] += 0.12
        modality_scores[Modality.HOMEOPATHY.value] += 0.04
        rationale.append("Self-care risk allowed more conservative home-based guidance.")

    warning_blob = _join_terms([warning.message for warning in warnings or []], [warning.resolution for warning in warnings or []])
    if warning_blob:
        if any(token in warning_blob for token in ["high", "contraindication", "drug", "interaction", "emergency"]):
            modality_scores[Modality.ALLOPATHY.value] += 0.12
            rationale.append("Safety warnings increased the need for physician-led management.")

    care_blob = _join_terms([step.specialist_type for step in care_steps or []], [step.reason for step in care_steps or []])
    if care_blob:
        for modality, keyword_map in MODALITY_KEYWORDS.items():
            score, matches = _keyword_score(care_blob, keyword_map)
            if matches:
                modality_scores[modality.value] += min(0.15, score / 30.0)

    model_used = _apply_hf_boost(analysis_text, modality_scores, rationale)

    for modality in modality_scores:
        modality_scores[modality] = round(max(0.05, min(0.99, modality_scores[modality])), 3)

    ranked_modalities = [
        modality for modality, _ in sorted(modality_scores.items(), key=lambda item: item[1], reverse=True)
    ]

    return modality_scores, ranked_modalities, "; ".join(rationale), model_used


def infer_doctor_inference(
    session_id: str,
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
    risk_factors: list[str],
    care_steps: list[CareStep],
    warnings: list[Warning],
) -> DoctorInference:
    """Return a normalized AI doctor recommendation for the full intake."""
    modality_scores, ranked_modalities, rationale_text, model_used = infer_modality_scores(
        intake=intake,
        symptom_objects=symptom_objects,
        risk_level=risk_level,
        risk_factors=risk_factors,
        care_steps=care_steps,
        warnings=warnings,
    )

    best_modality = Modality(ranked_modalities[0])
    top_score = modality_scores[best_modality.value]
    second_score = modality_scores[ranked_modalities[1]] if len(ranked_modalities) > 1 else 0.0
    confidence = round(max(0.2, min(0.99, top_score - (second_score * 0.35))), 3)

    primary_domain = "general"
    primary_specialty = DOCTOR_TYPE_BY_MODALITY[best_modality]

    specialty_scores = {domain: 0.0 for domain in SPECIALTY_KEYWORDS}
    profile_text = _extract_profile_text(intake, symptom_objects, risk_factors, care_steps, warnings)
    for domain, keyword_map in SPECIALTY_KEYWORDS.items():
        score, matches = _keyword_score(profile_text, keyword_map)
        specialty_scores[domain] += score
        if matches:
            rationale_text += f"; {domain} signals: {', '.join(matches[:4])}"

    if intake.age < 18:
        specialty_scores["general"] += 1.5
        primary_specialty = "Pediatrician / Family Physician"
        primary_domain = "pediatrics"
    elif intake.age >= 65:
        specialty_scores["general"] += 1.0
        primary_specialty = "Geriatric Medicine / Internal Medicine Specialist"
        primary_domain = "geriatrics"

    sorted_specialties = sorted(specialty_scores.items(), key=lambda item: item[1], reverse=True)
    if sorted_specialties and sorted_specialties[0][1] > 0:
        primary_domain = sorted_specialties[0][0]
        specialty_map = {
            "cardiology": "Cardiologist",
            "neurology": "Neurologist",
            "pulmonology": "Pulmonologist",
            "gastroenterology": "Gastroenterologist",
            "orthopedics": "Orthopedic / Rheumatology Specialist",
            "endocrinology": "Endocrinologist",
            "obgyn": "Obstetrician-Gynecologist",
            "general": "Internal Medicine / General Physician",
        }
        primary_specialty = specialty_map.get(primary_domain, primary_specialty)

    systemic_signal = any(
        token in profile_text
        for token in ["fever", "infection", "chills", "weakness", "red flag", "emergency"]
    )
    if intake.age < 18:
        primary_domain = "pediatrics"
        primary_specialty = "Pediatrician / Family Physician"
    elif intake.age >= 65:
        primary_domain = "geriatrics"
        primary_specialty = "Geriatric Medicine / Internal Medicine Specialist"
    elif risk_level == RiskLevel.EMERGENT:
        primary_domain = "emergency"
        primary_specialty = "Emergency Medicine Physician"
    elif risk_level == RiskLevel.URGENT and primary_domain not in {"cardiology", "neurology", "pulmonology", "obgyn"}:
        primary_domain = "general"
        primary_specialty = "Internal Medicine / General Physician"
    elif systemic_signal and primary_domain not in {"cardiology", "neurology", "pulmonology", "obgyn"}:
        primary_domain = "general"
        primary_specialty = "Internal Medicine / General Physician"

    return DoctorInference(
        ranked_modalities=ranked_modalities,
        modality_scores=modality_scores,
        primary_specialty=primary_specialty,
        primary_domain=primary_domain,
        confidence=confidence,
        rationale=rationale_text.split("; "),
        model_used=model_used,
    )
