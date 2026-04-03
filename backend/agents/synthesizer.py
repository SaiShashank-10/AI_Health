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

from backend.schemas.common import (
    RiskLevel,
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
from backend.schemas.recommendation import (
    CareRecommendation,
    Explainability,
)


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


# ═══════════════════════════════════════════════════════════════════
#  MAIN SYNTHESIZER FUNCTION
# ═══════════════════════════════════════════════════════════════════

def synthesize_recommendation(
    session_id: str,
    patient_hash: str,
    risk_level: RiskLevel,
    risk_confidence: float,
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

    # Step 4: Create synthesizer trace
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
            f"explainability: {len(explainability.rule_triggers)} rules triggered"
        ),
    )

    # Collect all traces (existing + synthesizer)
    all_traces = list(agent_traces) + [synth_trace]

    # Step 5: Build final CareRecommendation
    recommendation = CareRecommendation(
        session_id=session_id,
        patient_hash=patient_hash,
        timestamp=datetime.utcnow(),
        pipeline_status=PipelineStatus.COMPLETED,
        risk_level=risk_level,
        risk_confidence=risk_confidence,
        triage_justification=triage_justification,
        care_path=care_steps,
        plan_segments=ordered_segments,
        warnings=warnings,
        provenance=all_evidence,
        translations=[],  # Filled by Translation Agent next
        explainability=explainability,
        agent_trace=all_traces,
    )

    return recommendation, synth_trace
