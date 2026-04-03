"""
Safety & Conflict Agent — checks for dangerous interactions between
modalities, herb-drug conflicts, and contraindications.

Pipeline role:  Runs AFTER all specialist agents, BEFORE synthesizer.
Input:          PatientIntake, all PlanSegments, symptom_objects
Output:         list[Warning], resolution notes

This is the CRITICAL safety gate — it can:
  - Add warnings to the final plan
  - Flag dangerous herb-drug combinations
  - Detect cross-modality conflicts
  - Recommend resolution actions
  - Override care path if safety concern is severe
"""
from __future__ import annotations

from datetime import datetime

from backend.schemas.common import (
    Modality,
    RiskLevel,
    SymptomObject,
    PlanSegment,
    Warning,
    AgentTrace,
    AgentName,
    AgentStatus,
)
from backend.schemas.intake import PatientIntake
from backend.knowledge.safety_rules import (
    check_emergency_keywords,
    check_herb_drug_interactions,
    check_ayurvedic_contraindications,
    check_cross_modality_conflicts,
    run_all_safety_checks,
)


# ═══════════════════════════════════════════════════════════════════
#  EXTRACT HERBS AND DRUGS FROM PLAN SEGMENTS
# ═══════════════════════════════════════════════════════════════════

def _extract_medications_from_plans(
    plan_segments: list[PlanSegment],
) -> tuple[list[str], dict[str, str]]:
    """
    Extract all medication/herb names from plan segments.
    Returns (all_herb_names, plan_text_by_modality)
    """
    herbs: list[str] = []
    plan_text_by_modality: dict[str, str] = {}

    for segment in plan_segments:
        modality_key = segment.modality.value

        # Collect all text from the segment for keyword scanning
        all_text_parts = []
        all_text_parts.extend(segment.medications)
        all_text_parts.extend(segment.recommendations)
        all_text_parts.extend(segment.lifestyle)

        combined_text = " ".join(all_text_parts)
        plan_text_by_modality[modality_key] = combined_text

        # Extract herbs/medications from the medication list
        for med in segment.medications:
            herbs.append(med)

    return herbs, plan_text_by_modality


# ═══════════════════════════════════════════════════════════════════
#  DOSAGE SAFETY CHECKS
# ═══════════════════════════════════════════════════════════════════

def _check_polypharmacy(
    patient_medications: list[str],
    new_medications: list[str],
) -> list[Warning]:
    """
    Check for polypharmacy risk when adding new medications to
    existing prescriptions.
    """
    warnings: list[Warning] = []
    total_meds = len(patient_medications) + len(new_medications)

    if total_meds >= 8:
        warnings.append(Warning(
            rule_id="R_POLY_01",
            severity="high",
            message=(
                f"High polypharmacy risk: Patient is already on "
                f"{len(patient_medications)} medication(s), and the care plan "
                f"adds {len(new_medications)} more (total: {total_meds}). "
                f"This significantly increases the risk of adverse drug "
                f"interactions and side effects."
            ),
            affected_modalities=[Modality.ALLOPATHY, Modality.AYURVEDA],
            resolution=(
                "Review all medications with a clinical pharmacologist. "
                "Prioritize essential medications and consider reducing "
                "complementary formulations. Stagger introduction of new "
                "medications with 48-hour intervals."
            ),
        ))
    elif total_meds >= 5:
        warnings.append(Warning(
            rule_id="R_POLY_02",
            severity="medium",
            message=(
                f"Moderate polypharmacy: Total medication count is {total_meds} "
                f"({len(patient_medications)} existing + {len(new_medications)} new). "
                f"Monitor for cumulative side effects."
            ),
            affected_modalities=[Modality.ALLOPATHY, Modality.AYURVEDA],
            resolution=(
                "Pharmacist review recommended. Document all medications "
                "across systems. Watch for additive sedation, GI, or "
                "hepatic effects."
            ),
        ))

    return warnings


