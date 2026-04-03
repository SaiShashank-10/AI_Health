"""
Allopathy Specialist Agent — generates evidence-based allopathic
treatment recommendations.

Pipeline role:  MODALITY SPECIALIST (called by Orchestrator).
Input:          list[SymptomObject], PatientIntake, RiskLevel
Output:         PlanSegment (structured_plan_segment)

Provides:
  - Medication recommendations with dosage
  - Diagnostic investigations to order
  - Lifestyle modifications
  - Follow-up timeline
  - Evidence citations with reliability tier
"""
from __future__ import annotations

from datetime import datetime

from backend.schemas.common import (
    RiskLevel,
    Modality,
    Severity,
    SymptomObject,
    PlanSegment,
    EvidenceSource,
    AgentTrace,
    AgentName,
    AgentStatus,
)
from backend.schemas.intake import PatientIntake
from backend.knowledge.evidence_base import get_evidence_for_condition


# ═══════════════════════════════════════════════════════════════════
#  ALLOPATHIC TREATMENT DATABASE  (rule-based simulation)
# ═══════════════════════════════════════════════════════════════════

ALLOPATHY_TREATMENTS: dict[str, dict] = {
    "fever": {
        "recommendations": [
            "Paracetamol (Acetaminophen) 500-1000mg every 4-6 hours as needed (max 4g/day)",
            "Ensure adequate oral hydration — at least 2-3 liters of fluids daily",
            "Tepid sponging for temperature >39°C (102.2°F)",
            "Investigate underlying cause if fever persists >3 days",
        ],
        "medications": [
            "Tab. Paracetamol 500mg — 1 tab every 6 hours (SOS)",
            "ORS sachets — dissolve in 1L water, sip throughout the day",
        ],
        "investigations": [
            "Complete Blood Count (CBC) with differential",
            "Peripheral smear for malarial parasites (if endemic area)",
            "Urine routine & culture (if UTI suspected)",
            "Blood culture (if fever >5 days)",
        ],
        "lifestyle": [
            "Complete bed rest until fever subsides",
            "Light, easily digestible diet (khichdi, dal, soups)",
            "Avoid cold beverages; lukewarm fluids preferred",
            "Monitor temperature every 4-6 hours",
        ],
        "follow_up": "Review in 3 days if fever persists. Seek immediate care if temperature >40°C or new symptoms develop.",
    },
    "headache": {
        "recommendations": [
            "Ibuprofen 400mg or Paracetamol 1000mg for acute relief",
            "Identify and avoid triggers (stress, screen time, dehydration)",
            "Neurological evaluation if recurrent or progressive",
            "Consider prophylaxis if >4 episodes/month",
        ],
        "medications": [
            "Tab. Ibuprofen 400mg — 1 tab as needed (max 3/day with food)",
            "Tab. Paracetamol 500mg — alternative if NSAID intolerant",
        ],
        "investigations": [
            "Blood pressure measurement",
            "Visual acuity check",
            "CT/MRI Brain (if red flags: thunderclap onset, focal deficits, papilledema)",
        ],
        "lifestyle": [
            "Regular sleep schedule (7-8 hours)",
            "Adequate hydration (2-3L/day)",
            "Reduce screen time; take 20-20-20 breaks",
            "Stress management techniques",
        ],
        "follow_up": "Review in 1 week. If worsening or new neurological symptoms, seek immediate evaluation.",
    },
    "cough": {
        "recommendations": [
            "Determine type: dry vs productive cough",
            "Honey-based cough syrups for symptomatic relief (adults)",
            "Antihistamines if post-nasal drip suspected",
            "Chest X-ray if cough >3 weeks or hemoptysis",
        ],
        "medications": [
            "Syp. Dextromethorphan 10ml — every 8 hours (dry cough)",
            "Tab. Cetirizine 10mg — once daily at bedtime (if allergic component)",
            "Steam inhalation with menthol — twice daily",
        ],
        "investigations": [
            "Chest X-ray PA view (if >2 weeks)",
            "Sputum examination (if productive cough >1 week)",
            "Spirometry (if wheezing or suspected asthma)",
        ],
        "lifestyle": [
            "Avoid smoke, dust, and cold air exposure",
            "Warm fluids and gargling with salt water",
            "Elevate head during sleep",
            "Quit smoking if applicable",
        ],
        "follow_up": "Review in 5-7 days. Seek immediate care if breathlessness, blood in sputum, or high fever develops.",
    },
    "joint pain": {
        "recommendations": [
            "Topical NSAID gel (Diclofenac 1%) as first-line for localized pain",
            "Oral NSAIDs at lowest effective dose for shortest duration",
            "Physiotherapy referral for chronic cases",
            "Evaluate for inflammatory vs mechanical cause",
        ],
        "medications": [
            "Gel Diclofenac 1% — apply to affected joint 3-4 times daily",
            "Tab. Ibuprofen 400mg — 1 tab twice daily with food (max 5 days)",
            "Tab. Paracetamol 500mg — alternative if NSAID contraindicated",
            "Cap. Calcium + Vitamin D3 — 1 daily (if deficiency suspected)",
        ],
        "investigations": [
            "X-ray of affected joint",
            "ESR, CRP (inflammatory markers)",
            "Rheumatoid Factor, Anti-CCP (if RA suspected)",
            "Serum Uric Acid (if gout suspected)",
            "Vitamin D3, B12 levels",
        ],
        "lifestyle": [
            "Regular low-impact exercise (swimming, walking)",
            "Weight management if BMI >25",
            "Apply hot/cold compress (20 min, 3x/day)",
            "Ergonomic adjustments at workplace",
        ],
        "follow_up": "Review in 2 weeks with investigation reports. Refer to Rheumatologist if inflammatory markers elevated.",
    },
    "stomach pain": {
        "recommendations": [
            "Assess location, character, and radiation of pain",
            "Antacids / PPIs for epigastric pain with acidity symptoms",
            "Rule out surgical causes (appendicitis, cholecystitis) if severe",
            "H. pylori testing if recurrent dyspepsia",
        ],
        "medications": [
            "Tab. Pantoprazole 40mg — once daily before breakfast",
            "Syp. Sucralfate 10ml — before meals (mucosal protection)",
            "Tab. Domperidone 10mg — before meals (if bloating/nausea)",
        ],
        "investigations": [
            "Ultrasound Abdomen",
            "Upper GI Endoscopy (if >2 weeks or alarm symptoms)",
            "H. pylori stool antigen test",
            "Liver function tests",
        ],
        "lifestyle": [
            "Small, frequent meals (5-6/day instead of 3 large)",
            "Avoid spicy, fried, and acidic foods",
            "No lying down within 2 hours of eating",
            "Limit caffeine and alcohol",
        ],
        "follow_up": "Review in 1 week. Seek immediate care if severe pain, vomiting blood, or black stools.",
    },
    "acidity": {
        "recommendations": [
            "Proton Pump Inhibitor (PPI) therapy for 4-8 weeks",
            "Lifestyle and dietary modifications essential",
            "H. pylori eradication if positive",
            "Endoscopy if symptoms persist >8 weeks on PPI",
        ],
        "medications": [
            "Tab. Pantoprazole 40mg — once daily, 30 min before breakfast",
            "Tab. Antacid (Aluminum/Magnesium hydroxide) — SOS after meals",
            "Tab. Domperidone 10mg — before meals if bloating present",
        ],
        "investigations": [
            "H. pylori stool antigen or urea breath test",
            "Upper GI Endoscopy (if refractory symptoms)",
        ],
        "lifestyle": [
            "Avoid trigger foods: spicy, citrus, tomato, coffee, alcohol",
            "Elevate head of bed 15-20cm",
            "Eat dinner at least 3 hours before bedtime",
            "Weight loss if overweight",
            "Stress reduction techniques",
        ],
        "follow_up": "Review in 4 weeks. If symptom-free, taper PPI. If persistent, refer for endoscopy.",
    },
    "back pain": {
        "recommendations": [
            "Activity modification — avoid prolonged sitting/standing",
            "NSAIDs for acute pain relief (short course)",
            "Physiotherapy and core strengthening exercises",
            "MRI spine if red flags or >6 weeks without improvement",
        ],
        "medications": [
            "Tab. Ibuprofen 400mg — twice daily with food (5-7 days)",
            "Tab. Thiocolchicoside 4mg — twice daily (muscle relaxant, 5 days)",
            "Gel Diclofenac — apply locally twice daily",
        ],
        "investigations": [
            "X-ray Lumbosacral spine AP/Lateral",
            "MRI Lumbar spine (if radiculopathy or red flags)",
            "Vitamin D3, B12, Calcium levels",
        ],
        "lifestyle": [
            "Correct posture during sitting and standing",
            "Regular stretching and core strengthening exercises",
            "Firm mattress for sleeping",
            "Avoid lifting heavy objects",
        ],
        "follow_up": "Review in 2 weeks. Physiotherapy referral if not improving. Neurosurgery consult if radiculopathy.",
    },
    "anxiety": {
        "recommendations": [
            "Psychotherapy (CBT) as first-line treatment",
            "SSRI if moderate-severe or persistent symptoms",
            "Rule out thyroid dysfunction and substance use",
            "Benzodiazepines only for short-term acute relief",
        ],
        "medications": [
            "Tab. Escitalopram 5mg — once daily (start low, titrate to 10mg)",
            "Tab. Propranolol 10mg — SOS for acute episodes (if no asthma)",
        ],
        "investigations": [
            "Thyroid function tests (TSH, T3, T4)",
            "CBC, Blood sugar (rule out medical causes)",
            "PHQ-9 and GAD-7 screening questionnaires",
        ],
        "lifestyle": [
            "Regular physical exercise (30 min, 5 days/week)",
            "Mindfulness meditation or yoga",
            "Limit caffeine and alcohol",
            "Consistent sleep schedule",
            "Social support and stress management",
        ],
        "follow_up": "Review in 2 weeks to assess response. Monthly follow-up for medication adjustment. Psychiatry referral if severe.",
    },
    "insomnia": {
        "recommendations": [
            "Sleep hygiene education as first-line intervention",
            "CBT for Insomnia (CBT-I) — most effective long-term",
            "Short-term pharmacotherapy if CBT-I insufficient",
            "Rule out sleep apnea, restless leg syndrome",
        ],
        "medications": [
            "Tab. Melatonin 3mg — 30 min before bedtime (2-4 weeks)",
            "Tab. Zolpidem 5mg — at bedtime SOS (short-term only, max 2 weeks)",
        ],
        "investigations": [
            "Thyroid function tests",
            "Iron studies (ferritin) — rule out restless legs",
            "Sleep study (polysomnography) — if sleep apnea suspected",
        ],
        "lifestyle": [
            "Fixed wake-up time, even on weekends",
            "No screens 1 hour before bed",
            "Cool, dark, quiet bedroom environment",
            "Avoid caffeine after 2 PM",
            "Regular exercise (but not within 3 hours of bedtime)",
        ],
        "follow_up": "Review in 2 weeks. Sleep diary recommended. Refer to sleep medicine if persistent.",
    },
    "diabetes": {
        "recommendations": [
            "Metformin as first-line for Type 2 Diabetes",
            "Lifestyle modification: diet + exercise essential",
            "HbA1c target <7% for most adults",
            "Screen for complications annually (retinal, renal, neuropathy)",
        ],
        "medications": [
            "Tab. Metformin 500mg — twice daily with meals (titrate to 1000mg BD)",
            "Monitor blood glucose: fasting + post-prandial",
        ],
        "investigations": [
            "HbA1c (every 3 months until stable, then 6-monthly)",
            "Fasting lipid profile",
            "Serum creatinine, eGFR, urine microalbumin",
            "Fundoscopy (annual)",
            "Foot examination (annual)",
        ],
        "lifestyle": [
            "Balanced diet with complex carbohydrates, fiber, and lean protein",
            "Portion control — avoid refined sugars and processed foods",
            "150 minutes of moderate exercise per week",
            "Daily foot care and inspection",
            "Regular blood glucose monitoring",
        ],
        "follow_up": "Review in 1 month with HbA1c. Then every 3 months. Annual comprehensive diabetes screening.",
    },
    "hypertension": {
        "recommendations": [
            "Lifestyle modifications first for Stage 1 HTN without risk factors",
            "ARB or CCB as preferred first-line in Indian population",
            "Target BP: <130/80 mmHg for most adults",
            "Assess for end-organ damage (heart, kidneys, eyes)",
        ],
        "medications": [
            "Tab. Telmisartan 40mg — once daily morning",
            "Tab. Amlodipine 5mg — once daily (if CCB preferred)",
        ],
        "investigations": [
            "ECG — baseline cardiac assessment",
            "Echocardiography (if suspected LVH)",
            "Renal function tests (creatinine, electrolytes)",
            "Fasting lipid profile",
            "Fundoscopy (hypertensive retinopathy screening)",
            "Urine microalbumin",
        ],
        "lifestyle": [
            "DASH diet — rich in fruits, vegetables, whole grains",
            "Salt restriction: <5g/day (1 teaspoon)",
            "Regular aerobic exercise: 30 min, 5 days/week",
            "Weight reduction if BMI >25",
            "Limit alcohol and quit smoking",
            "Stress management and adequate sleep",
        ],
        "follow_up": "Review in 2 weeks for BP response. Monthly until controlled. Home BP monitoring recommended.",
    },
    "diarrhea": {
        "recommendations": [
            "Oral rehydration therapy — cornerstone of management",
            "Identify cause: infectious vs dietary vs drug-induced",
            "Antibiotics only if bacterial cause confirmed",
            "Antidiarrheals cautiously (avoid in bloody diarrhea)",
        ],
        "medications": [
            "ORS packets — dissolve in 1L water, ad libitum",
            "Tab. Zinc 20mg — once daily for 10-14 days",
            "Tab. Racecadotril 100mg — three times daily (antisecretory)",
            "Probiotics (Saccharomyces boulardii) — once daily",
        ],
        "investigations": [
            "Stool routine and culture",
            "Stool for ova and parasites",
            "Serum electrolytes (if severe dehydration)",
        ],
        "lifestyle": [
            "Clear fluids, ORS, coconut water, rice water",
            "BRAT diet: bananas, rice, applesauce, toast",
            "Avoid dairy, fatty, and spicy foods until resolved",
            "Monitor urine output for dehydration",
        ],
        "follow_up": "Review in 2-3 days. Seek immediate care if blood in stool, high fever, or signs of dehydration.",
    },
    "rash": {
        "recommendations": [
            "Identify and avoid trigger (allergen, contact irritant)",
            "Topical corticosteroids for inflammatory dermatoses",
            "Oral antihistamines for pruritus",
            "Biopsy if atypical or not responding to treatment",
        ],
        "medications": [
            "Cream Hydrocortisone 1% — apply thin layer twice daily (max 2 weeks)",
            "Tab. Cetirizine 10mg — once daily at bedtime",
            "Calamine lotion — apply SOS for itch relief",
        ],
        "investigations": [
            "Skin scraping/KOH mount (if fungal suspected)",
            "IgE levels (if allergic etiology)",
            "Skin biopsy (if persistent or atypical)",
        ],
        "lifestyle": [
            "Wear loose, cotton clothing",
            "Mild, fragrance-free soap and moisturizer",
            "Avoid scratching — keep nails short",
            "Identify and eliminate allergens/irritants",
        ],
        "follow_up": "Review in 1 week. Dermatology referral if spreading or not improving.",
    },
}

