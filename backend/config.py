"""
Centralized configuration for the Telehealth Orchestrator.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings — loaded from env vars with sensible defaults."""

    # ── Server ──────────────────────────────────────────────
    APP_NAME: str = "AI Integrative Multilingual Telehealth Orchestrator"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "debug")
    API_PREFIX: str = "/api"

    # ── Backend ─────────────────────────────────────────────
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "*",  # Allow all for prototype
    ]

    # ── LLM Configuration (for future use) ──────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "simulated")
    LLM_NOVA_LITE_MODEL: str = os.getenv("LLM_NOVA_LITE_MODEL", "amazon.nova-lite-v1:0")
    LLM_COMMAND_R_MODEL: str = os.getenv("LLM_COMMAND_R_MODEL", "cohere.command-r-plus-v1:0")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))

    # ── Translation Provider ────────────────────────────────
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "auto")
    TRANSLATOR_ENDPOINT: str = os.getenv("TRANSLATOR_ENDPOINT", "")
    TRANSLATOR_KEY: str = os.getenv("TRANSLATOR_KEY", "")
    TRANSLATOR_REGION: str = os.getenv("TRANSLATOR_REGION", "")
    TRANSLATOR_TIMEOUT: int = int(os.getenv("TRANSLATOR_TIMEOUT", "20"))

    # ── Agent Configuration ─────────────────────────────────
    MAX_PARALLEL_MODALITIES: int = 2
    EMERGENCY_LATENCY_TARGET_MS: int = 2000
    TRANSLATION_BLEU_THRESHOLD: float = 0.92
    BACK_TRANSLATION_SIMILARITY: float = 0.90

    # ── Doctor Recommendation Model ────────────────────────
    ENABLE_HF_DOCTOR_RECOMMENDER: bool = os.getenv("ENABLE_HF_DOCTOR_RECOMMENDER", "true").lower() == "true"
    HF_DOCTOR_RECOMMENDER_MODEL: str = os.getenv(
        "HF_DOCTOR_RECOMMENDER_MODEL",
        "facebook/bart-large-mnli",
    )
    ENABLE_HF_TRIAGE_MODEL: bool = os.getenv("ENABLE_HF_TRIAGE_MODEL", "true").lower() == "true"
    HF_TRIAGE_MODEL: str = os.getenv(
        "HF_TRIAGE_MODEL",
        "facebook/bart-large-mnli",
    )
    ENABLE_HF_INPUT_VALIDATION: bool = os.getenv("ENABLE_HF_INPUT_VALIDATION", "true").lower() == "true"
    HF_INPUT_VALIDATION_MODEL: str = os.getenv(
        "HF_INPUT_VALIDATION_MODEL",
        "facebook/bart-large-mnli",
    )
    HF_INPUT_INVALID_THRESHOLD: float = float(os.getenv("HF_INPUT_INVALID_THRESHOLD", "0.58"))

    # ── Supported Languages ─────────────────────────────────
    SUPPORTED_LANGUAGES: list[str] = ["en", "hi", "ta", "te", "bn", "mr"]
    DEFAULT_LANGUAGE: str = "en"

    # ── Supported Modalities ────────────────────────────────
    SUPPORTED_MODALITIES: list[str] = [
        "allopathy",
        "ayurveda",
        "homeopathy",
        "home_remedial",
    ]

    # ── Risk Levels ─────────────────────────────────────────
    RISK_LEVELS: list[str] = ["emergent", "urgent", "routine", "self-care"]

    # ── Feature Flags ───────────────────────────────────────
    ENABLE_HOMEOPATHY: bool = False   # Phase 4
    ENABLE_HOME_REMEDIAL: bool = False  # Phase 4
    ENABLE_SPEECH_INTAKE: bool = False  # Phase 5


settings = Settings()
