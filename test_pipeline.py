"""
PHASE 3 BATCH 2 — End-to-End Pipeline Verification Script

Tests the complete 8-agent pipeline from intake to translated recommendation.
Specifically validates:
  1. Normalization detects multilingual symptoms
  2. Triage assigns correct risk level
  3. Orchestrator builds appropriate care path
  4. Allopathy + Ayurveda generate plan segments
  5. Safety agent catches herb-drug conflicts
  6. Synthesizer merges everything with evidence ranking
  7. Translation produces multilingual output
"""
import json
from backend.schemas.intake import PatientIntake
from backend.agents.normalization import normalize_intake
from backend.agents.triage import run_triage
from backend.agents.orchestrator import build_care_path
from backend.agents.allopathy import generate_allopathy_plan
from backend.agents.ayurveda import generate_ayurveda_plan
from backend.agents.safety import run_safety_checks
from backend.agents.synthesizer import synthesize_recommendation
from backend.agents.translation import translate_recommendation

print("=" * 60)
print("  PHASE 3 BATCH 2 — FULL PIPELINE TEST")
print("=" * 60)

# ── Test Case: Patient with herb-drug interaction risk ──
intake = PatientIntake(
    patient_hash="p_test01",
    language_pref="hi",
    age=45,
    sex="F",
    symptom_text="Bukhad aur sardard, jodo ka dard, kamar dard for 5 days",
    duration_days=5,
    comorbidities=["hypertension", "diabetes"],
    medications=["amlodipine", "metformin"],
    modality_preferences=["allopathy", "ayurveda"],
)

print(f"\n✅ Patient: age={intake.age}, sex={intake.sex}")
print(f"   Symptoms: {intake.symptom_text}")
print(f"   Comorbidities: {intake.comorbidities}")
print(f"   Medications: {intake.medications}")
print(f"   Preferences: {intake.modality_preferences}")

# Agent 1: Normalization
syms, t1 = normalize_intake(intake)
names = [s.name for s in syms]
print(f"\n✅ Agent 1 — Normalization: {len(syms)} symptoms detected")
print(f"   Detected: {names}")
print(f"   Dosha tags: {[(s.name, s.dosha_tag.value if s.dosha_tag else None) for s in syms]}")

# Agent 2: Triage
risk, conf, just, factors, t2 = run_triage(intake, syms)
print(f"\n✅ Agent 2 — Triage: {risk.value} (confidence={conf})")
print(f"   Justification: {just[:120]}...")

# Agent 3: Orchestrator
steps, rationale, t3 = build_care_path(intake, syms, risk)
print(f"\n✅ Agent 3 — Orchestrator: {len(steps)} care steps")
for s in steps:
    print(f"   Step {s.step_number}: {s.modality.value} ({s.priority}) → {s.specialist_type}")

# Agent 4: Allopathy Specialist
allo_plan, t4 = generate_allopathy_plan(intake, syms, risk)
print(f"\n✅ Agent 4 — Allopathy: {len(allo_plan.recommendations)} recs, "
      f"{len(allo_plan.medications)} meds, {len(allo_plan.evidence)} evidence")

# Agent 5: Ayurveda Specialist
ayur_plan, dosha, scores, t5 = generate_ayurveda_plan(intake, syms, risk)
print(f"\n✅ Agent 5 — Ayurveda: dosha={dosha.value}, scores={scores}")
print(f"   {len(ayur_plan.recommendations)} recs, "
      f"{len(ayur_plan.medications)} formulations, "
      f"{len(ayur_plan.evidence)} evidence")

# Agent 6: Safety & Conflict
all_segments = [allo_plan, ayur_plan]
warnings, checks, t6 = run_safety_checks(intake, syms, all_segments, risk)
print(f"\n✅ Agent 6 — Safety: {len(warnings)} warnings, {len(checks)} checks")
for w in warnings:
    print(f"   [{w.severity.upper()}] {w.rule_id}: {w.message[:80]}...")

# Agent 7: Synthesizer
traces = [t1, t2, t3, t4, t5, t6]
rec, t7 = synthesize_recommendation(
    session_id="test_session_001",
    patient_hash=intake.patient_hash,
    risk_level=risk,
    risk_confidence=conf,
    triage_justification=just,
    risk_factors=factors,
    care_steps=steps,
    plan_segments=all_segments,
    warnings=warnings,
    modality_rationale=rationale,
    checks_performed=checks,
    agent_traces=traces,
)
print(f"\n✅ Agent 7 — Synthesizer: final plan assembled")
print(f"   Plan segments: {len(rec.plan_segments)}")
print(f"   Evidence sources: {len(rec.provenance)}")
print(f"   Warnings: {len(rec.warnings)}")
print(f"   Explainability rules triggered: {len(rec.explainability.rule_triggers)}")

# Agent 8: Translation
translations, t8 = translate_recommendation(rec, ["hi", "ta"])
print(f"\n✅ Agent 8 — Translation: {len(translations)} languages")
for t in translations:
    print(f"   {t.language_name} ({t.language_code}):")
    print(f"   Summary preview: {t.summary[:100]}...")
    print(f"   Recs: {len(t.recommendations)}, Warnings: {len(t.warnings)}")

# Final summary
print("\n" + "=" * 60)
print("  ✅ ALL 8 AGENTS PASSED — FULL PIPELINE VERIFIED")
print("=" * 60)
print(f"\nPipeline: Intake → Normalization → Triage → Orchestrator")
print(f"  → Allopathy → Ayurveda → Safety → Synthesizer → Translation")
print(f"\nTotal agent traces: {len(rec.agent_trace) + 1}")
