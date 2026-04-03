"""
Evidence & Provenance Store — simulated knowledge base of medical guidelines,
AYUSH pharmacopeia references, and peer-reviewed sources.

Each recommendation cites evidence with a reliability tier:
  A = RCT / meta-analysis
  B = Observational study
  T = Traditional textual reference
  Caution = Conflicting or insufficient evidence
"""
from __future__ import annotations

from backend.schemas.common import EvidenceSource, ReliabilityTier


# ═══════════════════════════════════════════════════════════════════
#  ALLOPATHIC EVIDENCE BASE
# ═══════════════════════════════════════════════════════════════════

ALLOPATHY_EVIDENCE: dict[str, list[EvidenceSource]] = {
    "fever": [
        EvidenceSource(
            title="WHO Guidelines on Management of Fever in Primary Care",
            source_type="WHO Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="WHO/UHL/2023.01",
            year=2023,
            summary="Paracetamol 500-1000mg every 4-6 hours as first-line "
                    "antipyretic. Avoid aspirin in children under 16.",
        ),
        EvidenceSource(
            title="ICMR National Guidelines for Fever Management",
            source_type="ICMR Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="ICMR/FEV/2022",
            year=2022,
            summary="Stepwise approach: hydration → paracetamol → "
                    "investigation if fever >3 days or >39°C.",
        ),
    ],
    "headache": [
        EvidenceSource(
            title="NICE Clinical Guideline: Headaches in Over 12s",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="NICE-CG150",
            year=2021,
            summary="Ibuprofen or paracetamol for tension-type headache. "
                    "Triptans for confirmed migraine. Red flags: "
                    "thunderclap, fever+neck stiffness, neurological deficit.",
        ),
    ],
    "hypertension": [
        EvidenceSource(
            title="ACC/AHA 2017 Guideline for High Blood Pressure in Adults",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="DOI:10.1161/HYP.0000000000000065",
            year=2017,
            summary="Stage 1 HTN: lifestyle modification ± single agent. "
                    "Stage 2: combination therapy. Target <130/80 mmHg.",
        ),
        EvidenceSource(
            title="Indian Guidelines on Hypertension (IGH-IV)",
            source_type="National Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="JAPI/2019/HTN",
            year=2019,
            summary="India-specific thresholds. ARBs or CCBs preferred "
                    "first line. DASH diet + salt restriction <5g/day.",
        ),
    ],
    "diabetes": [
        EvidenceSource(
            title="ADA Standards of Medical Care in Diabetes",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="DOI:10.2337/dc23-SINT",
            year=2023,
            summary="Metformin first-line for T2DM. SGLT2 inhibitors for "
                    "cardiorenal benefit. HbA1c target <7% for most adults.",
        ),
        EvidenceSource(
            title="RSSDI Clinical Practice Recommendations for T2DM",
            source_type="Indian Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="RSSDI/2022/CPR",
            year=2022,
            summary="India-specific: consider ethnic predisposition. "
                    "Metformin + lifestyle first. Add DPP4i or SGLT2i early.",
        ),
    ],
    "cough": [
        EvidenceSource(
            title="BTS Guidelines for Management of Cough in Adults",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="Thorax/2006/61/Suppl_1",
            year=2020,
            summary="Acute cough (<3 weeks): usually viral, supportive care. "
                    "Chronic cough: investigate GERD, asthma, post-nasal drip.",
        ),
    ],
    "acidity": [
        EvidenceSource(
            title="ACG Clinical Guideline: GERD Management",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="ACG/GERD/2022",
            year=2022,
            summary="Lifestyle modifications first. PPIs for erosive disease. "
                    "H2 blockers for mild symptoms. 8-week PPI trial standard.",
        ),
    ],
    "joint pain": [
        EvidenceSource(
            title="EULAR Recommendations for OA Management",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="ARD/2019/78/16",
            year=2019,
            summary="Exercise + weight management core. Topical NSAIDs first. "
                    "Oral NSAIDs lowest effective dose, shortest duration.",
        ),
    ],
    "urinary tract infection": [
        EvidenceSource(
            title="IDSA Guidelines for Uncomplicated UTI",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="CID/2011/52/5",
            year=2019,
            summary="Nitrofurantoin 5 days or TMP-SMX 3 days first line. "
                    "Fosfomycin single dose alternative. Avoid fluoroquinolones.",
        ),
    ],
    "skin infection": [
        EvidenceSource(
            title="IDSA Practice Guidelines for Skin Infections",
            source_type="Clinical Guideline",
            reliability_tier=ReliabilityTier.A,
            reference_id="CID/2014/59/2",
            year=2014,
            summary="Mild: topical mupirocin. Moderate: oral cephalexin or "
                    "clindamycin. Severe/abscess: I&D + culture.",
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  AYURVEDIC EVIDENCE BASE
# ═══════════════════════════════════════════════════════════════════

AYURVEDA_EVIDENCE: dict[str, list[EvidenceSource]] = {
    "fever": [
        EvidenceSource(
            title="Charaka Samhita — Jwara Chikitsa (Fever Treatment)",
            source_type="Classical Ayurvedic Text",
            reliability_tier=ReliabilityTier.T,
            reference_id="CS/Chi/3",
            year=None,
            summary="Langhana (fasting) + Pachana (digestive herbs) in early "
                    "fever. Guduchi (Tinospora cordifolia) as primary anti-pyretic. "
                    "Avoid heavy food during jwara.",
        ),
        EvidenceSource(
            title="AYUSH Protocol for Fever Management",
            source_type="AYUSH Guideline",
            reliability_tier=ReliabilityTier.B,
            reference_id="AYUSH/FEV/2021",
            year=2021,
            summary="Sudarshana Churna for intermittent fever. "
                    "Tulsi + Ginger decoction for viral fever. "
                    "CCRAS validated formulation.",
        ),
    ],
    "headache": [
        EvidenceSource(
            title="Ashtanga Hridaya — Shiroroga Chikitsa",
            source_type="Classical Ayurvedic Text",
            reliability_tier=ReliabilityTier.T,
            reference_id="AH/Utt/23",
            year=None,
            summary="Classify headache by dosha: Vata (throbbing), "
                    "Pitta (burning), Kapha (dull, heavy). "
                    "Nasya therapy with Anu Taila for chronic headache.",
        ),
    ],
    "joint pain": [
        EvidenceSource(
            title="CCRAS Clinical Study: Yogaraja Guggulu in OA",
            source_type="CCRAS Research",
            reliability_tier=ReliabilityTier.B,
            reference_id="CCRAS/OA/2020",
            year=2020,
            summary="Yogaraja Guggulu showed significant improvement in "
                    "joint pain and morning stiffness in 60-patient RCT. "
                    "Effect comparable to diclofenac at 8 weeks.",
        ),
        EvidenceSource(
            title="Charaka Samhita — Vatavyadhi Chikitsa",
            source_type="Classical Ayurvedic Text",
            reliability_tier=ReliabilityTier.T,
            reference_id="CS/Chi/28",
            year=None,
            summary="Abhyanga (oil massage) with Mahanarayana Taila. "
                    "Bala + Ashwagandha for Vata-type pain. "
                    "Panchakarma: Basti therapy for chronic cases.",
        ),
    ],
    "acidity": [
        EvidenceSource(
            title="Ayurvedic Management of Amlapitta (Hyperacidity)",
            source_type="AYUSH Pharmacopeia",
            reliability_tier=ReliabilityTier.T,
            reference_id="API/Vol-6/Amlapitta",
            year=None,
            summary="Avipattikar Churna as primary formulation. "
                    "Yashtimadhu (Licorice) for mucosal protection. "
                    "Shatavari for Pitta pacification.",
        ),
    ],
    "cough": [
        EvidenceSource(
            title="AYUSH Advisory: Ayurvedic Management of Kasa (Cough)",
            source_type="AYUSH Guideline",
            reliability_tier=ReliabilityTier.B,
            reference_id="AYUSH/KASA/2020",
            year=2020,
            summary="Sitopaladi Churna for productive cough. "
                    "Vasaka (Adhatoda) syrup for bronchitis. "
                    "Honey + Tulsi for dry cough.",
        ),
    ],
    "diabetes": [
        EvidenceSource(
            title="CCRAS Study: Ayurvedic Management of Prameha (Diabetes)",
            source_type="CCRAS Research",
            reliability_tier=ReliabilityTier.B,
            reference_id="CCRAS/DM/2019",
            year=2019,
            summary="Gudmar (Gymnema sylvestre) + Jamun (Syzygium cumini) "
                    "showed adjunctive benefit in T2DM. Reduce HbA1c by "
                    "0.5-0.8% as add-on therapy.",
        ),
    ],
    "hypertension": [
        EvidenceSource(
            title="Ayurvedic Approach to Rakta Vata (Hypertension)",
            source_type="Classical Ayurvedic Text",
            reliability_tier=ReliabilityTier.T,
            reference_id="CS/Chi/RaktaVata",
            year=None,
            summary="Sarpagandha (Rauwolfia serpentina) as classical "
                    "antihypertensive. Arjuna bark for cardioprotection. "
                    "Brahmi for stress-related HTN.",
        ),
    ],
    "insomnia": [
        EvidenceSource(
            title="Ayurvedic Nidra Chikitsa (Sleep Therapy)",
            source_type="Classical Ayurvedic Text",
            reliability_tier=ReliabilityTier.T,
            reference_id="AH/Su/7",
            year=None,
            summary="Ashwagandha for Vata-type insomnia. "
                    "Brahmi + Jatamansi for mental restlessness. "
                    "Shirodhara therapy for chronic cases.",
        ),
    ],
    "anxiety": [
        EvidenceSource(
            title="CCRAS: Brahmi in Anxiety Disorders",
            source_type="CCRAS Research",
            reliability_tier=ReliabilityTier.B,
            reference_id="CCRAS/ANX/2018",
            year=2018,
            summary="Brahmi (Bacopa monnieri) 300mg daily showed "
                    "significant anxiolytic effect in 12-week study. "
                    "Also improved cognitive function.",
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  HOME REMEDIAL EVIDENCE (stub — Phase 4)
# ═══════════════════════════════════════════════════════════════════

HOME_REMEDY_EVIDENCE: dict[str, list[EvidenceSource]] = {
    "fever": [
        EvidenceSource(
            title="Traditional Home Remedies for Fever — Evidence Review",
            source_type="Systematic Review",
            reliability_tier=ReliabilityTier.B,
            reference_id="JEM/2020/HF",
            year=2020,
            summary="Tepid sponging effective for reducing fever. "
                    "Adequate hydration critical. "
                    "Tulsi-ginger tea — traditional but limited RCT data.",
        ),
    ],
    "cough": [
        EvidenceSource(
            title="Honey for Acute Cough in Children — Cochrane Review",
            source_type="Cochrane Review",
            reliability_tier=ReliabilityTier.A,
            reference_id="DOI:10.1002/14651858.CD007094",
            year=2018,
            summary="Honey may be superior to diphenhydramine and no "
                    "treatment for cough relief and sleep quality. "
                    "Not for children under 1 year.",
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════
#  EVIDENCE LOOKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_evidence_for_condition(
    condition: str,
    modality: str = "allopathy",
) -> list[EvidenceSource]:
    """
    Look up evidence sources for a given condition and modality.
    """
    condition_key = condition.lower().strip()

    evidence_store = {
        "allopathy": ALLOPATHY_EVIDENCE,
        "ayurveda": AYURVEDA_EVIDENCE,
        "home_remedial": HOME_REMEDY_EVIDENCE,
    }

    store = evidence_store.get(modality, {})

    # Direct match
    if condition_key in store:
        return store[condition_key]

    # Fuzzy match — check if condition is a substring of any key
    for key, sources in store.items():
        if condition_key in key or key in condition_key:
            return sources

    return []


def get_all_evidence_for_condition(condition: str) -> dict[str, list[EvidenceSource]]:
    """
    Get evidence from ALL modalities for a condition.
    Returns { "allopathy": [...], "ayurveda": [...], ... }
    """
    result = {}
    for modality in ["allopathy", "ayurveda", "home_remedial"]:
        evidence = get_evidence_for_condition(condition, modality)
        if evidence:
            result[modality] = evidence
    return result


def get_highest_tier_evidence(
    condition: str, modality: str = "allopathy"
) -> EvidenceSource | None:
    """Return the single highest-reliability evidence for a condition."""
    sources = get_evidence_for_condition(condition, modality)
    if not sources:
        return None

    tier_rank = {
        ReliabilityTier.A: 0,
        ReliabilityTier.B: 1,
        ReliabilityTier.T: 2,
        ReliabilityTier.CAUTION: 3,
    }

    return min(sources, key=lambda s: tier_rank.get(s.reliability_tier, 99))
