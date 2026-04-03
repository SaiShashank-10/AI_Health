"""
Safety Rule Engine — emergency detection, herb-drug interactions,
and Ayurvedic contraindication checking.

Each rule has:  Rule ID → Trigger → Condition → Action

Rules are evaluated against patient intake and plan segments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.schemas.common import RiskLevel, Modality, Warning


# ═══════════════════════════════════════════════════════════════════
#  RULE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SafetyRule:
    """A declarative safety rule."""
    rule_id: str
    category: str          # "emergency", "herb_drug", "ayurvedic_contra", "general"
    trigger_keywords: list[str]
    condition_fn_name: str  # name of the condition check function
    severity: str          # "high", "medium", "low"
    action_message: str
    resolution: Optional[str] = None
    affected_modalities: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
#  EMERGENCY KEYWORDS
# ═══════════════════════════════════════════════════════════════════

EMERGENCY_KEYWORDS: list[list[str]] = [
    # Each sub-list is a group — any keyword in the group triggers
    ["chest pain", "seene mein dard", "sine mein dard", "छाती में दर्द",
     "sीने में दर्द", "நெஞ்சு வலி", "ఛాతీ నొప్పి"],
    ["difficulty breathing", "breathing difficulty", "breathlessness",
     "sans phoolna", "saans phulna", "श्वास", "dyspnea"],
    ["stroke", "paralysis", "facial drooping", "speech slurred",
     "sudden numbness"],
    ["severe bleeding", "bleeding profusely", "hemorrhage"],
    ["unconscious", "unresponsive", "fainting", "loss of consciousness",
     "behosh"],
    ["seizure", "convulsion", "fits", "mirgi"],
    ["severe allergic reaction", "anaphylaxis", "swollen throat",
     "can't breathe"],
    ["diaphoresis", "profuse sweating", "cold sweat"],
    ["suicidal", "self harm", "want to die", "suicide"],
]

EMERGENCY_SYMPTOM_PAIRS: list[dict] = [
    # Combinations that escalate to emergent
    {
        "symptoms": ["chest pain", "sweating"],
        "min_age": 30,
        "note": "Possible acute coronary syndrome",
    },
    {
        "symptoms": ["chest pain", "breathlessness"],
        "min_age": 25,
        "note": "Cardiac or pulmonary emergency",
    },
    {
        "symptoms": ["headache", "vomiting", "vision"],
        "min_age": 0,
        "note": "Possible raised intracranial pressure",
    },
    {
        "symptoms": ["fever", "rash", "neck stiffness"],
        "min_age": 0,
        "note": "Possible meningitis",
    },
]


# ═══════════════════════════════════════════════════════════════════
#  HERB-DRUG INTERACTIONS DATABASE
# ═══════════════════════════════════════════════════════════════════

HERB_DRUG_INTERACTIONS: list[dict] = [
    {
        "rule_id": "R_HERB_DRUG_01",
        "herb": "st. john's wort",
        "herb_aliases": ["st john's wort", "hypericum", "st johns wort"],
        "drug_class": "SSRI",
        "drug_names": ["fluoxetine", "sertraline", "paroxetine", "citalopram",
                       "escitalopram", "fluvoxamine"],
        "severity": "high",
        "warning": "St. John's Wort combined with SSRIs can cause serotonin "
                   "syndrome — a potentially life-threatening condition. "
                   "Symptoms include agitation, confusion, rapid heart rate, "
                   "and high blood pressure.",
        "resolution": "Discontinue St. John's Wort. Consult a psychiatrist "
                      "before any herbal supplementation with SSRIs.",
    },
    {
        "rule_id": "R_HERB_DRUG_02",
        "herb": "ginkgo biloba",
        "herb_aliases": ["ginkgo", "ginkgo leaf"],
        "drug_class": "anticoagulant",
        "drug_names": ["warfarin", "heparin", "aspirin", "clopidogrel",
                       "rivaroxaban", "apixaban"],
        "severity": "high",
        "warning": "Ginkgo Biloba may increase bleeding risk when taken "
                   "with anticoagulants or antiplatelet drugs.",
        "resolution": "Avoid Ginkgo if on blood thinners. Monitor INR closely.",
    },
    {
        "rule_id": "R_HERB_DRUG_03",
        "herb": "ashwagandha",
        "herb_aliases": ["withania somnifera", "indian ginseng"],
        "drug_class": "thyroid_medication",
        "drug_names": ["levothyroxine", "liothyronine", "thyroxine",
                       "thyronorm", "eltroxin"],
        "severity": "medium",
        "warning": "Ashwagandha may increase thyroid hormone levels. "
                   "Combined with thyroid medications, this could lead "
                   "to hyperthyroidism symptoms.",
        "resolution": "Monitor thyroid function tests regularly. "
                      "Adjust thyroid medication dose under physician guidance.",
    },
    {
        "rule_id": "R_HERB_DRUG_04",
        "herb": "turmeric",
        "herb_aliases": ["curcumin", "haldi"],
        "drug_class": "anticoagulant",
        "drug_names": ["warfarin", "aspirin", "clopidogrel"],
        "severity": "medium",
        "warning": "High-dose turmeric/curcumin supplements may enhance "
                   "anticoagulant effects and increase bleeding risk.",
        "resolution": "Dietary turmeric is generally safe. Avoid concentrated "
                      "curcumin supplements if on blood thinners.",
    },
    {
        "rule_id": "R_HERB_DRUG_05",
        "herb": "licorice",
        "herb_aliases": ["mulethi", "yashtimadhu", "glycyrrhiza"],
        "drug_class": "antihypertensive",
        "drug_names": ["amlodipine", "losartan", "enalapril", "telmisartan",
                       "ramipril", "atenolol", "metoprolol"],
        "severity": "high",
        "warning": "Licorice (Mulethi) can raise blood pressure and "
                   "counteract antihypertensive medications. Can also "
                   "cause hypokalemia.",
        "resolution": "Avoid licorice if on blood pressure medications. "
                      "Use alternative soothing herbs like chamomile.",
    },
    {
        "rule_id": "R_HERB_DRUG_06",
        "herb": "garlic supplement",
        "herb_aliases": ["allium sativum", "garlic extract"],
        "drug_class": "anticoagulant",
        "drug_names": ["warfarin", "aspirin", "clopidogrel"],
        "severity": "medium",
        "warning": "Concentrated garlic supplements may increase bleeding "
                   "risk when combined with anticoagulants.",
        "resolution": "Dietary garlic in food is generally safe. "
                      "Avoid high-dose garlic supplements.",
    },
]


# ═══════════════════════════════════════════════════════════════════
#  AYURVEDIC CONTRAINDICATIONS
# ═══════════════════════════════════════════════════════════════════

AYURVEDIC_CONTRAINDICATIONS: list[dict] = [
    {
        "rule_id": "R_AYURV_CONTRA_01",
        "condition": "hypertension",
        "condition_aliases": ["high blood pressure", "high bp", "hbp"],
        "contraindicated_herbs": ["trikatu", "black pepper", "dry ginger",
                                   "long pepper", "pippali", "marich"],
        "category": "warming herbs",
        "severity": "medium",
        "warning": "Warming herbs (Trikatu, Marich) can elevate blood "
                   "pressure. Contraindicated in hypertensive patients.",
        "resolution": "Use cooling alternatives: Brahmi, Shankhapushpi, "
                      "or Arjuna for cardiac support.",
        "alternatives": ["brahmi", "shankhapushpi", "arjuna", "sarpagandha"],
    },
    {
        "rule_id": "R_AYURV_CONTRA_02",
        "condition": "pregnancy",
        "condition_aliases": ["pregnant", "expecting"],
        "contraindicated_herbs": ["shatavari high dose", "aloe vera internal",
                                   "kalonji oil", "papaya seeds", "fenugreek high dose"],
        "category": "uterine stimulants",
        "severity": "high",
        "warning": "Certain Ayurvedic herbs can cause uterine contractions "
                   "and are unsafe during pregnancy.",
        "resolution": "Use only pregnancy-safe herbs under qualified "
                      "Ayurvedic practitioner's supervision.",
        "alternatives": [],
    },
    {
        "rule_id": "R_AYURV_CONTRA_03",
        "condition": "diabetes",
        "condition_aliases": ["diabetic", "blood sugar", "sugar patient"],
        "contraindicated_herbs": [],
        "category": "blood sugar interactions",
        "severity": "medium",
        "warning": "Some Ayurvedic formulations for diabetes (e.g., Gudmar, "
                   "Karela) can cause hypoglycemia when combined with "
                   "oral hypoglycemics or insulin.",
        "resolution": "Monitor blood sugar closely. Adjust allopathic "
                      "dosage under physician supervision when adding "
                      "Ayurvedic diabetes formulations.",
        "alternatives": [],
    },
    {
        "rule_id": "R_AYURV_CONTRA_04",
        "condition": "kidney disease",
        "condition_aliases": ["renal failure", "ckd", "kidney problem"],
        "contraindicated_herbs": ["punarnava high dose", "gokshura high dose",
                                   "heavy metal containing formulations"],
        "category": "nephrotoxic risk",
        "severity": "high",
        "warning": "Some Ayurvedic bhasmas (metallic preparations) and "
                   "high-dose herbs can stress compromised kidneys.",
        "resolution": "Avoid Rasa Shastra (metallic) preparations. "
                      "Use only plant-based formulations with renal clearance.",
        "alternatives": [],
    },
]


# ═══════════════════════════════════════════════════════════════════
#  CROSS-MODALITY CONFLICT RULES
# ═══════════════════════════════════════════════════════════════════

CROSS_MODALITY_CONFLICTS: list[dict] = [
    {
        "rule_id": "R_CROSS_01",
        "modality_a": "allopathy",
        "modality_b": "ayurveda",
        "drug_a_keywords": ["steroids", "prednisone", "prednisolone",
                            "dexamethasone", "corticosteroid"],
        "drug_b_keywords": ["ashwagandha", "guduchi", "immunomodulator",
                            "rasayana"],
        "severity": "medium",
        "warning": "Immunosuppressive steroids (allopathic) combined with "
                   "immunomodulatory Rasayanas (Ayurvedic) may create "
                   "unpredictable immune responses.",
        "resolution": "Stagger administration. Consult both practitioners. "
                      "Use Ayurvedic herbs only after steroid taper.",
    },
    {
        "rule_id": "R_CROSS_02",
        "modality_a": "allopathy",
        "modality_b": "ayurveda",
        "drug_a_keywords": ["metformin", "glimepiride", "insulin",
                            "oral hypoglycemic"],
        "drug_b_keywords": ["gudmar", "gymnema", "karela", "bitter gourd",
                            "fenugreek", "jamun"],
        "severity": "medium",
        "warning": "Combining allopathic diabetes drugs with Ayurvedic "
                   "hypoglycemic herbs may cause dangerous hypoglycemia.",
        "resolution": "Start Ayurvedic herbs at low dose. Monitor blood "
                      "sugar 4 times daily for 2 weeks. Adjust allopathic "
                      "dose under physician guidance.",
    },
]


# ═══════════════════════════════════════════════════════════════════
#  SAFETY ENGINE — EVALUATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def check_emergency_keywords(symptom_text: str) -> list[Warning]:
    """
    Scan symptom text for emergency-level keywords.
    Returns warnings for any detected emergency patterns.
    """
    warnings: list[Warning] = []
    text_lower = symptom_text.lower()

    for keyword_group in EMERGENCY_KEYWORDS:
        for keyword in keyword_group:
            if keyword.lower() in text_lower:
                warnings.append(Warning(
                    rule_id="R_EMERG_01",
                    severity="high",
                    message=f"Emergency keyword detected: '{keyword}'. "
                            f"Immediate medical attention may be required.",
                    affected_modalities=[Modality.ALLOPATHY],
                    resolution="Override to allopathy-only pathway. "
                               "Recommend immediate emergency department visit.",
                ))
                return warnings  # One emergency warning is enough

    return warnings


def check_emergency_combinations(
    symptom_terms: list[str], age: int
) -> list[Warning]:
    """
    Check for dangerous symptom combinations that require escalation.
    """
    warnings: list[Warning] = []
    terms_lower = [t.lower() for t in symptom_terms]

    for pair in EMERGENCY_SYMPTOM_PAIRS:
        required = pair["symptoms"]
        min_age = pair.get("min_age", 0)

        # Check if all required symptoms are present
        matches = sum(
            1 for req in required
            if any(req in term for term in terms_lower)
        )

        if matches >= len(required) and age >= min_age:
            warnings.append(Warning(
                rule_id="R_EMERG_COMBO",
                severity="high",
                message=f"{pair['note']}. Detected symptoms: "
                        f"{', '.join(required)} in patient age {age}.",
                affected_modalities=[Modality.ALLOPATHY],
                resolution="Escalate to emergent. Allopathy-only pathway. "
                           "Recommend immediate medical evaluation.",
            ))

    return warnings


def check_herb_drug_interactions(
    medications: list[str],
    recommended_herbs: list[str] | None = None,
    plan_text: str = "",
) -> list[Warning]:
    """
    Check for dangerous herb-drug interactions.
    Scans patient's current medications against known interaction database.
    """
    warnings: list[Warning] = []
    meds_lower = [m.lower() for m in medications]
    herbs_text = " ".join(recommended_herbs or []).lower() + " " + plan_text.lower()

    for interaction in HERB_DRUG_INTERACTIONS:
        # Check if patient is on any of the interacting drugs
        drug_match = any(
            drug in med
            for drug in interaction["drug_names"]
            for med in meds_lower
        )

        if not drug_match:
            continue

        # Check if the interacting herb is being recommended
        herb_names = [interaction["herb"]] + interaction.get("herb_aliases", [])
        herb_match = any(h.lower() in herbs_text for h in herb_names)

        if herb_match:
            warnings.append(Warning(
                rule_id=interaction["rule_id"],
                severity=interaction["severity"],
                message=interaction["warning"],
                affected_modalities=[Modality.AYURVEDA],
                resolution=interaction["resolution"],
            ))

    return warnings


def check_ayurvedic_contraindications(
    comorbidities: list[str],
    recommended_herbs: list[str] | None = None,
    plan_text: str = "",
) -> tuple[list[Warning], list[str]]:
    """
    Check for Ayurvedic herb contraindications based on patient conditions.
    Returns (warnings, alternative_herb_suggestions).
    """
    warnings: list[Warning] = []
    alternatives: list[str] = []
    conditions_lower = [c.lower() for c in comorbidities]
    herbs_text = " ".join(recommended_herbs or []).lower() + " " + plan_text.lower()

    for contra in AYURVEDIC_CONTRAINDICATIONS:
        # Check if patient has the contraindicated condition
        all_condition_names = [contra["condition"]] + contra.get("condition_aliases", [])
        condition_match = any(
            cond_name in cond
            for cond_name in all_condition_names
            for cond in conditions_lower
        )

        if not condition_match:
            continue

        # Check if any contraindicated herbs are in the plan
        contra_herbs = contra.get("contraindicated_herbs", [])
        herb_found = any(h.lower() in herbs_text for h in contra_herbs) if contra_herbs else True

        if herb_found or not contra_herbs:
            warnings.append(Warning(
                rule_id=contra["rule_id"],
                severity=contra["severity"],
                message=contra["warning"],
                affected_modalities=[Modality.AYURVEDA],
                resolution=contra["resolution"],
            ))
            alternatives.extend(contra.get("alternatives", []))

    return warnings, alternatives


def check_cross_modality_conflicts(
    plan_segments_text: dict[str, str],
    medications: list[str],
) -> list[Warning]:
    """
    Check for conflicts between different modality recommendations.
    plan_segments_text: { "allopathy": "full text...", "ayurveda": "full text..." }
    """
    warnings: list[Warning] = []

    all_text = " ".join(plan_segments_text.values()).lower()
    all_text += " " + " ".join(medications).lower()

    for conflict in CROSS_MODALITY_CONFLICTS:
        a_match = any(kw in all_text for kw in conflict["drug_a_keywords"])
        b_match = any(kw in all_text for kw in conflict["drug_b_keywords"])

        if a_match and b_match:
            warnings.append(Warning(
                rule_id=conflict["rule_id"],
                severity=conflict["severity"],
                message=conflict["warning"],
                affected_modalities=[
                    Modality(conflict["modality_a"]),
                    Modality(conflict["modality_b"]),
                ],
                resolution=conflict["resolution"],
            ))

    return warnings


def run_all_safety_checks(
    symptom_text: str,
    symptom_terms: list[str],
    age: int,
    medications: list[str],
    comorbidities: list[str],
    recommended_herbs: list[str] | None = None,
    plan_segments_text: dict[str, str] | None = None,
) -> list[Warning]:
    """
    Run the complete safety check suite.
    Returns all triggered warnings, sorted by severity.
    """
    all_warnings: list[Warning] = []

    # 1. Emergency keyword check
    all_warnings.extend(check_emergency_keywords(symptom_text))

    # 2. Emergency combination check
    all_warnings.extend(check_emergency_combinations(symptom_terms, age))

    # 3. Herb-drug interactions
    plan_text = " ".join((plan_segments_text or {}).values())
    all_warnings.extend(
        check_herb_drug_interactions(medications, recommended_herbs, plan_text)
    )

    # 4. Ayurvedic contraindications
    ayurv_warnings, _ = check_ayurvedic_contraindications(
        comorbidities, recommended_herbs, plan_text
    )
    all_warnings.extend(ayurv_warnings)

    # 5. Cross-modality conflicts
    if plan_segments_text:
        all_warnings.extend(
            check_cross_modality_conflicts(plan_segments_text, medications)
        )

    # Sort by severity: high > medium > low
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_warnings.sort(key=lambda w: severity_order.get(w.severity, 3))

    # Deduplicate by rule_id
    seen: set[str] = set()
    unique: list[Warning] = []
    for w in all_warnings:
        if w.rule_id not in seen:
            seen.add(w.rule_id)
            unique.append(w)

    return unique