# Generic fallback for symptoms not in the database
GENERIC_TREATMENT: dict = {
    "recommendations": [
        "Consult a General Physician for clinical evaluation",
        "Symptomatic management based on clinical assessment",
        "Investigate further if symptoms persist >1 week",
    ],
    "medications": [
        "Symptomatic treatment as prescribed by physician",
    ],
    "investigations": [
        "Complete Blood Count (CBC)",
        "Basic metabolic panel",
    ],
    "lifestyle": [
        "Adequate rest and hydration",
        "Balanced, nutritious diet",
        "Monitor symptoms and maintain a health diary",
    ],
    "follow_up": "Schedule a follow-up within 1 week if symptoms do not improve.",
}


# ═══════════════════════════════════════════════════════════════════
#  ALLOPATHY SPECIALIST FUNCTION
# ═══════════════════════════════════════════════════════════════════

def generate_allopathy_plan(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
    is_primary: bool = True,
) -> tuple[PlanSegment, AgentTrace]:
    """
    Generate evidence-based allopathic treatment plan.

    Args:
        intake: Patient intake data.
        symptom_objects: Normalized symptoms.
        risk_level: Triage risk level.
        is_primary: Whether allopathy is the primary modality.

    Returns:
        (plan_segment, agent_trace)
    """
    started_at = datetime.utcnow()

    all_recommendations: list[str] = []
    all_medications: list[str] = []
    all_lifestyle: list[str] = []
    all_evidence: list[EvidenceSource] = []
    follow_ups: list[str] = []
    seen_recs: set[str] = set()

    # Process each symptom
    for symptom in symptom_objects:
        treatment = ALLOPATHY_TREATMENTS.get(symptom.name, GENERIC_TREATMENT)

        # Add recommendations (deduplicated)
        for rec in treatment["recommendations"]:
            if rec not in seen_recs:
                all_recommendations.append(rec)
                seen_recs.add(rec)

        # Add medications
        all_medications.extend(treatment.get("medications", []))

        # Add investigations as recommendations
        for inv in treatment.get("investigations", []):
            inv_text = f"Investigation: {inv}"
            if inv_text not in seen_recs:
                all_recommendations.append(inv_text)
                seen_recs.add(inv_text)

        # Add lifestyle
        for ls in treatment.get("lifestyle", []):
            if ls not in seen_recs:
                all_lifestyle.append(ls)
                seen_recs.add(ls)

        # Follow-up
        if treatment.get("follow_up"):
            follow_ups.append(treatment["follow_up"])

        # Evidence
        evidence = get_evidence_for_condition(symptom.name, "allopathy")
        all_evidence.extend(evidence)

    # Medication safety: flag if patient has allergies
    if intake.allergies:
        all_recommendations.insert(
            0,
            f"⚠️ Patient has known allergies: {', '.join(intake.allergies)}. "
            f"Verify all prescriptions against allergy list."
        )

    # Comorbidity-aware adjustments
    comorbidity_notes = _get_comorbidity_adjustments(
        intake.comorbidities, intake.medications
    )
    if comorbidity_notes:
        all_recommendations.extend(comorbidity_notes)

    # Confidence based on evidence availability and symptom match
    confidence = min(
        0.95,
        0.6 + (len(all_evidence) * 0.05) + (len(symptom_objects) * 0.03),
    )

    # Build plan title
    symptom_names = [s.name for s in symptom_objects[:3]]
    title = f"Allopathic Treatment Plan — {', '.join(symptom_names)}"
    if len(symptom_objects) > 3:
        title += f" (+{len(symptom_objects) - 3} more)"

    # Combine follow-ups
    combined_follow_up = " | ".join(follow_ups[:3]) if follow_ups else (
        "Schedule routine follow-up in 1-2 weeks."
    )

    plan = PlanSegment(
        modality=Modality.ALLOPATHY,
        title=title,
        recommendations=all_recommendations,
        medications=all_medications,
        lifestyle=all_lifestyle,
        follow_up=combined_follow_up,
        evidence=all_evidence,
        priority_label="primary" if is_primary else "complementary",
        confidence=round(confidence, 2),
    )

    completed_at = datetime.utcnow()
    trace = AgentTrace(
        agent_name=AgentName.ALLOPATHY,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=f"{len(symptom_objects)} symptoms, risk={risk_level.value}",
        output_summary=f"{len(all_recommendations)} recs, "
                       f"{len(all_medications)} meds, "
                       f"{len(all_evidence)} evidence sources",
    )

    return plan, trace