def _check_age_specific_safety(
    age: int,
    plan_segments: list[PlanSegment],
) -> list[Warning]:
    """
    Age-specific medication safety checks.
    """
    warnings: list[Warning] = []
    all_meds_text = " ".join(
        " ".join(seg.medications) for seg in plan_segments
    ).lower()

    # Pediatric checks
    if age < 12:
        if "aspirin" in all_meds_text:
            warnings.append(Warning(
                rule_id="R_PED_01",
                severity="high",
                message=(
                    "Aspirin is contraindicated in children under 16 due to "
                    "risk of Reye's syndrome."
                ),
                affected_modalities=[Modality.ALLOPATHY],
                resolution="Replace with Paracetamol (age-appropriate dose).",
            ))

        if any(term in all_meds_text for term in ["guggulu", "bhasma", "rasa"]):
            warnings.append(Warning(
                rule_id="R_PED_02",
                severity="medium",
                message=(
                    "Guggulu and Bhasma preparations require careful dosing "
                    "in pediatric patients. Some may contain heavy metals."
                ),
                affected_modalities=[Modality.AYURVEDA],
                resolution=(
                    "Use only pediatric-approved Ayurvedic formulations. "
                    "Prefer liquid preparations (Kwatha, Swarasa) over "
                    "Bhasma/Rasa preparations."
                ),
            ))

    # Elderly checks
    if age >= 65:
        if any(term in all_meds_text for term in ["nsaid", "ibuprofen", "diclofenac"]):
            warnings.append(Warning(
                rule_id="R_ELDER_01",
                severity="medium",
                message=(
                    "NSAIDs carry elevated risk in elderly patients: GI bleeding, "
                    "renal impairment, and cardiovascular events."
                ),
                affected_modalities=[Modality.ALLOPATHY],
                resolution=(
                    "Prefer Paracetamol. If NSAID essential, use lowest dose "
                    "for shortest duration with gastroprotection (PPI)."
                ),
            ))

    return warnings


def _check_pregnancy_safety(
    comorbidities: list[str],
    plan_segments: list[PlanSegment],
) -> list[Warning]:
    """
    Pregnancy-specific safety checks.
    """
    warnings: list[Warning] = []

    is_pregnant = any(
        term in cond.lower()
        for cond in comorbidities
        for term in ["pregnancy", "pregnant", "expecting"]
    )

    if not is_pregnant:
        return warnings

    all_meds_text = " ".join(
        " ".join(seg.medications) for seg in plan_segments
    ).lower()

    # Category X drugs
    dangerous_terms = [
        "methotrexate", "warfarin", "isotretinoin", "statins",
        "misoprostol", "thalidomide",
    ]
    for drug in dangerous_terms:
        if drug in all_meds_text:
            warnings.append(Warning(
                rule_id="R_PREG_01",
                severity="high",
                message=f"PREGNANCY CONTRAINDICATION: {drug} is Category X "
                        f"— absolutely contraindicated in pregnancy.",
                affected_modalities=[Modality.ALLOPATHY],
                resolution=f"Remove {drug} immediately. Consult obstetrician.",
            ))

    # Ayurvedic pregnancy cautions
    ayurvedic_cautions = [
        "trikatu", "vamana", "virechana", "basti", "nasya",
        "sarpagandha", "kalonji",
    ]
    for herb in ayurvedic_cautions:
        if herb in all_meds_text:
            warnings.append(Warning(
                rule_id="R_PREG_AY_01",
                severity="high",
                message=(
                    f"Ayurvedic caution during pregnancy: '{herb}' may be "
                    f"unsafe. Many Panchakarma procedures are contraindicated."
                ),
                affected_modalities=[Modality.AYURVEDA],
                resolution=(
                    "Use only pregnancy-safe Ayurvedic remedies under "
                    "qualified practitioner supervision."
                ),
            ))

    return warnings


# ═══════════════════════════════════════════════════════════════════
#  MAIN SAFETY CHECK FUNCTION
# ═══════════════════════════════════════════════════════════════════

