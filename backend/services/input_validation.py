"""
Input validation service.

This module blocks invalid or nonsensical input before pipeline execution.
It combines strict character/word-level checks with a Hugging Face zero-shot
classifier so invalid user text does not produce an AI report.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re

from backend.config import settings
from backend.schemas.intake import PatientIntake

try:
    from transformers import pipeline as hf_pipeline  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    hf_pipeline = None


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    reasons: list[str]
    confidence: float
    model_used: str


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def _alphabetic_ratio(text: str) -> float:
    cleaned = [ch for ch in text if not ch.isspace()]
    if not cleaned:
        return 0.0
    alpha_count = sum(1 for ch in cleaned if ch.isalpha())
    return alpha_count / len(cleaned)


def _has_long_repeated_char_sequence(text: str, threshold: int = 5) -> bool:
    lowered = text.lower()
    count = 1
    for idx in range(1, len(lowered)):
        if lowered[idx] == lowered[idx - 1]:
            count += 1
            if count >= threshold:
                return True
        else:
            count = 1
    return False


def _is_placeholder_text(text: str) -> bool:
    lowered = text.lower().strip()
    placeholders = {
        "test",
        "hello",
        "hi",
        "asdf",
        "qwerty",
        "na",
        "n/a",
        "none",
        "abc",
        "xyz",
        "12345",
    }
    return lowered in placeholders


def _token_noise_ratio(text: str) -> float:
    tokens = _words(text)
    if not tokens:
        return 1.0
    valid_tokens = 0
    for token in tokens:
        has_alpha = any(ch.isalpha() for ch in token)
        long_enough = len(token) >= 2
        if has_alpha and long_enough:
            valid_tokens += 1
    return 1.0 - (valid_tokens / len(tokens))


def _validate_text_field(name: str, text: str, min_words: int) -> list[str]:
    reasons: list[str] = []
    t = (text or "").strip()
    if not t:
        reasons.append(f"{name} is empty")
        return reasons

    words = _words(t)
    if len(words) < min_words:
        reasons.append(f"{name} must contain at least {min_words} word(s)")

    if _is_placeholder_text(t):
        reasons.append(f"{name} appears to be placeholder text")

    alpha_ratio = _alphabetic_ratio(t)
    if alpha_ratio < 0.45:
        reasons.append(f"{name} has too many non-letter characters")

    if _has_long_repeated_char_sequence(t):
        reasons.append(f"{name} contains repeated character noise")

    if _token_noise_ratio(t) > 0.55:
        reasons.append(f"{name} contains too many low-quality tokens")

    return reasons


@lru_cache(maxsize=1)
def _get_hf_validator():
    if hf_pipeline is None or not settings.ENABLE_HF_INPUT_VALIDATION:
        return None
    try:
        return hf_pipeline("zero-shot-classification", model=settings.HF_INPUT_VALIDATION_MODEL)
    except Exception:
        return None


def _hf_input_validity_score(text: str) -> tuple[float, str]:
    classifier = _get_hf_validator()
    if classifier is None:
        return 0.0, "rule-only"

    labels = [
        "valid medical symptom description",
        "invalid or nonsensical input",
        "unrelated greeting or placeholder text",
    ]
    result = classifier(text[:2500], candidate_labels=labels, multi_label=False)
    scores = {str(label): float(score) for label, score in zip(result["labels"], result["scores"])}
    invalid_score = max(
        scores.get("invalid or nonsensical input", 0.0),
        scores.get("unrelated greeting or placeholder text", 0.0),
    )
    return invalid_score, settings.HF_INPUT_VALIDATION_MODEL


def validate_intake_payload(intake: PatientIntake) -> ValidationResult:
    reasons: list[str] = []

    # Allow concise symptoms like "fever" or "migraine" while still
    # enforcing placeholder/noise/HF checks.
    reasons.extend(_validate_text_field("symptom_text", intake.symptom_text, min_words=1))

    for idx, item in enumerate(intake.comorbidities):
        reasons.extend(_validate_text_field(f"comorbidities[{idx}]", item, min_words=1))

    for idx, item in enumerate(intake.medications):
        reasons.extend(_validate_text_field(f"medications[{idx}]", item, min_words=1))

    for idx, item in enumerate(intake.allergies):
        reasons.extend(_validate_text_field(f"allergies[{idx}]", item, min_words=1))

    if intake.lifestyle_notes:
        reasons.extend(_validate_text_field("lifestyle_notes", intake.lifestyle_notes, min_words=1))

    invalid_score, model_used = _hf_input_validity_score(intake.symptom_text)
    if invalid_score >= settings.HF_INPUT_INVALID_THRESHOLD:
        reasons.append(
            f"symptom_text failed Hugging Face validity check (invalid_score={invalid_score:.2f})"
        )

    deduped_reasons: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        if reason not in seen:
            deduped_reasons.append(reason)
            seen.add(reason)

    return ValidationResult(
        is_valid=len(deduped_reasons) == 0,
        reasons=deduped_reasons,
        confidence=round(max(0.0, min(1.0, 1.0 - invalid_score)), 3),
        model_used=model_used,
    )