def _get_comorbidity_adjustments(
    comorbidities: list[str], medications: list[str]
) -> list[str]:
    """Generate comorbidity-aware medication adjustments."""
    notes: list[str] = []
    comorbidities_lower = [c.lower() for c in comorbidities]
    meds_lower = [m.lower() for m in medications]

    if any("hypertension" in c for c in comorbidities_lower):
        notes.append(
            "⚠️ Hypertension: Avoid NSAIDs if possible (can raise BP). "
            "Prefer Paracetamol for pain. Monitor BP regularly."
        )

    if any("diabetes" in c for c in comorbidities_lower):
        notes.append(
            "⚠️ Diabetes: Avoid corticosteroids (raise blood sugar). "
            "Sugar-free formulations preferred. Monitor glucose closely."
        )

    if any("asthma" in c for c in comorbidities_lower):
        notes.append(
            "⚠️ Asthma: Avoid NSAIDs and beta-blockers. "
            "Use Paracetamol for pain/fever."
        )

    if any("kidney" in c for c in comorbidities_lower):
        notes.append(
            "⚠️ Kidney disease: Dose-adjust renally cleared drugs. "
            "Avoid nephrotoxic agents. Monitor creatinine."
        )

    if any("warfarin" in m or "anticoagulant" in m for m in meds_lower):
        notes.append(
            "⚠️ Patient on anticoagulants: Avoid aspirin and NSAIDs "
            "unless specifically indicated. Monitor INR."
        )

    return notes
