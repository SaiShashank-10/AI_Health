"""
Recommendation Synthesizer Agent — merges all modality plan segments
into a single unified care recommendation, ranked by evidence tier.

Pipeline role:  Runs AFTER Safety Agent, BEFORE Translation Agent.
Input:          All PlanSegments, Warnings, risk data, evidence
Output:         final CareRecommendation (minus translations)

Responsibilities:
  - Merge and deduplicate recommendations across modalities
  - Rank by evidence reliability tier (A > B > T > Caution)
  - Structure final_plan JSON
  - Compile complete provenance list
  - Build explainability object
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import re

from backend.schemas.common import (
    RiskLevel,
    Modality,
    SymptomObject,
    CareStep,
    PlanSegment,
    Warning,
    EvidenceSource,
    ReliabilityTier,
    AgentTrace,
    AgentName,
    AgentStatus,
    PipelineStatus,
)
from backend.schemas.intake import PatientIntake
from backend.schemas.recommendation import (
    CareRecommendation,
    DoctorRecommendation,
    ModalityDoctorTypeRecommendation,
    Explainability,
)
from backend.services.doctor_recommender import infer_doctor_inference


# ═══════════════════════════════════════════════════════════════════
#  EVIDENCE RANKING
# ═══════════════════════════════════════════════════════════════════

TIER_RANK = {
    ReliabilityTier.A: 0,
    ReliabilityTier.B: 1,
    ReliabilityTier.T: 2,
    ReliabilityTier.CAUTION: 3,
}


def _rank_evidence(sources: list[EvidenceSource]) -> list[EvidenceSource]:
    """Sort evidence by reliability tier (A first, Caution last)."""
    return sorted(sources, key=lambda s: TIER_RANK.get(s.reliability_tier, 99))


def _deduplicate_evidence(sources: list[EvidenceSource]) -> list[EvidenceSource]:
    """Remove duplicate evidence sources by title."""
    seen: set[str] = set()
    unique: list[EvidenceSource] = []
    for source in sources:
        key = source.title.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(source)
    return unique


# ═══════════════════════════════════════════════════════════════════
#  PLAN SEGMENT ORDERING
# ═══════════════════════════════════════════════════════════════════

def _order_plan_segments(segments: list[PlanSegment]) -> list[PlanSegment]:
    """
    Order plan segments:
    1. Primary modalities first
    2. Then by average evidence tier (higher reliability first)
    3. Then by confidence score
    """
    def sort_key(seg: PlanSegment) -> tuple:
        # Primary first (0 for primary, 1 for complementary)
        priority_rank = 0 if seg.priority_label == "primary" else 1

        # Average evidence tier (lower is better)
        if seg.evidence:
            avg_tier = sum(
                TIER_RANK.get(e.reliability_tier, 3) for e in seg.evidence
            ) / len(seg.evidence)
        else:
            avg_tier = 3.0

        # Confidence (negative so higher confidence sorts first)
        confidence_rank = -seg.confidence

        return (priority_rank, avg_tier, confidence_rank)

    return sorted(segments, key=sort_key)


_MEDICATION_PATTERNS = [
    r"\btab\.?\b",
    r"\bcap\.?\b",
    r"\bsyrup\b",
    r"\binjection\b",
    r"\bmg\b",
    r"\bml\b",
    r"\bdose\b",
    r"\bparacetamol\b",
    r"\bibuprofen\b",
    r"\bantibiotic\b",
    r"\bmetformin\b",
    r"\bamlodipine\b",
]


def _looks_like_medication_line(text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return False
    return any(re.search(pattern, lowered) for pattern in _MEDICATION_PATTERNS)


def _sanitize_plan_segments(segments: list[PlanSegment]) -> list[PlanSegment]:
    """Remove medication output and medication-like recommendation lines for safer reports."""
    sanitized: list[PlanSegment] = []
    for segment in segments:
        safe_recs = [rec for rec in segment.recommendations if not _looks_like_medication_line(rec)]
        safe_follow_up = segment.follow_up or None

        sanitized.append(
            segment.model_copy(
                update={
                    "recommendations": safe_recs,
                    "medications": [],
                    "follow_up": safe_follow_up,
                }
            )
        )
    return sanitized


# ═══════════════════════════════════════════════════════════════════
#  EXPLAINABILITY BUILDER
# ═══════════════════════════════════════════════════════════════════

def _build_explainability(
    risk_level: RiskLevel,
    risk_confidence: float,
    risk_factors: list[str],
    care_steps: list[CareStep],
    plan_segments: list[PlanSegment],
    warnings: list[Warning],
    modality_rationale: list[str],
    checks_performed: list[str],
) -> Explainability:
    """Build complete explainability object."""

    # Risk factors
    explain_risk = []
    for factor in risk_factors:
        explain_risk.append(factor)

    # Risk adjustments
    risk_adjustments = [
        f"Risk level: {risk_level.value} (confidence: {risk_confidence})",
    ]
    if risk_level == RiskLevel.EMERGENT:
        risk_adjustments.append("EMERGENCY OVERRIDE applied — allopathy only")

    # Contraindication checks
    contraindication_checks = list(checks_performed)

    # Modality selection rationale
    modality_rationale_items = list(modality_rationale)

    # Rule triggers
    rule_triggers = []
    for warning in warnings:
        rule_triggers.append(
            f"[{warning.rule_id}] ({warning.severity}): {warning.message[:100]}"
        )

    return Explainability(
        risk_factors=explain_risk,
        risk_adjustments=risk_adjustments,
        contraindication_checks=contraindication_checks,
        modality_selection_rationale=modality_rationale_items,
        rule_triggers=rule_triggers,
    )


def _build_doctor_recommendation(
    session_id: str,
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
    risk_factors: list[str],
    care_steps: list[CareStep],
    warnings: list[Warning],
) -> DoctorRecommendation:
    """Build one system-assigned doctor recommendation plus modality-specific doctor types."""
    inference = infer_doctor_inference(
        session_id=session_id,
        intake=intake,
        symptom_objects=symptom_objects,
        risk_level=risk_level,
        risk_factors=risk_factors,
        care_steps=care_steps,
        warnings=warnings,
    )

    focus_specialist = inference.primary_specialty

    timing_map = {
        RiskLevel.EMERGENT: "Immediate escalation: connect within 15 minutes",
        RiskLevel.URGENT: "Priority consult: within 4 hours",
        RiskLevel.ROUTINE: "Scheduled consult: within 24 hours",
        RiskLevel.SELF_CARE: "Guidance consult: within 48 hours",
    }
    urgency_map = {
        RiskLevel.EMERGENT: "High-priority clinician oversight is mandatory.",
        RiskLevel.URGENT: "Early clinical review recommended for safe progression.",
        RiskLevel.ROUTINE: "Routine physician review advised for continuity of care.",
        RiskLevel.SELF_CARE: "Preventive check-in suggested to confirm recovery trajectory.",
    }
    mode_map = {
        RiskLevel.EMERGENT: "hybrid",
        RiskLevel.URGENT: "teleconsult",
        RiskLevel.ROUTINE: "teleconsult",
        RiskLevel.SELF_CARE: "teleconsult",
    }

    care_modalities = {step.modality.value for step in care_steps}
    has_high_warning = any((w.severity or "").lower() == "high" for w in warnings)

    doctor_type_by_modality = {
        Modality.ALLOPATHY: focus_specialist,
        Modality.AYURVEDA: "BAMS Physician (Kayachikitsa / Panchakarma Specialist)",
        Modality.HOMEOPATHY: "BHMS Homeopathic Physician (Constitutional Care)",
        Modality.HOME_REMEDIAL: "Family Medicine / Lifestyle Medicine Physician",
    }

    base_scores = {
        Modality.ALLOPATHY: 0.82,
        Modality.AYURVEDA: 0.74,
        Modality.HOMEOPATHY: 0.62,
        Modality.HOME_REMEDIAL: 0.55,
    }

    modality_recommendations: list[ModalityDoctorTypeRecommendation] = []
    for modality in [
        Modality.ALLOPATHY,
        Modality.AYURVEDA,
        Modality.HOMEOPATHY,
        Modality.HOME_REMEDIAL,
    ]:
        score = 0.25 + (inference.modality_scores.get(modality.value, 0.0) * 0.55)
        if modality.value in care_modalities:
            score += 0.07

        if risk_level == RiskLevel.EMERGENT:
            if modality == Modality.ALLOPATHY:
                score += 0.12
            elif modality == Modality.AYURVEDA:
                score -= 0.04
            else:
                score -= 0.12
        elif risk_level == RiskLevel.URGENT:
            if modality == Modality.ALLOPATHY:
                score += 0.08
            elif modality == Modality.AYURVEDA:
                score += 0.01
            else:
                score -= 0.03
        elif risk_level == RiskLevel.SELF_CARE:
            if modality == Modality.HOME_REMEDIAL:
                score += 0.12
            if modality == Modality.HOMEOPATHY:
                score += 0.05

        if has_high_warning and modality in {Modality.HOMEOPATHY, Modality.HOME_REMEDIAL}:
            score -= 0.08

        score = max(0.2, min(0.99, round(score, 2)))
        recommended = score >= 0.7
        rationale = (
            f"AI profile analysis used {inference.model_used}; risk={risk_level.value}, "
            f"symptoms, history, care path, and safety constraints informed this recommendation."
        )

        modality_recommendations.append(
            ModalityDoctorTypeRecommendation(
                modality=modality,
                doctor_type=doctor_type_by_modality[modality],
                rationale=rationale,
                suitability_score=score,
                recommended=recommended,
            )
        )

    modality_recommendations.sort(key=lambda m: m.suitability_score, reverse=True)
    best = modality_recommendations[0]

    token = hashlib.sha1(
        f"{session_id}:{risk_level.value}:{best.modality.value}:{best.doctor_type}".encode("utf-8")
    ).hexdigest()[:6].upper()

    return DoctorRecommendation(
        assignment_id=f"DOC-{token}",
        doctor_name=f"Assigned {best.doctor_type}",
        specialty=best.doctor_type,
        consultation_mode=mode_map.get(risk_level, "teleconsult"),
        next_available_window=timing_map.get(risk_level, "Scheduled consult: within 24 hours"),
        urgency_note=f"{urgency_map.get(risk_level, 'Clinical review recommended.')} {inference.confidence * 100:.0f}% confidence in AI doctor routing.",
        automation_locked=True,
        premium_feature="premium_auto_assignment",
        best_modality=best.modality,
        modality_recommendations=modality_recommendations,
    )


# ═══════════════════════════════════════════════════════════════════
#  MAIN SYNTHESIZER FUNCTION
# ═══════════════════════════════════════════════════════════════════

def synthesize_recommendation(
    session_id: str,
    patient_hash: str,
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
    risk_confidence: float,
    risk_score: float,
    triage_justification: str,
    risk_factors: list[str],
    care_steps: list[CareStep],
    plan_segments: list[PlanSegment],
    warnings: list[Warning],
    modality_rationale: list[str],
    checks_performed: list[str],
    agent_traces: list[AgentTrace],
) -> tuple[CareRecommendation, AgentTrace]:
    """
    Synthesize all pipeline outputs into a single CareRecommendation.

    Args:
        session_id: Unique session identifier.
        patient_hash: Pseudonymized patient ID.
        risk_level: From triage agent.
        risk_confidence: Confidence score for triage.
        risk_score: Model-assisted risk score from triage.
        triage_justification: Text explanation from triage.
        risk_factors: List of risk factor descriptions.
        care_steps: From orchestrator agent.
        plan_segments: From all specialist agents.
        warnings: From safety agent.
        modality_rationale: From orchestrator agent.
        checks_performed: From safety agent.
        agent_traces: All agent traces collected so far.

    Returns:
        (care_recommendation, synthesizer_trace)
    """
    started_at = datetime.utcnow()

    # Step 1: Order plan segments by priority and evidence quality
    ordered_segments = _order_plan_segments(plan_segments)
    ordered_segments = _sanitize_plan_segments(ordered_segments)

    # Step 2: Compile all evidence sources (deduplicated, ranked)
    all_evidence: list[EvidenceSource] = []
    for segment in ordered_segments:
        all_evidence.extend(segment.evidence)
    all_evidence = _deduplicate_evidence(all_evidence)
    all_evidence = _rank_evidence(all_evidence)

    # Step 3: Build explainability
    explainability = _build_explainability(
        risk_level=risk_level,
        risk_confidence=risk_confidence,
        risk_factors=risk_factors,
        care_steps=care_steps,
        plan_segments=ordered_segments,
        warnings=warnings,
        modality_rationale=modality_rationale,
        checks_performed=checks_performed,
    )

    # Step 4: Build premium doctor auto-assignment (single, locked)
    doctor_recommendation = _build_doctor_recommendation(
        session_id=session_id,
        intake=intake,
        symptom_objects=symptom_objects,
        risk_level=risk_level,
        risk_factors=risk_factors,
        care_steps=care_steps,
        warnings=warnings,
    )

    # Step 5: Create synthesizer trace
    completed_at = datetime.utcnow()
    synth_trace = AgentTrace(
        agent_name=AgentName.SYNTHESIZER,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=(
            f"{len(plan_segments)} segments, {len(warnings)} warnings, "
            f"{len(all_evidence)} evidence sources"
        ),
        output_summary=(
            f"Synthesized final plan: {len(ordered_segments)} segments, "
            f"{len(all_evidence)} evidence (ranked by tier), "
            f"{len(warnings)} warnings, "
            f"explainability: {len(explainability.rule_triggers)} rules triggered, "
            f"doctor assignment: {doctor_recommendation.assignment_id}"
        ),
    )

    # Collect all traces (existing + synthesizer)
    all_traces = list(agent_traces) + [synth_trace]

    # Step 6: Build final CareRecommendation
    recommendation = CareRecommendation(
        session_id=session_id,
        patient_hash=patient_hash,
        timestamp=datetime.utcnow(),
        pipeline_status=PipelineStatus.COMPLETED,
        risk_level=risk_level,
        risk_confidence=risk_confidence,
        risk_score=risk_score,
        triage_justification=triage_justification,
        care_path=care_steps,
        plan_segments=ordered_segments,
        warnings=warnings,
        provenance=all_evidence,
        translations=[],  # Filled by Translation Agent next
        doctor_recommendation=doctor_recommendation,
        explainability=explainability,
        agent_trace=all_traces,
    )

    return recommendation, synth_trace
