"""
Triage Agent — performs risk-stratified triage using a hybrid
rule-based + scoring model approach.

Pipeline role:  SECOND agent (after Normalization).
Input:          list[SymptomObject], PatientIntake
Output:         risk_level, confidence, justification

Classifies patient risk as: emergent | urgent | routine | self-care
Uses emergency keyword detection, symptom severity scoring, age/comorbidity
weighting, and duration analysis.
"""
from __future__ import annotations

from datetime import datetime

from backend.schemas.common import (
    RiskLevel,
    Severity,
    SymptomObject,
    AgentTrace,
    AgentName,
    AgentStatus,
)
from backend.schemas.intake import PatientIntake
from backend.knowledge.safety_rules import (
    check_emergency_keywords,
    check_emergency_combinations,
)


# ═══════════════════════════════════════════════════════════════════
#  EMERGENCY PATTERN DETECTION (Rule-based — fast path)
# ═══════════════════════════════════════════════════════════════════

# Symptoms that are emergent regardless of scoring
HARD_EMERGENT_SYMPTOMS: set[str] = {
    "chest pain", "breathlessness", "palpitations",
}

# Age thresholds for escalation
AGE_HIGH_RISK_THRESHOLD: int = 60
AGE_PEDIATRIC_THRESHOLD: int = 5


# ═══════════════════════════════════════════════════════════════════
#  SCORING WEIGHTS (simulated GBM-like feature importance)
# ═══════════════════════════════════════════════════════════════════

# Symptom severity score contribution
SEVERITY_SCORES: dict[Severity, float] = {
    Severity.CRITICAL: 40.0,
    Severity.SEVERE: 25.0,
    Severity.MODERATE: 12.0,
    Severity.MILD: 5.0,
}

# Body system risk weighting — some systems are inherently more urgent
SYSTEM_RISK_WEIGHT: dict[str, float] = {
    "Cardiovascular": 15.0,
    "Cardiovascular / Respiratory": 15.0,
    "Respiratory / Cardiovascular": 14.0,
    "Neurological": 12.0,
    "Respiratory": 10.0,
    "Gastrointestinal": 6.0,
    "Endocrine": 5.0,
    "Musculoskeletal": 4.0,
    "Dermatological": 3.0,
    "ENT": 3.0,
    "Psychiatric": 7.0,
    "General / Systemic": 5.0,
    "Urological / Endocrine": 5.0,
    "General / Vascular": 5.0,
    "Ophthalmological": 4.0,
}

# Comorbidity risk multipliers
COMORBIDITY_RISKS: dict[str, float] = {
    "hypertension": 8.0,
    "diabetes": 7.0,
    "heart disease": 12.0,
    "cardiac": 12.0,
    "asthma": 6.0,
    "copd": 8.0,
    "kidney disease": 7.0,
    "liver disease": 6.0,
    "cancer": 10.0,
    "hiv": 8.0,
    "pregnancy": 5.0,
    "obesity": 4.0,
    "thyroid disorder": 3.0,
    "anemia": 4.0,
}

# Duration score — longer duration without treatment increases risk
DURATION_SCORES: dict[str, float] = {
    "acute": 3.0,       # 0-2 days
    "subacute": 6.0,    # 3-7 days
    "prolonged": 10.0,  # 8-14 days
    "chronic": 8.0,     # 15+ days (slightly lower as likely not emergent)
}

# Risk level thresholds (total score → risk level)
RISK_THRESHOLDS = {
    "emergent": 60.0,
    "urgent": 35.0,
    "routine": 15.0,
    # Below 15 → self-care
}


# ═══════════════════════════════════════════════════════════════════
#  TRIAGE SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════

def _compute_symptom_score(symptoms: list[SymptomObject]) -> tuple[float, list[str]]:
    """Score symptoms based on severity and body system."""
    total = 0.0
    factors: list[str] = []

    for sym in symptoms:
        # Severity contribution
        sev_score = SEVERITY_SCORES.get(sym.severity, 5.0)
        total += sev_score
        if sym.severity in (Severity.SEVERE, Severity.CRITICAL):
            factors.append(
                f"Severe symptom: {sym.name} (severity={sym.severity.value}, "
                f"+{sev_score} pts)"
            )

        # Body system risk
        sys_score = 0.0
        if sym.body_system:
            sys_score = SYSTEM_RISK_WEIGHT.get(sym.body_system, 3.0)
            total += sys_score

        # Emergency symptom hard flag
        if sym.name in HARD_EMERGENT_SYMPTOMS:
            total += 20.0
            factors.append(
                f"Emergency symptom detected: {sym.name} (+20 pts)"
            )

    return total, factors