def run_safety_checks(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    plan_segments: list[PlanSegment],
    risk_level: RiskLevel,
) -> tuple[list[Warning], list[str], AgentTrace]:
    """
    Run the complete safety & conflict checking pipeline.

    Args:
        intake: Patient intake data.
        symptom_objects: Normalized symptoms.
        plan_segments: All modality plan segments to check.
        risk_level: Current risk level.

    Returns:
        (warnings, contraindication_checks_performed, agent_trace)
    """
    started_at = datetime.utcnow()
    all_warnings: list[Warning] = []
    checks_performed: list[str] = []

    # Extract medication data from plan segments
    recommended_herbs, plan_text_by_modality = _extract_medications_from_plans(
        plan_segments
    )

    # ── CHECK 1: Core safety rules from knowledge base ─────
    checks_performed.append("Core safety rules (emergency, herb-drug, Ayurvedic)")
    kb_warnings = run_all_safety_checks(
        symptom_text=intake.symptom_text,
        symptom_terms=[s.name for s in symptom_objects],
        age=intake.age,
        medications=intake.medications,
        comorbidities=intake.comorbidities,
        recommended_herbs=recommended_herbs,
        plan_segments_text=plan_text_by_modality,
    )
    all_warnings.extend(kb_warnings)

    # ── CHECK 2: Polypharmacy ──────────────────────────────
    checks_performed.append("Polypharmacy risk assessment")
    new_meds = []
    for seg in plan_segments:
        new_meds.extend(seg.medications)
    poly_warnings = _check_polypharmacy(intake.medications, new_meds)
    all_warnings.extend(poly_warnings)

    # ── CHECK 3: Age-specific safety ───────────────────────
    checks_performed.append(f"Age-specific safety (age={intake.age})")
    age_warnings = _check_age_specific_safety(intake.age, plan_segments)
    all_warnings.extend(age_warnings)

    # ── CHECK 4: Pregnancy safety ──────────────────────────
    checks_performed.append("Pregnancy safety screen")
    preg_warnings = _check_pregnancy_safety(intake.comorbidities, plan_segments)
    all_warnings.extend(preg_warnings)

    # ── CHECK 5: Cross-modality conflict ───────────────────
    checks_performed.append("Cross-modality conflict detection")
    cross_warnings = check_cross_modality_conflicts(
        plan_text_by_modality, intake.medications
    )
    # Avoid duplicates from run_all_safety_checks
    existing_rule_ids = {w.rule_id for w in all_warnings}
    for w in cross_warnings:
        if w.rule_id not in existing_rule_ids:
            all_warnings.append(w)

    # ── CHECK 6: Allergy cross-reference ───────────────────
    checks_performed.append("Allergy cross-reference")
    if intake.allergies:
        all_plan_text = " ".join(plan_text_by_modality.values()).lower()
        for allergy in intake.allergies:
            if allergy.lower() in all_plan_text:
                all_warnings.append(Warning(
                    rule_id="R_ALLERGY_01",
                    severity="high",
                    message=(
                        f"ALLERGY ALERT: Patient has known allergy to "
                        f"'{allergy}', which appears in the care plan."
                    ),
                    affected_modalities=[Modality.ALLOPATHY, Modality.AYURVEDA],
                    resolution=(
                        f"Remove all formulations containing '{allergy}'. "
                        f"Use alternative medications."
                    ),
                ))

    # ── Deduplicate and sort by severity ───────────────────
    seen_ids: set[str] = set()
    unique_warnings: list[Warning] = []
    for w in all_warnings:
        key = f"{w.rule_id}_{w.message[:50]}"
        if key not in seen_ids:
            seen_ids.add(key)
            unique_warnings.append(w)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    unique_warnings.sort(key=lambda w: severity_order.get(w.severity, 3))

    completed_at = datetime.utcnow()
    trace = AgentTrace(
        agent_name=AgentName.SAFETY,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=(
            f"{len(plan_segments)} plan segments, "
            f"{len(intake.medications)} patient meds, "
            f"{len(intake.comorbidities)} comorbidities"
        ),
        output_summary=(
            f"{len(unique_warnings)} warnings "
            f"(high={sum(1 for w in unique_warnings if w.severity == 'high')}, "
            f"med={sum(1 for w in unique_warnings if w.severity == 'medium')}, "
            f"low={sum(1 for w in unique_warnings if w.severity == 'low')}), "
            f"{len(checks_performed)} checks performed"
        ),
    )

    return unique_warnings, checks_performed, trace
