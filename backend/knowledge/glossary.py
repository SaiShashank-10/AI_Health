"""
Multilingual Medical Glossary — maps English medical terms to Hindi, Tamil,
Telugu, Bengali, and Marathi translations.

Used by the Translation Agent and Normalization Agent to preserve
clinical fidelity across languages.
"""
from __future__ import annotations

from typing import Optional


# ═══════════════════════════════════════════════════════════════════
#  MEDICAL GLOSSARY  (English → regional translations)
#  Keys: English term (lowercase)
#  Values: dict with language codes → translations
# ═══════════════════════════════════════════════════════════════════

MEDICAL_GLOSSARY: dict[str, dict[str, str]] = {
    # ── Common Symptoms ─────────────────────────────────────
    "fever": {
        "hi": "बुखार",
        "ta": "காய்ச்சல்",
        "te": "జ్వరం",
        "bn": "জ্বর",
        "mr": "ताप",
    },
    "headache": {
        "hi": "सिरदर्द",
        "ta": "தலைவலி",
        "te": "తలనొప్పి",
        "bn": "মাথাব্যথা",
        "mr": "डोकेदुखी",
    },
    "cough": {
        "hi": "खांसी",
        "ta": "இருமல்",
        "te": "దగ్గు",
        "bn": "কাশি",
        "mr": "खोकला",
    },
    "cold": {
        "hi": "सर्दी",
        "ta": "சளி",
        "te": "జలుబు",
        "bn": "ঠাণ্ডা",
        "mr": "सर्दी",
    },
    "sore throat": {
        "hi": "गले में खराश",
        "ta": "தொண்டை வலி",
        "te": "గొంతు నొప్పి",
        "bn": "গলা ব্যথা",
        "mr": "घसा दुखणे",
    },
    "body pain": {
        "hi": "शरीर दर्द",
        "ta": "உடல் வலி",
        "te": "శరీరం నొప్పి",
        "bn": "শরীর ব্যথা",
        "mr": "अंगदुखी",
    },
    "joint pain": {
        "hi": "जोड़ों का दर्द",
        "ta": "மூட்டு வலி",
        "te": "కీళ్ల నొప్పి",
        "bn": "জয়েন্ট ব্যথা",
        "mr": "सांधेदुखी",
    },
    "chest pain": {
        "hi": "सीने में दर्द",
        "ta": "நெஞ்சு வலி",
        "te": "ఛాతీ నొప్పి",
        "bn": "বুকে ব্যথা",
        "mr": "छातीत दुखणे",
    },
    "stomach pain": {
        "hi": "पेट दर्द",
        "ta": "வயிற்று வலி",
        "te": "కడుపు నొప్పి",
        "bn": "পেট ব্যথা",
        "mr": "पोटदुखी",
    },
    "back pain": {
        "hi": "कमर दर्द",
        "ta": "முதுகு வலி",
        "te": "వెన్ను నొప్పి",
        "bn": "পিঠে ব্যথা",
        "mr": "पाठदुखी",
    },
    "nausea": {
        "hi": "मतली",
        "ta": "குமட்டல்",
        "te": "వికారం",
        "bn": "বমি বমি ভাব",
        "mr": "मळमळ",
    },
    "vomiting": {
        "hi": "उल्टी",
        "ta": "வாந்தி",
        "te": "వాంతి",
        "bn": "বমি",
        "mr": "उलटी",
    },
    "diarrhea": {
        "hi": "दस्त",
        "ta": "வயிற்றுப்போக்கு",
        "te": "విరేచనాలు",
        "bn": "ডায়রিয়া",
        "mr": "जुलाब",
    },
    "constipation": {
        "hi": "कब्ज",
        "ta": "மலச்சிக்கல்",
        "te": "మలబద్ధకం",
        "bn": "কোষ্ঠকাঠিন্য",
        "mr": "बद्धकोष्ठता",
    },
    "dizziness": {
        "hi": "चक्कर आना",
        "ta": "தலைசுற்றல்",
        "te": "తల తిరగడం",
        "bn": "মাথা ঘোরা",
        "mr": "चक्कर येणे",
    },
    "fatigue": {
        "hi": "थकान",
        "ta": "சோர்வு",
        "te": "అలసట",
        "bn": "ক্লান্তি",
        "mr": "थकवा",
    },
    "weakness": {
        "hi": "कमजोरी",
        "ta": "பலவீனம்",
        "te": "బలహీనత",
        "bn": "দুর্বলতা",
        "mr": "अशक्तपणा",
    },
    "breathlessness": {
        "hi": "सांस फूलना",
        "ta": "மூச்சுத்திணறல்",
        "te": "శ్వాస ఆడకపోవడం",
        "bn": "শ্বাসকষ্ট",
        "mr": "श्वास लागणे",
    },
    "palpitations": {
        "hi": "धड़कन बढ़ना",
        "ta": "படபடப்பு",
        "te": "గుండె దడ",
        "bn": "বুক ধড়ফড়",
        "mr": "धडधड",
    },
    "swelling": {
        "hi": "सूजन",
        "ta": "வீக்கம்",
        "te": "వాపు",
        "bn": "ফোলা",
        "mr": "सूज",
    },
    "rash": {
        "hi": "चकत्ते",
        "ta": "சொறி",
        "te": "దద్దుర్లు",
        "bn": "ফুসকুড়ি",
        "mr": "पुरळ",
    },
    "itching": {
        "hi": "खुजली",
        "ta": "அரிப்பு",
        "te": "దురద",
        "bn": "চুলকানি",
        "mr": "खाज",
    },
    "burning sensation": {
        "hi": "जलन",
        "ta": "எரிச்சல்",
        "te": "మంట",
        "bn": "জ্বালা",
        "mr": "जळजळ",
    },
    "insomnia": {
        "hi": "अनिद्रा",
        "ta": "தூக்கமின்மை",
        "te": "నిద్రలేమి",
        "bn": "অনিদ্রা",
        "mr": "निद्रानाश",
    },
    "anxiety": {
        "hi": "चिंता",
        "ta": "பதற்றம்",
        "te": "ఆందోళన",
        "bn": "উদ্বেগ",
        "mr": "चिंता",
    },
    "loss of appetite": {
        "hi": "भूख न लगना",
        "ta": "பசியின்மை",
        "te": "ఆకలి తగ్గడం",
        "bn": "ক্ষুধামান্দ্য",
        "mr": "भूक न लागणे",
    },
    "weight loss": {
        "hi": "वजन कम होना",
        "ta": "எடை குறைவு",
        "te": "బరువు తగ్గడం",
        "bn": "ওজন কমে যাওয়া",
        "mr": "वजन कमी होणे",
    },
    "excessive thirst": {
        "hi": "अत्यधिक प्यास",
        "ta": "அதிக தாகம்",
        "te": "విపరీతమైన దాహం",
        "bn": "অতিরিক্ত তৃষ্ণা",
        "mr": "अति तहान",
    },
    "frequent urination": {
        "hi": "बार-बार पेशाब",
        "ta": "அடிக்கடி சிறுநீர்",
        "te": "తరచుగా మూత్రవిసర్జన",
        "bn": "ঘন ঘন প্রস্রাব",
        "mr": "वारंवार लघवी",
    },
    "blurred vision": {
        "hi": "धुंधला दिखना",
        "ta": "மங்கலான பார்வை",
        "te": "మసకగా కనిపించడం",
        "bn": "ঝাপসা দৃষ্টি",
        "mr": "अंधुक दिसणे",
    },

    # ── Conditions / Diseases ───────────────────────────────
    "diabetes": {
        "hi": "मधुमेह",
        "ta": "நீரிழிவு",
        "te": "మధుమేహం",
        "bn": "ডায়াবেটিস",
        "mr": "मधुमेह",
    },
    "hypertension": {
        "hi": "उच्च रक्तचाप",
        "ta": "உயர் இரத்த அழுத்தம்",
        "te": "అధిక రక్తపోటు",
        "bn": "উচ্চ রক্তচাপ",
        "mr": "उच्च रक्तदाब",
    },
    "asthma": {
        "hi": "दमा",
        "ta": "ஆஸ்துமா",
        "te": "ఆస్తమా",
        "bn": "হাঁপানি",
        "mr": "दमा",
    },
    "arthritis": {
        "hi": "गठिया",
        "ta": "மூட்டு வீக்கம்",
        "te": "కీళ్లవాతం",
        "bn": "বাত",
        "mr": "संधिवात",
    },
    "thyroid disorder": {
        "hi": "थायराइड विकार",
        "ta": "தைராய்டு கோளாறு",
        "te": "థైరాయిడ్ రుగ్మత",
        "bn": "থাইরয়েড সমস্যা",
        "mr": "थायरॉईड विकार",
    },
    "anemia": {
        "hi": "खून की कमी",
        "ta": "இரத்தசோகை",
        "te": "రక్తహీనత",
        "bn": "রক্তস্বল্পতা",
        "mr": "रक्ताल्पता",
    },
    "migraine": {
        "hi": "माइग्रेन",
        "ta": "ஒற்றைத் தலைவலி",
        "te": "మైగ్రేన్",
        "bn": "মাইগ্রেন",
        "mr": "मायग्रेन",
    },
    "acidity": {
        "hi": "एसिडिटी",
        "ta": "அமிலத்தன்மை",
        "te": "ఆమ్లత్వం",
        "bn": "এসিডিটি",
        "mr": "ऍसिडिटी",
    },
    "urinary tract infection": {
        "hi": "मूत्र मार्ग संक्रमण",
        "ta": "சிறுநீர் பாதை தொற்று",
        "te": "మూత్ర మార్గ ఇన్ఫెక్షన్",
        "bn": "মূত্রনালীর সংক্রমণ",
        "mr": "मूत्रमार्ग संसर्ग",
    },
    "skin infection": {
        "hi": "त्वचा संक्रमण",
        "ta": "தோல் தொற்று",
        "te": "చర్మ ఇన్ఫెక్షన్",
        "bn": "ত্বকের সংক্রমণ",
        "mr": "त्वचा संसर्ग",
    },

    # ── Medical Terms ───────────────────────────────────────
    "blood pressure": {
        "hi": "रक्तचाप",
        "ta": "இரத்த அழுத்தம்",
        "te": "రక్తపోటు",
        "bn": "রক্তচাপ",
        "mr": "रक्तदाब",
    },
    "blood sugar": {
        "hi": "रक्त शर्करा",
        "ta": "இரத்த சர்க்கரை",
        "te": "రక్తంలో చక్కెర",
        "bn": "রক্তে শর্করা",
        "mr": "रक्तशर्करा",
    },
    "medication": {
        "hi": "दवाई",
        "ta": "மருந்து",
        "te": "మందు",
        "bn": "ওষুধ",
        "mr": "औषध",
    },
    "dosage": {
        "hi": "खुराक",
        "ta": "மருந்தளவு",
        "te": "మోతాదు",
        "bn": "ডোজ",
        "mr": "डोस",
    },
    "prescription": {
        "hi": "नुस्खा",
        "ta": "மருந்துச்சீட்டு",
        "te": "ప్రిస్క్రిప్షన్",
        "bn": "প্রেসক্রিপশন",
        "mr": "प्रिस्क्रिप्शन",
    },
    "diagnosis": {
        "hi": "निदान",
        "ta": "நோயறிதல்",
        "te": "రోగ నిర్ధారణ",
        "bn": "রোগ নির্ণয়",
        "mr": "निदान",
    },
    "treatment": {
        "hi": "उपचार",
        "ta": "சிகிச்சை",
        "te": "చికిత్స",
        "bn": "চিকিৎসা",
        "mr": "उपचार",
    },
    "consultation": {
        "hi": "परामर्श",
        "ta": "ஆலோசனை",
        "te": "సంప్రదింపు",
        "bn": "পরামর্শ",
        "mr": "सल्ला",
    },
    "emergency": {
        "hi": "आपातकाल",
        "ta": "அவசரநிலை",
        "te": "అత్యవసరం",
        "bn": "জরুরি অবস্থা",
        "mr": "आणीबाणी",
    },
    "hospital": {
        "hi": "अस्पताल",
        "ta": "மருத்துவமனை",
        "te": "ఆసుపత్రి",
        "bn": "হাসপাতাল",
        "mr": "रुग्णालय",
    },

    # ── Ayurvedic Terms ─────────────────────────────────────
    "dosha": {
        "hi": "दोष",
        "ta": "தோஷம்",
        "te": "దోషం",
        "bn": "দোষ",
        "mr": "दोष",
    },
    "vata": {
        "hi": "वात",
        "ta": "வாதம்",
        "te": "వాతం",
        "bn": "বাত",
        "mr": "वात",
    },
    "pitta": {
        "hi": "पित्त",
        "ta": "பித்தம்",
        "te": "పిత్తం",
        "bn": "পিত্ত",
        "mr": "पित्त",
    },
    "kapha": {
        "hi": "कफ",
        "ta": "கபம்",
        "te": "కఫం",
        "bn": "কফ",
        "mr": "कफ",
    },
    "ayurveda": {
        "hi": "आयुर्वेद",
        "ta": "ஆயுர்வேதம்",
        "te": "ఆయుర్వేదం",
        "bn": "আয়ুর্বেদ",
        "mr": "आयुर्वेद",
    },
    "panchakarma": {
        "hi": "पंचकर्म",
        "ta": "பஞ்சகர்மா",
        "te": "పంచకర్మ",
        "bn": "পঞ্চকর্ম",
        "mr": "पंचकर्म",
    },

    # ── Care Plan Terms ─────────────────────────────────────
    "follow up": {
        "hi": "अनुवर्ती",
        "ta": "தொடர் கவனிப்பு",
        "te": "ఫాలో అప్",
        "bn": "ফলো আপ",
        "mr": "पाठपुरावा",
    },
    "warning": {
        "hi": "चेतावनी",
        "ta": "எச்சரிக்கை",
        "te": "హెచ్చరిక",
        "bn": "সতর্কতা",
        "mr": "इशारा",
    },
    "contraindication": {
        "hi": "मतभेद",
        "ta": "முரண்பாடு",
        "te": "విరుద్ధ సూచన",
        "bn": "প্রতিনির্দেশ",
        "mr": "प्रतिबंध",
    },
    "side effect": {
        "hi": "दुष्प्रभाव",
        "ta": "பக்க விளைவு",
        "te": "దుష్ప్రభావం",
        "bn": "পার্শ্বপ্রতিক্রিয়া",
        "mr": "दुष्परिणाम",
    },
    "self care": {
        "hi": "स्व-देखभाल",
        "ta": "சுய கவனிப்பு",
        "te": "స్వీయ సంరక్షణ",
        "bn": "স্ব-যত্ন",
        "mr": "स्व-काळजी",
    },
    "rest": {
        "hi": "आराम",
        "ta": "ஓய்வு",
        "te": "విశ్రాంతి",
        "bn": "বিশ্রাম",
        "mr": "विश्रांती",
    },
    "hydration": {
        "hi": "जलयोजन",
        "ta": "நீரேற்றம்",
        "te": "హైడ్రేషన్",
        "bn": "হাইড্রেশন",
        "mr": "हायड्रेशन",
    },
}