def _compute_age_score(age: int) -> tuple[float, list[str]]:
    """Age-based risk adjustment."""
    score = 0.0
    factors: list[str] = []

    if age >= AGE_HIGH_RISK_THRESHOLD:
        score = 10.0 + (age - AGE_HIGH_RISK_THRESHOLD) * 0.3
        factors.append(f"Elderly patient (age {age}, +{score:.1f} pts)")
    elif age <= AGE_PEDIATRIC_THRESHOLD:
        score = 8.0
        factors.append(f"Pediatric patient (age {age}, +{score:.1f} pts)")

    return score, factors


def _compute_comorbidity_score(comorbidities: list[str]) -> tuple[float, list[str]]:
    """Comorbidity burden scoring."""
    score = 0.0
    factors: list[str] = []

    for condition in comorbidities:
        cond_lower = condition.lower()
        for key, risk_val in COMORBIDITY_RISKS.items():
            if key in cond_lower:
                score += risk_val
                factors.append(
                    f"Comorbidity: {condition} (+{risk_val} pts)"
                )
                break

    # Multiple comorbidity penalty
    if len(comorbidities) >= 3:
        bonus = 5.0
        score += bonus
        factors.append(f"Multiple comorbidities ({len(comorbidities)}, +{bonus} pts)")

    return score, factors


def _compute_duration_score(duration_days: int | None) -> tuple[float, list[str]]:
    """Duration-based risk adjustment."""
    if duration_days is None:
        return 2.0, ["Duration unknown (+2 pts default)"]

    if duration_days <= 2:
        cat = "acute"
    elif duration_days <= 7:
        cat = "subacute"
    elif duration_days <= 14:
        cat = "prolonged"
    else:
        cat = "chronic"

    score = DURATION_SCORES[cat]
    return score, [f"Duration: {duration_days} days ({cat}, +{score} pts)"]


def _score_to_risk_level(score: float) -> RiskLevel:
    """Convert numeric score to risk level."""
    if score >= RISK_THRESHOLDS["emergent"]:
        return RiskLevel.EMERGENT
    elif score >= RISK_THRESHOLDS["urgent"]:
        return RiskLevel.URGENT
    elif score >= RISK_THRESHOLDS["routine"]:
        return RiskLevel.ROUTINE
    else:
        return RiskLevel.SELF_CARE


def _compute_confidence(
    score: float, risk_level: RiskLevel, num_symptoms: int
) -> float:
    """
    Compute confidence score for the triage decision.
    Higher scores relative to threshold boundaries = higher confidence.
    More symptoms = more data = higher confidence.
    """
    thresholds = {
        RiskLevel.EMERGENT: (RISK_THRESHOLDS["emergent"], 100.0),
        RiskLevel.URGENT: (RISK_THRESHOLDS["urgent"], RISK_THRESHOLDS["emergent"]),
        RiskLevel.ROUTINE: (RISK_THRESHOLDS["routine"], RISK_THRESHOLDS["urgent"]),
        RiskLevel.SELF_CARE: (0.0, RISK_THRESHOLDS["routine"]),
    }

    low, high = thresholds[risk_level]
    range_size = high - low
    if range_size <= 0:
        position = 1.0
    else:
        position = (score - low) / range_size

    # Base confidence from position within range
    base_conf = 0.5 + (position * 0.3)

    # Symptom count bonus (more data = more confident)
    data_bonus = min(0.15, num_symptoms * 0.03)

    confidence = min(0.98, base_conf + data_bonus)
    return round(confidence, 2)


# ═══════════════════════════════════════════════════════════════════
#  MAIN TRIAGE FUNCTION
# ═══════════════════════════════════════════════════════════════════

