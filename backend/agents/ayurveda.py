"""
Ayurveda Specialist Agent — generates dosha-aligned Ayurvedic treatment
recommendations based on symptoms, constitution, and classical texts.

Pipeline role:  MODALITY SPECIALIST (called by Orchestrator).
Input:          list[SymptomObject], PatientIntake, RiskLevel
Output:         PlanSegment (dosha_plan_segment)

Provides:
  - Dosha imbalance assessment (Vata / Pitta / Kapha)
  - Herbal formulation recommendations
  - Panchakarma / therapy suggestions
  - Dietary guidelines (Pathya-Apathya)
  - Lifestyle (Dinacharya) modifications
  - Evidence citations from classical texts and CCRAS studies
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from backend.schemas.common import (
    RiskLevel,
    Modality,
    Severity,
    DoshaType,
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
#  DOSHA ASSESSMENT
# ═══════════════════════════════════════════════════════════════════

def _assess_dominant_dosha(
    symptom_objects: list[SymptomObject],
    age: int,
    sex: str,
) -> tuple[DoshaType, dict[str, float], str]:
    """
    Determine the dominant dosha imbalance from symptoms, age, and
    constitutional indicators.

    Returns: (dominant_dosha, dosha_scores, assessment_text)
    """
    dosha_counts: Counter = Counter()

    # Count dosha tags from symptoms
    for sym in symptom_objects:
        if sym.dosha_tag:
            tag = sym.dosha_tag.value
            # Compound doshas contribute to both
            if "-" in tag:
                parts = tag.split("-")
                for p in parts:
                    dosha_counts[p] += 1.0
            else:
                dosha_counts[tag] += 1.5  # Pure dosha gets more weight

    # Age-based dosha tendency (Ayurvedic principle)
    if age <= 16:
        dosha_counts["kapha"] += 0.5   # Kapha predominance in childhood
    elif age <= 50:
        dosha_counts["pitta"] += 0.5   # Pitta predominance in middle age
    else:
        dosha_counts["vata"] += 0.5    # Vata predominance in old age

    # Normalize to percentages
    total = sum(dosha_counts.values()) or 1.0
    dosha_scores = {
        "vata": round((dosha_counts.get("vata", 0) / total) * 100, 1),
        "pitta": round((dosha_counts.get("pitta", 0) / total) * 100, 1),
        "kapha": round((dosha_counts.get("kapha", 0) / total) * 100, 1),
    }

    # Determine dominant dosha
    dominant = max(dosha_scores, key=lambda k: dosha_scores[k])
    dosha_map = {
        "vata": DoshaType.VATA,
        "pitta": DoshaType.PITTA,
        "kapha": DoshaType.KAPHA,
    }
    dominant_dosha = dosha_map[dominant]

    # Check for dual-dosha dominance
    sorted_scores = sorted(dosha_scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_scores) >= 2:
        diff = sorted_scores[0][1] - sorted_scores[1][1]
        if diff < 10:  # Close scores → dual dosha
            combo = f"{sorted_scores[0][0]}-{sorted_scores[1][0]}"
            dual_map = {
                "vata-pitta": DoshaType.VATA_PITTA,
                "pitta-vata": DoshaType.VATA_PITTA,
                "pitta-kapha": DoshaType.PITTA_KAPHA,
                "kapha-pitta": DoshaType.PITTA_KAPHA,
                "vata-kapha": DoshaType.VATA_KAPHA,
                "kapha-vata": DoshaType.VATA_KAPHA,
            }
            dominant_dosha = dual_map.get(combo, dominant_dosha)

    # Build assessment text
    assessment = (
        f"Dosha Analysis: Vata {dosha_scores['vata']}%, "
        f"Pitta {dosha_scores['pitta']}%, "
        f"Kapha {dosha_scores['kapha']}%. "
        f"Primary imbalance: {dominant_dosha.value.upper()}. "
    )

    if dominant == "vata":
        assessment += (
            "Vata vitiation indicated by symptoms of pain, dryness, "
            "irregularity, and nervous system involvement. "
            "Treatment focus: Vata Shamana (pacification) through "
            "warmth, nourishment, and regularity."
        )
    elif dominant == "pitta":
        assessment += (
            "Pitta vitiation indicated by symptoms of heat, inflammation, "
            "burning, and metabolic disturbance. "
            "Treatment focus: Pitta Shamana through cooling, soothing, "
            "and anti-inflammatory measures."
        )
    else:
        assessment += (
            "Kapha vitiation indicated by symptoms of congestion, heaviness, "
            "sluggishness, and fluid accumulation. "
            "Treatment focus: Kapha Shamana through stimulation, lightening, "
            "and drying measures."
        )

    return dominant_dosha, dosha_scores, assessment


# ═══════════════════════════════════════════════════════════════════
#  AYURVEDIC TREATMENT DATABASE
# ═══════════════════════════════════════════════════════════════════

AYURVEDA_TREATMENTS: dict[str, dict] = {
    "fever": {
        "formulations": [
            "Sudarshana Churna — 3g twice daily with warm water (classical Jwara-hara)",
            "Guduchi (Tinospora cordifolia) Kwatha — 30ml twice daily",
            "Tulsi + Ginger + Black Pepper decoction — 100ml twice daily",
        ],
        "therapies": [
            "Langhana (therapeutic fasting) during acute phase",
            "Pachana (digestive correction) with Trikatu if Kapha-type fever",
            "Svedana (mild steam) after fever subsides for residual ama",
        ],
        "pathya_diet": [
            "Light, warm, liquid diet: Yusha (lentil soup), Peya (rice gruel)",
            "Warm water infused with cumin and coriander seeds",
            "Avoid heavy, oily, cold foods and dairy during fever",
            "Ripe pomegranate juice for hydration and appetite",
        ],
        "dinacharya": [
            "Complete rest; avoid exertion and mental stress",
            "Warm water for drinking throughout the day",
            "Light Abhyanga with lukewarm sesame oil after fever breaks",
        ],
    },
    "headache": {
        "formulations": [
            "Pathyadi Kwatha — 30ml twice daily (classical Shiroroga remedy)",
            "Shirashooladi Vajra Rasa — 1 tab twice daily with honey",
            "Brahmi Ghrita — 1 tsp at bedtime (for recurring headache)",
        ],
        "therapies": [
            "Nasya with Anu Taila — 2 drops each nostril (morning, empty stomach)",
            "Shirodhara with medicated oil (for chronic/stress headache)",
            "Shiro Abhyanga (head massage) with Bhringaraj oil",
        ],
        "pathya_diet": [
            "Regular meal timing — avoid fasting",
            "Cooling foods for Pitta-type headache: milk, ghee, coconut water",
            "Warm, grounding foods for Vata-type: soups, stews, ghee",
            "Avoid excessive sour, spicy, and fermented foods",
        ],
        "dinacharya": [
            "Regular sleep schedule (10 PM–6 AM ideal)",
            "Pada Abhyanga (foot massage) with warm oil before sleep",
            "Pranayama: Nadi Shodhana (alternate nostril breathing) — 10 minutes",
        ],
    },
    "joint pain": {
        "formulations": [
            "Yogaraja Guggulu — 2 tablets twice daily after food",
            "Maharasnadi Kwatha — 30ml twice daily before food",
            "Ashwagandha Churna — 3g with warm milk at bedtime",
        ],
        "therapies": [
            "Abhyanga (oil massage) with Mahanarayana Taila — daily",
            "Janu Basti / Kati Basti (local oil pooling) for knee/back pain",
            "Patra Pinda Sweda (herbal bolus fomentation) — weekly sessions",
            "Basti therapy (medicated enema) for chronic Vata-type pain",
        ],
        "pathya_diet": [
            "Warm, unctuous foods: ghee, sesame oil, soups",
            "Anti-inflammatory spices: turmeric, ginger, garlic in cooking",
            "Avoid cold, dry, raw foods and excess bitter/astringent taste",
            "Warm milk with turmeric (Haldi Doodh) at bedtime",
        ],
        "dinacharya": [
            "Daily Abhyanga (self-oil massage) before bath",
            "Gentle yoga: Pawanmuktasana series for joint mobility",
            "Avoid cold exposure and excessive physical strain",
            "Warm sesame oil massage on affected joints",
        ],
    },
    "cough": {
        "formulations": [
            "Sitopaladi Churna — 3g with honey, thrice daily (Kapha-type cough)",
            "Vasaka (Adhatoda vasica) Swarasa — 10ml twice daily",
            "Kantakari + Yashtimadhu Kwatha — 30ml twice daily (dry cough)",
        ],
        "therapies": [
            "Vamana (therapeutic emesis) for chronic Kapha-type cough",
            "Steam inhalation with Ajwain (carom seeds) and Eucalyptus",
            "Pratishyaya Nasya — 2 drops each nostril with Anu Taila",
        ],
        "pathya_diet": [
            "Warm fluids: ginger-tulsi tea, turmeric milk",
            "Honey — 1 tsp with Sitopaladi Churna (best Kapha-liquefying agent)",
            "Avoid cold drinks, ice cream, yogurt, and banana",
            "Light, warm, freshly cooked meals",
        ],
        "dinacharya": [
            "Gargle with warm Turmeric + salt water — twice daily",
            "Pranayama: Kapalabhati (for productive cough) — 3 sets of 30",
            "Keep chest and throat warm; avoid cold drafts",
        ],
    },
    "stomach pain": {
        "formulations": [
            "Avipattikar Churna — 3g with warm water before meals",
            "Shankha Bhasma — 250mg with buttermilk after meals",
            "Hingvashtak Churna — 1g with first morsel of food",
        ],
        "therapies": [
            "Deepana-Pachana (digestive stimulation) therapy",
            "Virechana (therapeutic purgation) for Pitta-type pain",
            "Udara Abhyanga (abdominal massage) with warm castor oil",
        ],
        "pathya_diet": [
            "Small, frequent meals; eat at regular times",
            "Buttermilk (Takra) with roasted cumin and rock salt",
            "Khichdi (rice + moong dal) as therapeutic food",
            "Avoid heavy, fried, excessively spicy foods",
        ],
        "dinacharya": [
            "Eat meals at fixed times; lunch should be the largest meal",
            "Short walk (100 steps) after meals",
            "Avoid sleeping immediately after eating",
            "Vajrasana (thunderbolt pose) for 5 minutes after meals",
        ],
    },
    "acidity": {
        "formulations": [
            "Avipattikar Churna — 3-5g with warm water at bedtime",
            "Yashtimadhu (Licorice) Churna — 3g twice daily with milk",
            "Shatavari Churna — 3g with cool milk (Pitta pacification)",
            "Praval Pishti — 250mg twice daily (natural antacid)",
        ],
        "therapies": [
            "Virechana (mild purgation) with Trivrit Lehyam",
            "Pitta-shamaka Seka (cooling oil pouring)",
        ],
        "pathya_diet": [
            "Cooling foods: milk, ghee, coconut, pomegranate, amla",
            "Avoid sour, spicy, fermented, and fried foods",
            "Eat dinner before 7:30 PM; keep it light",
            "Drink Shatadhauta Ghrita (100-times washed ghee) — 1 tsp morning",
        ],
        "dinacharya": [
            "Avoid day sleep (increases Pitta)",
            "Sheetali Pranayama (cooling breath) — 10 minutes morning",
            "Moonlight exposure (Chandranshubheda) — Ayurvedic relaxation",
        ],
    },
    "back pain": {
        "formulations": [
            "Yogaraja Guggulu — 2 tabs twice daily after food",
            "Dashamoola Kwatha — 30ml twice daily",
            "Bala + Ashwagandha Churna — 3g with warm milk at bedtime",
        ],
        "therapies": [
            "Kati Basti — warm medicated oil pooling on lower back (30 min)",
            "Abhyanga with Dhanwantaram Taila — daily",
            "Pinda Sweda (herbal bolus fomentation) — weekly",
            "Basti (Anuvasana + Niruha) for chronic lumbar pain",
        ],
        "pathya_diet": [
            "Warm, nourishing foods with ghee",
            "Sesame seeds, garlic, ginger in daily cooking",
            "Avoid cold, raw, dry foods",
            "Warm milk with Ashwagandha at bedtime",
        ],
        "dinacharya": [
            "Gentle yoga: Cat-Cow, Bhujangasana, Shalabhasana",
            "Daily warm oil self-massage on back",
            "Avoid prolonged sitting; take breaks every 30 minutes",
            "Sleep on firm mattress; side-lying with pillow between knees",
        ],
    },
    "insomnia": {
        "formulations": [
            "Ashwagandha Churna — 3g with warm milk at bedtime",
            "Brahmi + Jatamansi Churna — 2g each at bedtime",
            "Saraswatarishta — 15ml with equal water after dinner",
        ],
        "therapies": [
            "Shirodhara (continuous oil pouring on forehead) — weekly",
            "Pada Abhyanga (foot massage) with Ksheerabala Taila — nightly",
            "Nasya with Brahmi Ghrita — 2 drops each nostril (morning)",
        ],
        "pathya_diet": [
            "Warm milk with cardamom, nutmeg, and ghee at bedtime",
            "Dinner should be light and before 7:30 PM",
            "Cherries, almonds, warm soups in evening",
            "Avoid caffeine, heavy meals, and stimulants after 4 PM",
        ],
        "dinacharya": [
            "Fixed sleep time (10 PM) — Kapha kala promotes sleep",
            "Dim lights 1 hour before bed; no screens",
            "Yoga Nidra or Shavasana meditation — 20 minutes before sleep",
            "Warm bath with Dashamool decoction before bedtime",
        ],
    },
    "anxiety": {
        "formulations": [
            "Brahmi (Bacopa monnieri) — 300mg twice daily (adaptogenic anxiolytic)",
            "Ashwagandha Churna — 3g in warm milk twice daily",
            "Manasamitra Vatakam — 1 tablet twice daily (classical Manas Roga remedy)",
            "Shankhapushpi Syrup — 10ml twice daily",
        ],
        "therapies": [
            "Shirodhara with Brahmi Taila — weekly (deeply calming)",
            "Abhyanga with Bala Taila — daily (grounding, Vata pacification)",
            "Nasya with Anu Taila (supports mental clarity)",
        ],
        "pathya_diet": [
            "Warm, grounding, Sattvic diet: milk, ghee, almonds, dates",
            "Regular meals at fixed times — never skip meals",
            "Avoid caffeine, alcohol, processed foods",
            "Golden milk (turmeric + ashwagandha + milk) at bedtime",
        ],
        "dinacharya": [
            "Morning Abhyanga (self-massage) — deeply grounding",
            "Pranayama: Nadi Shodhana (10 min) + Bhramari (5 min)",
            "Meditation: 20 minutes morning and evening",
            "Yoga: Viparita Karani, Balasana, Shavasana daily",
            "Nature walks and sunlight exposure",
        ],
    },
    "constipation": {
        "formulations": [
            "Triphala Churna — 5g with warm water at bedtime (best Vata laxative)",
            "Eranda (castor) oil — 1 tsp with warm milk at bedtime (Mridu Virechana)",
            "Abhayarishta — 15ml with equal water after meals",
        ],
        "therapies": [
            "Basti (medicated enema) — Anuvasana with sesame oil (chronic cases)",
            "Udara Abhyanga with warm castor oil — clockwise abdominal massage",
        ],
        "pathya_diet": [
            "High-fiber: papaya, figs, prunes, leafy greens, isabgol",
            "Warm water first thing in morning (Ushapana)",
            "Ghee — 1 tsp in warm milk at bedtime",
            "Avoid excess dry, cold, and astringent foods",
        ],
        "dinacharya": [
            "Wake early (Brahma Muhurta) — body's natural elimination time",
            "Pavanamuktasana, Malasana (garland pose) daily",
            "Warm water throughout the day; minimum 8 glasses",
            "Regular meal times; never suppress natural urges",
        ],
    },
    "diabetes": {
        "formulations": [
            "Gudmar (Gymnema sylvestre) — 400mg twice daily (reduces sugar cravings)",
            "Nisha Amalaki Churna (Turmeric + Amla) — 3g twice daily",
            "Jamun (Syzygium cumini) seed powder — 3g twice daily with water",
            "Chandraprabha Vati — 2 tablets twice daily",
        ],
        "therapies": [
            "Udvartana (herbal powder massage) — reduces Kapha and improves metabolism",
            "Yoga therapy protocol for diabetes management",
        ],
        "pathya_diet": [
            "Bitter vegetables: karela (bitter gourd), methi (fenugreek), neem leaves",
            "Whole grains: barley (Yava), foxtail millet, old rice",
            "Avoid: sweet, heavy, oily foods; white rice; sugarcane; jaggery",
            "Triphala water — soak overnight, drink morning",
        ],
        "dinacharya": [
            "Brisk morning walk — 30-45 minutes daily",
            "Yoga: Surya Namaskar, Mandukasana, Ardha Matsyendrasana",
            "Pranayama: Kapalabhati (20 min) + Bhastrika",
            "Avoid daytime sleep (increases Kapha)",
        ],
    },
    "hypertension": {
        "formulations": [
            "Sarpagandha (Rauwolfia) Vati — 1 tab twice daily (classical antihypertensive)",
            "Arjuna (Terminalia arjuna) Ksheerapaka — bark boiled in milk, 100ml daily",
            "Brahmi Churna — 3g twice daily (stress-related HTN)",
            "Jatamansi Churna — 1g at bedtime (calming, mild hypotensive)",
        ],
        "therapies": [
            "Shirodhara with Brahmi Taila — weekly (reduces stress response)",
            "Takra Dhara (buttermilk pouring on forehead) — cooling",
            "Foot massage with warm ghee before sleep",
        ],
        "pathya_diet": [
            "Low-sodium: avoid pickles, papad, processed foods",
            "Cooling foods: lauki (bottle gourd) juice, coconut water, pomegranate",
            "Garlic — 2 cloves on empty stomach daily (mild antihypertensive)",
            "Avoid: excess salt, fried foods, anger-inducing stimulants",
        ],
        "dinacharya": [
            "Pranayama: Nadi Shodhana + Sheetali — 15 minutes morning",
            "Meditation: Yoga Nidra or guided relaxation — 20 minutes",
            "Avoid excessive anger, argument, and competitive stress",
            "Walk in nature — 30 minutes in early morning or evening",
        ],
    },
    "cold": {
        "formulations": [
            "Trikatu Churna (Ginger+Pepper+Pippali) — 2g with honey, thrice daily",
            "Tulsi Kwatha — fresh tulsi leaves boiled in water, 100ml twice daily",
            "Lakshmi Vilas Ras — 1 tab twice daily with honey",
        ],
        "therapies": [
            "Nasya with Anu Taila — 2 drops each nostril morning",
            "Steam inhalation with Nilgiri (Eucalyptus) oil",
            "Dhoomapana (herbal smoking) with Haridra and Vacha — classical",
        ],
        "pathya_diet": [
            "Warm soups with Pepper, Ginger, and Tulsi",
            "Avoid cold foods, yogurt, banana, ice cream",
            "Honey — 1 tsp with Black Pepper powder (Kapha liquefying)",
            "Warm water throughout the day",
        ],
        "dinacharya": [
            "Steam inhalation morning and evening",
            "Gargle with warm Turmeric + salt water",
            "Avoid cold drafts; keep head and chest warm",
            "Rest and avoid strenuous activity",
        ],
    },
    "fatigue": {
        "formulations": [
            "Ashwagandha Churna — 3g with warm milk twice daily (Rasayana)",
            "Chyawanprash — 1 tablespoon morning with warm milk",
            "Shatavari Churna — 3g with milk (especially for women)",
        ],
        "therapies": [
            "Abhyanga with Bala Taila — daily full-body oil massage",
            "Rasayana therapy (rejuvenation protocol)",
        ],
        "pathya_diet": [
            "Nourishing Rasayana foods: milk, ghee, almonds, dates, saffron",
            "Regular meals — never skip; lunch should be heaviest",
            "Avoid excessive fasting, processed foods, stale food",
            "Fresh fruit juices: pomegranate, grape, amla",
        ],
        "dinacharya": [
            "Adequate sleep: 7-8 hours, fixed schedule",
            "Gentle yoga: Surya Namaskar (slow pace), Shavasana",
            "Morning sunlight exposure — 15 minutes",
            "Reduce overwork and mental stress",
        ],
    },
}

# Generic Ayurvedic fallback
GENERIC_AYURVEDA: dict = {
    "formulations": [
        "Triphala Churna — 3g at bedtime (general health maintenance)",
        "Chyawanprash — 1 tbsp morning (Rasayana — rejuvenation)",
        "Consult qualified Ayurvedic Vaidya (BAMS) for specific formulations",
    ],
    "therapies": [
        "Abhyanga (oil massage) — daily self-massage with suitable oil",
        "Dinacharya (daily routine) alignment for overall wellness",
    ],
    "pathya_diet": [
        "Eat freshly cooked, warm, Sattvic food",
        "Eat according to Agni (digestive fire) capacity",
        "Include all six tastes (Shadrasa) in meals",
        "Warm water throughout the day",
    ],
    "dinacharya": [
        "Wake at Brahma Muhurta (~5:30 AM)",
        "Daily self-massage (Abhyanga) before bath",
        "Yoga and Pranayama — 30 minutes daily",
        "Fixed meal and sleep timings",
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  MAIN AYURVEDA SPECIALIST FUNCTION
# ═══════════════════════════════════════════════════════════════════

def generate_ayurveda_plan(
    intake: PatientIntake,
    symptom_objects: list[SymptomObject],
    risk_level: RiskLevel,
    is_primary: bool = False,
) -> tuple[PlanSegment, DoshaType, dict[str, float], AgentTrace]:
    """
    Generate dosha-aligned Ayurvedic treatment plan.

    Args:
        intake: Patient intake data.
        symptom_objects: Normalized symptoms.
        risk_level: Triage risk level.
        is_primary: Whether ayurveda is the primary modality.

    Returns:
        (plan_segment, dominant_dosha, dosha_scores, agent_trace)
    """
    started_at = datetime.utcnow()

    # Step 1: Assess dosha imbalance
    dominant_dosha, dosha_scores, dosha_assessment = _assess_dominant_dosha(
        symptom_objects, intake.age, intake.sex
    )

    # Step 2: Gather recommendations for each symptom
    all_recommendations: list[str] = []
    all_medications: list[str] = []
    all_lifestyle: list[str] = []
    all_evidence: list[EvidenceSource] = []
    seen: set[str] = set()

    # Add dosha assessment as first recommendation
    all_recommendations.append(f"🔬 {dosha_assessment}")

    for symptom in symptom_objects:
        treatment = AYURVEDA_TREATMENTS.get(symptom.name, GENERIC_AYURVEDA)

        # Formulations → medications
        for form in treatment.get("formulations", []):
            if form not in seen:
                all_medications.append(form)
                seen.add(form)

        # Therapies → recommendations
        for therapy in treatment.get("therapies", []):
            if therapy not in seen:
                all_recommendations.append(therapy)
                seen.add(therapy)

        # Pathya diet → lifestyle
        for diet_item in treatment.get("pathya_diet", []):
            if diet_item not in seen:
                all_lifestyle.append(f"🍽️ {diet_item}")
                seen.add(diet_item)

        # Dinacharya → lifestyle
        for dina in treatment.get("dinacharya", []):
            if dina not in seen:
                all_lifestyle.append(f"🌅 {dina}")
                seen.add(dina)

        # Evidence
        evidence = get_evidence_for_condition(symptom.name, "ayurveda")
        all_evidence.extend(evidence)

    # Step 3: Add dosha-specific general advice
    dosha_general = _get_dosha_specific_advice(dominant_dosha)
    all_recommendations.extend(dosha_general)

    # Step 4: Safety note for integrative use
    if not is_primary:
        all_recommendations.append(
            "⚠️ Ayurvedic recommendations are COMPLEMENTARY to allopathic "
            "treatment. Inform your allopathic physician about all herbal "
            "formulations. Do not replace prescribed medications without "
            "medical consultation."
        )

    # Step 5: Calculate confidence
    confidence = min(
        0.90,
        0.50 + (len(all_evidence) * 0.05) + (len(symptom_objects) * 0.03),
    )

    # Build title
    symptom_names = [s.name for s in symptom_objects[:3]]
    title = (
        f"Ayurvedic Care Plan ({dominant_dosha.value.title()} Dosha Focus) "
        f"— {', '.join(symptom_names)}"
    )

    # Follow-up
    follow_up = (
        "Review with Ayurvedic Vaidya in 2 weeks. "
        "Panchakarma consultation recommended for chronic conditions. "
        "Report any adverse reactions from herbal formulations immediately."
    )

    plan = PlanSegment(
        modality=Modality.AYURVEDA,
        title=title,
        recommendations=all_recommendations,
        medications=all_medications,
        lifestyle=all_lifestyle,
        follow_up=follow_up,
        evidence=all_evidence,
        priority_label="primary" if is_primary else "complementary",
        confidence=round(confidence, 2),
    )

    completed_at = datetime.utcnow()
    trace = AgentTrace(
        agent_name=AgentName.AYURVEDA,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=f"{len(symptom_objects)} symptoms, "
                      f"dosha={dominant_dosha.value}",
        output_summary=f"{len(all_recommendations)} recs, "
                       f"{len(all_medications)} formulations, "
                       f"dosha={dominant_dosha.value} "
                       f"({dosha_scores})",
    )

    return plan, dominant_dosha, dosha_scores, trace


def _get_dosha_specific_advice(dosha: DoshaType) -> list[str]:
    """General dosha-balancing advice."""
    advice_map: dict[str, list[str]] = {
        "vata": [
            "Vata Shamana: Favor warm, moist, grounding foods (soups, stews, ghee)",
            "Vata Shamana: Regular daily routine (Dinacharya) is essential",
            "Vata Shamana: Warm sesame oil Abhyanga (self-massage) daily",
            "Vata Shamana: Avoid cold, dry, raw foods and irregular schedules",
        ],
        "pitta": [
            "Pitta Shamana: Favor cooling, sweet, bitter foods (milk, ghee, coconut)",
            "Pitta Shamana: Avoid excessive heat, spicy food, and anger",
            "Pitta Shamana: Moonlight walks, cooling Pranayama (Sheetali)",
            "Pitta Shamana: Coconut oil or Brahmi oil for head massage",
        ],
        "kapha": [
            "Kapha Shamana: Favor warm, light, dry foods with pungent/bitter taste",
            "Kapha Shamana: Regular vigorous exercise — morning is best",
            "Kapha Shamana: Avoid cold, heavy, oily foods and daytime sleep",
            "Kapha Shamana: Dry herbal powder massage (Udvartana) recommended",
        ],
    }

    dosha_key = dosha.value.split("-")[0]  # Use first dosha for compound
    return advice_map.get(dosha_key, advice_map["vata"])