# ═══════════════════════════════════════════════════════════════════
#  REVERSE MAPPINGS  (regional term → English)
#  Used by the Normalization Agent to detect symptoms in any language
# ═══════════════════════════════════════════════════════════════════

# Build reverse lookup: { "बुखार": "fever", "காய்ச்சல்": "fever", ... }
REVERSE_GLOSSARY: dict[str, str] = {}
for eng_term, translations in MEDICAL_GLOSSARY.items():
    for _lang, local_term in translations.items():
        REVERSE_GLOSSARY[local_term.lower()] = eng_term

# Also add common transliterated / romanized forms
TRANSLITERATED_TERMS: dict[str, str] = {
    "bukhar": "fever",
    "bukhad": "fever",
    "sardard": "headache",
    "sir dard": "headache",
    "sirdard": "headache",
    "khansi": "cough",
    "khaansi": "cough",
    "khasi": "cough",
    "sardi": "cold",
    "jukham": "cold",
    "pet dard": "stomach pain",
    "pet mein dard": "stomach pain",
    "kamar dard": "back pain",
    "chakkar": "dizziness",
    "chakkar aana": "dizziness",
    "thakan": "fatigue",
    "kamzori": "weakness",
    "kamjori": "weakness",
    "ulti": "vomiting",
    "dast": "diarrhea",
    "kabz": "constipation",
    "sujan": "swelling",
    "khujli": "itching",
    "jalan": "burning sensation",
    "neend na aana": "insomnia",
    "chinta": "anxiety",
    "bhuk na lagna": "loss of appetite",
    "sans phoolna": "breathlessness",
    "saans phulna": "breathlessness",
    "seene mein dard": "chest pain",
    "sine mein dard": "chest pain",
    "gala kharab": "sore throat",
    "gale mein dard": "sore throat",
    "jodo ka dard": "joint pain",
    "jodon ka dard": "joint pain",
    "badan dard": "body pain",
    "kai": "vomiting",
    "vaanti": "vomiting",
    "matli": "nausea",
}