def run_triage(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
) -> tuple[RiskLevel, float, str, list[str], AgentTrace]:
    """
    Perform risk-stratified triage.

    Args:
        intake: Original patient intake.
        symptom_objects: Normalized symptoms from the Normalization Agent.

    Returns:
        (risk_level, confidence, justification, risk_factors, agent_trace)
    """
    started_at = datetime.utcnow()
    all_factors: list[str] = []
    total_score: float = 0.0

    # ── 1. FAST PATH: Emergency keyword check ──────────────
    emergency_warnings = check_emergency_keywords(intake.symptom_text)
    emergency_combo_warnings = check_emergency_combinations(
        [s.name for s in symptom_objects], intake.age
    )

    if emergency_warnings or emergency_combo_warnings:
        risk_level = RiskLevel.EMERGENT
        confidence = 0.95
        emergency_reasons = []
        for w in emergency_warnings + emergency_combo_warnings:
            emergency_reasons.append(w.message)
            all_factors.append(f"EMERGENCY RULE: {w.message}")

        justification = (
            f"EMERGENT — Immediate medical attention required. "
            f"{' '.join(emergency_reasons)} "
            f"Patient (age {intake.age}) "
            f"should proceed to the nearest emergency department."
        )

        completed_at = datetime.utcnow()
        trace = AgentTrace(
            agent_name=AgentName.TRIAGE,
            status=AgentStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            input_summary=f"{len(symptom_objects)} symptoms, age={intake.age}",
            output_summary=f"risk={risk_level.value}, confidence={confidence}",
        )
        return risk_level, confidence, justification, all_factors, trace

    # ── 2. SCORING PATH: Compute composite risk score ──────
    # Symptom score
    sym_score, sym_factors = _compute_symptom_score(symptom_objects)
    total_score += sym_score
    all_factors.extend(sym_factors)

    # Age score
    age_score, age_factors = _compute_age_score(intake.age)
    total_score += age_score
    all_factors.extend(age_factors)

    # Comorbidity score
    comorbidity_score, comorbidity_factors = _compute_comorbidity_score(
        intake.comorbidities
    )
    total_score += comorbidity_score
    all_factors.extend(comorbidity_factors)

    # Duration score
    duration_score, duration_factors = _compute_duration_score(intake.duration_days)
    total_score += duration_score
    all_factors.extend(duration_factors)

    # Medication count adjustment (polypharmacy risk)
    if len(intake.medications) >= 4:
        poly_score = 3.0
        total_score += poly_score
        all_factors.append(
            f"Polypharmacy risk ({len(intake.medications)} medications, "
            f"+{poly_score} pts)"
        )

    # ── 3. DETERMINE RISK LEVEL ────────────────────────────
    risk_level = _score_to_risk_level(total_score)
    confidence = _compute_confidence(
        total_score, risk_level, len(symptom_objects)
    )

    # ── 4. BUILD JUSTIFICATION ─────────────────────────────
    symptom_names = [s.name for s in symptom_objects]
    justification = (
        f"{risk_level.value.upper()} — "
        f"Risk score: {total_score:.1f}/100. "
        f"Symptoms: {', '.join(symptom_names)}. "
        f"Patient: age {intake.age}, sex {intake.sex}"
    )

    if intake.comorbidities:
        justification += f", comorbidities: {', '.join(intake.comorbidities)}"
    if intake.duration_days:
        justification += f", duration: {intake.duration_days} days"

    justification += ". "

    # Add level-specific guidance
    guidance_map = {
        RiskLevel.EMERGENT: "Immediate medical evaluation recommended.",
        RiskLevel.URGENT: (
            "Medical consultation recommended within 24 hours. "
            "Monitor symptoms closely."
        ),
        RiskLevel.ROUTINE: (
            "Schedule a routine consultation at your convenience. "
            "Continue symptom monitoring."
        ),
        RiskLevel.SELF_CARE: (
            "Symptoms suggest self-care may be sufficient. "
            "Rest, hydration, and over-the-counter remedies as appropriate. "
            "Seek medical attention if symptoms worsen."
        ),
    }
    justification += guidance_map.get(risk_level, "")

    # ── 5. TRACE ───────────────────────────────────────────
    completed_at = datetime.utcnow()
    trace = AgentTrace(
        agent_name=AgentName.TRIAGE,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=f"{len(symptom_objects)} symptoms, age={intake.age}, "
                      f"comorbidities={len(intake.comorbidities)}",
        output_summary=f"risk={risk_level.value}, confidence={confidence}, "
                       f"score={total_score:.1f}",
    )

    return risk_level, confidence, justification, all_factors, trace
