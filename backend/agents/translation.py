"""
Translation Agent — generates multilingual versions of the care plan
using the medical glossary for clinical fidelity.

Pipeline role:  FINAL agent before Feedback (runs after Synthesizer).
Input:          CareRecommendation, target language(s)
Output:         list[TranslationOutput] (localized_text_variants)

Features:
  - Glossary-based medical term translation (preserves clinical accuracy)
  - Structured summary generation in each language
  - Warning translation
  - Recommendation item translation
"""
from __future__ import annotations

from datetime import datetime

from backend.schemas.common import (
    PlanSegment,
    Warning,
    AgentTrace,
    AgentName,
    AgentStatus,
)
from backend.schemas.recommendation import (
    CareRecommendation,
    TranslationOutput,
)
from backend.knowledge.glossary import (
    translate_term,
    translate_text_segment,
    get_all_supported_languages,
    MEDICAL_GLOSSARY,
)


# ═══════════════════════════════════════════════════════════════════
#  LANGUAGE METADATA
# ═══════════════════════════════════════════════════════════════════

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
}

# Localized UI phrases for structured output
LOCALIZED_PHRASES: dict[str, dict[str, str]] = {
    "care_plan_title": {
        "en": "Your Care Plan",
        "hi": "आपकी देखभाल योजना",
        "ta": "உங்கள் பராமரிப்புத் திட்டம்",
        "te": "మీ సంరక్షణ ప్రణాళిక",
        "bn": "আপনার যত্ন পরিকল্পনা",
        "mr": "तुमची काळजी योजना",
    },
    "risk_level": {
        "en": "Risk Level",
        "hi": "जोखिम स्तर",
        "ta": "ஆபத்து நிலை",
        "te": "ప్రమాద స్థాయి",
        "bn": "ঝুঁকির মাত্রা",
        "mr": "जोखीम पातळी",
    },
    "recommendations": {
        "en": "Recommendations",
        "hi": "सिफारिशें",
        "ta": "பரிந்துரைகள்",
        "te": "సిఫార్సులు",
        "bn": "সুপারিশ",
        "mr": "शिफारसी",
    },
    "medications": {
        "en": "Medications / Formulations",
        "hi": "दवाइयाँ / फॉर्मूलेशन",
        "ta": "மருந்துகள்",
        "te": "మందులు",
        "bn": "ওষুধ",
        "mr": "औषधे",
    },
    "lifestyle": {
        "en": "Lifestyle Advice",
        "hi": "जीवनशैली सलाह",
        "ta": "வாழ்க்கைமுறை ஆலோசனை",
        "te": "జీవనశైలి సలహా",
        "bn": "জীবনধারা পরামর্শ",
        "mr": "जीवनशैली सल्ला",
    },
    "warnings": {
        "en": "Important Warnings",
        "hi": "महत्वपूर्ण चेतावनियाँ",
        "ta": "முக்கிய எச்சரிக்கைகள்",
        "te": "ముఖ్యమైన హెచ్చరికలు",
        "bn": "গুরুত্বপূর্ণ সতর্কতা",
        "mr": "महत्त्वाच्या इशारे",
    },
    "follow_up": {
        "en": "Follow-up",
        "hi": "अनुवर्ती",
        "ta": "தொடர்நிலை",
        "te": "ఫాలో-అప్",
        "bn": "ফলো-আপ",
        "mr": "पाठपुरावा",
    },
    "emergent": {
        "en": "EMERGENCY — Seek immediate medical attention",
        "hi": "आपातकाल — तुरंत चिकित्सा सहायता लें",
        "ta": "அவசரநிலை — உடனடி மருத்துவ உதவி பெறுங்கள்",
        "te": "అత్యవసరం — వెంటనే వైద్య సహాయం పొందండి",
        "bn": "জরুরি — অবিলম্বে চিকিৎসা সাহায্য নিন",
        "mr": "आणीबाणी — तात्काळ वैद्यकीय मदत घ्या",
    },
    "urgent": {
        "en": "URGENT — Consult a doctor within 24 hours",
        "hi": "तत्काल — 24 घंटे के भीतर डॉक्टर से मिलें",
        "ta": "அவசரம் — 24 மணி நேரத்திற்குள் மருத்துவரை அணுகுங்கள்",
        "te": "అత్యవసరం — 24 గంటల్లో వైద్యుడిని సంప్రదించండి",
        "bn": "জরুরি — ২৪ ঘণ্টার মধ্যে ডাক্তার দেখান",
        "mr": "तातडीचे — 24 तासांच्या आत डॉक्टरांना भेटा",
    },
    "routine": {
        "en": "ROUTINE — Schedule a regular consultation",
        "hi": "सामान्य — नियमित परामर्श निर्धारित करें",
        "ta": "வழக்கமான — வழக்கமான ஆலோசனையை திட்டமிடுங்கள்",
        "te": "రొటీన్ — సాధారణ సంప్రదింపు షెడ్యూల్ చేయండి",
        "bn": "রুটিন — নিয়মিত পরামর্শ নির্ধারণ করুন",
        "mr": "नियमित — नियमित सल्ला निश्चित करा",
    },
    "self-care": {
        "en": "SELF-CARE — Home management recommended",
        "hi": "स्व-देखभाल — घरेलू प्रबंधन की सलाह",
        "ta": "சுய கவனிப்பு — வீட்டு மேலாண்மை பரிந்துரைக்கப்படுகிறது",
        "te": "స్వీయ సంరక్షణ — ఇంటి నిర్వహణ సిఫార్సు",
        "bn": "স্ব-যত্ন — ঘরোয়া ব্যবস্থাপনা প্রস্তাবিত",
        "mr": "स्व-काळजी — घरगुती व्यवस्थापन शिफारस",
    },
    "disclaimer": {
        "en": "This is an AI-generated recommendation. Please consult a qualified healthcare professional before starting any treatment.",
        "hi": "यह एक AI-जनित सिफारिश है। कोई भी उपचार शुरू करने से पहले कृपया योग्य स्वास्थ्य पेशेवर से परामर्श करें।",
        "ta": "இது AI உருவாக்கிய பரிந்துரை. எந்த சிகிச்சையையும் தொடங்குவதற்கு முன் தகுதிவாய்ந்த சுகாதார நிபுணரை அணுகவும்.",
        "te": "ఇది AI రూపొందించిన సిఫార్సు. ఏదైనా చికిత్స ప్రారంభించే ముందు అర్హత కలిగిన వైద్య నిపుణుడిని సంప్రదించండి.",
        "bn": "এটি একটি AI-উত্পন্ন সুপারিশ। কোনো চিকিৎসা শুরু করার আগে দয়া করে একজন যোগ্য স্বাস্থ্যসেবা পেশাদারের সাথে পরামর্শ করুন।",
        "mr": "ही AI-निर्मित शिफारस आहे. कोणताही उपचार सुरू करण्यापूर्वी कृपया पात्र आरोग्य व्यावसायिकांचा सल्ला घ्या.",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  TRANSLATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _translate_recommendation_item(text: str, lang: str) -> str:
    """Translate a single recommendation line using glossary mapping."""
    if lang == "en":
        return text
    return translate_text_segment(text, lang)


def _translate_warning(warning: Warning, lang: str) -> str:
    """Translate a warning message."""
    if lang == "en":
        return f"⚠️ [{warning.severity.upper()}] {warning.message}"

    translated_msg = translate_text_segment(warning.message, lang)
    severity_map = {
        "high": {"hi": "उच्च", "ta": "அதிக", "te": "అధిక", "bn": "উচ্চ", "mr": "उच्च"},
        "medium": {"hi": "मध्यम", "ta": "நடுத்தர", "te": "మధ్యస్థ", "bn": "মাঝারি", "mr": "मध्यम"},
        "low": {"hi": "कम", "ta": "குறைந்த", "te": "తక్కువ", "bn": "নিম্ন", "mr": "कमी"},
    }
    sev_text = severity_map.get(warning.severity, {}).get(lang, warning.severity.upper())
    return f"⚠️ [{sev_text}] {translated_msg}"


def _build_summary(
    recommendation: CareRecommendation,
    lang: str,
) -> str:
    """Build a localized summary of the care plan."""
    risk_text = LOCALIZED_PHRASES.get(
        recommendation.risk_level.value, {}
    ).get(lang, recommendation.risk_level.value.upper())

    title = LOCALIZED_PHRASES["care_plan_title"].get(lang, "Your Care Plan")
    risk_label = LOCALIZED_PHRASES["risk_level"].get(lang, "Risk Level")

    # Modalities involved
    modalities = []
    for seg in recommendation.plan_segments:
        mod_name = seg.modality.value.title()
        label = seg.priority_label
        modalities.append(f"{mod_name} ({label})")
    modalities_text = ", ".join(modalities)

    # Build summary lines
    lines = [
        f"📋 {title}",
        f"",
        f"🔴 {risk_label}: {risk_text}",
        f"",
    ]

    if recommendation.triage_justification:
        just_translated = translate_text_segment(
            recommendation.triage_justification, lang
        )
        lines.append(just_translated)
        lines.append("")

    # Modalities
    rec_label = LOCALIZED_PHRASES["recommendations"].get(lang, "Recommendations")
    lines.append(f"🏥 {rec_label}:")
    for seg in recommendation.plan_segments:
        seg_title = translate_text_segment(seg.title, lang)
        lines.append(f"  • {seg_title}")
    lines.append("")

    # Key medications (top 5)
    med_label = LOCALIZED_PHRASES["medications"].get(lang, "Medications")
    lines.append(f"💊 {med_label}:")
    med_count = 0
    for seg in recommendation.plan_segments:
        for med in seg.medications[:3]:
            med_translated = translate_text_segment(med, lang)
            lines.append(f"  • {med_translated}")
            med_count += 1
            if med_count >= 5:
                break
        if med_count >= 5:
            break
    lines.append("")

    # Warnings
    if recommendation.warnings:
        warn_label = LOCALIZED_PHRASES["warnings"].get(lang, "Warnings")
        lines.append(f"⚠️ {warn_label}:")
        for warning in recommendation.warnings[:3]:
            lines.append(f"  • {_translate_warning(warning, lang)}")
        lines.append("")

    # Follow-up
    fu_label = LOCALIZED_PHRASES["follow_up"].get(lang, "Follow-up")
    for seg in recommendation.plan_segments[:1]:
        if seg.follow_up:
            fu_translated = translate_text_segment(seg.follow_up, lang)
            lines.append(f"📅 {fu_label}: {fu_translated}")
    lines.append("")

    # Disclaimer
    disclaimer = LOCALIZED_PHRASES["disclaimer"].get(lang, "")
    if disclaimer:
        lines.append(f"ℹ️ {disclaimer}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  MAIN TRANSLATION FUNCTION
# ═══════════════════════════════════════════════════════════════════

def translate_recommendation(
    recommendation: CareRecommendation,
    target_languages: list[str] | None = None,
) -> tuple[list[TranslationOutput], AgentTrace]:
    """
    Generate multilingual translations of the care recommendation.

    Args:
        recommendation: The synthesized care recommendation.
        target_languages: Languages to translate to. If None, translates
                         to all supported non-English languages.

    Returns:
        (translation_outputs, agent_trace)
    """
    started_at = datetime.utcnow()

    if target_languages is None:
        target_languages = ["hi", "ta", "te", "bn", "mr"]

    # Remove English if present (we always include English as base)
    target_languages = [l for l in target_languages if l != "en"]

    translations: list[TranslationOutput] = []

    for lang in target_languages:
        lang_name = LANGUAGE_NAMES.get(lang, lang)

        # Build localized summary
        summary = _build_summary(recommendation, lang)

        # Translate individual recommendation items
        translated_recs: list[str] = []
        for segment in recommendation.plan_segments:
            for rec in segment.recommendations[:5]:  # Top 5 per segment
                translated = _translate_recommendation_item(rec, lang)
                translated_recs.append(translated)

        # Translate warnings
        translated_warnings: list[str] = []
        for warning in recommendation.warnings:
            translated_warnings.append(_translate_warning(warning, lang))

        translation = TranslationOutput(
            language_code=lang,
            language_name=lang_name,
            summary=summary,
            recommendations=translated_recs,
            warnings=translated_warnings,
        )
        translations.append(translation)

    completed_at = datetime.utcnow()
    trace = AgentTrace(
        agent_name=AgentName.TRANSLATION,
        status=AgentStatus.COMPLETED,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        input_summary=f"Target languages: {target_languages}",
        output_summary=(
            f"{len(translations)} translations generated: "
            f"{[t.language_code for t in translations]}"
        ),
    )

    return translations, trace