# ═══════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def translate_term(english_term: str, target_lang: str) -> Optional[str]:
    """
    Translate an English medical term to a target language.
    Returns None if translation is not available.
    """
    entry = MEDICAL_GLOSSARY.get(english_term.lower())
    if entry and target_lang in entry:
        return entry[target_lang]
    return None


def translate_text_segment(text: str, target_lang: str) -> str:
    """
    Translate a text segment by replacing known English medical terms
    with their target language equivalents.  Non-medical words are kept as-is.
    """
    if target_lang == "en":
        return text

    result = text
    # Sort by length (longest first) to avoid partial replacements
    sorted_terms = sorted(MEDICAL_GLOSSARY.keys(), key=len, reverse=True)
    for eng_term in sorted_terms:
        if eng_term.lower() in result.lower():
            translation = translate_term(eng_term, target_lang)
            if translation:
                # Case-insensitive replacement
                import re
                result = re.sub(
                    re.escape(eng_term), translation, result, flags=re.IGNORECASE
                )
    return result


def detect_language_terms(text: str) -> list[str]:
    """
    Detect medical terms in text (any language) and return English equivalents.
    Handles both native script and transliterated input.
    """
    text_lower = text.lower()
    found_terms: list[str] = []

    # Check transliterated terms first (romanized Hindi, etc.)
    for romanized, english in TRANSLITERATED_TERMS.items():
        if romanized in text_lower and english not in found_terms:
            found_terms.append(english)

    # Check native script reverse glossary
    for local_term, english in REVERSE_GLOSSARY.items():
        if local_term in text_lower and english not in found_terms:
            found_terms.append(english)

    # Check direct English terms
    for eng_term in MEDICAL_GLOSSARY:
        if eng_term in text_lower and eng_term not in found_terms:
            found_terms.append(eng_term)

    return found_terms


def get_glossary_for_language(lang_code: str) -> dict[str, str]:
    """Return the entire glossary filtered for a specific language."""
    result = {}
    for eng_term, translations in MEDICAL_GLOSSARY.items():
        if lang_code in translations:
            result[eng_term] = translations[lang_code]
    return result


def get_all_supported_languages() -> list[dict[str, str]]:
    """Return list of supported languages with codes and names."""
    return [
        {"code": "en", "name": "English", "native": "English"},
        {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
        {"code": "ta", "name": "Tamil", "native": "தமிழ்"},
        {"code": "te", "name": "Telugu", "native": "తెలుగు"},
        {"code": "bn", "name": "Bengali", "native": "বাংলা"},
        {"code": "mr", "name": "Marathi", "native": "मराठी"},
    ]
