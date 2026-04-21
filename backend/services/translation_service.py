"""Translation service adapter for the telehealth orchestrator.

Prefers a real translation provider when configured and falls back to the
clinical glossary-based translator for deterministic offline behavior.
"""
from __future__ import annotations

import json
import uuid
from typing import Sequence
from urllib import error, request

from backend.config import settings
from backend.knowledge.glossary import translate_text_segment

try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover - optional dependency
    GoogleTranslator = None


class TranslationServiceError(RuntimeError):
    """Raised when the configured translation provider cannot be used."""


def _google_translate_batch(
    texts: Sequence[str],
    target_lang: str,
    source_lang: str = "en",
) -> list[str]:
    """Translate a batch through Google Translator (free provider)."""
    if GoogleTranslator is None:
        raise TranslationServiceError(
            "Google Translator dependency is missing. Install deep-translator."
        )

    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated: list[str] = []
        for text in texts:
            translated.append(translator.translate(text or "") or "")
        return translated
    except Exception as exc:  # pragma: no cover - network/provider variability
        raise TranslationServiceError(str(exc)) from exc


def _azure_translate_batch(
    texts: Sequence[str],
    target_lang: str,
    source_lang: str = "en",
) -> list[str]:
    """Translate a batch through Azure Translator Text API."""
    if not settings.TRANSLATOR_ENDPOINT or not settings.TRANSLATOR_KEY or not settings.TRANSLATOR_REGION:
        raise TranslationServiceError(
            "Azure Translator is not configured. Set TRANSLATION_PROVIDER=azure "
            "and provide TRANSLATOR_ENDPOINT, TRANSLATOR_KEY, and TRANSLATOR_REGION."
        )

    endpoint = settings.TRANSLATOR_ENDPOINT.rstrip("/")
    url = f"{endpoint}/translate?api-version=3.0&from={source_lang}&to={target_lang}"
    body = json.dumps([{ "text": text } for text in texts]).encode("utf-8")
    headers = {
        "Ocp-Apim-Subscription-Key": settings.TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": settings.TRANSLATOR_REGION,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }
    req = request.Request(url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=settings.TRANSLATOR_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise TranslationServiceError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise TranslationServiceError("Azure Translator returned invalid JSON") from exc

    translated_texts: list[str] = []
    for item in payload:
        translations = item.get("translations", [])
        translated_texts.append(translations[0]["text"] if translations else "")
    return translated_texts


def translate_texts(
    texts: Sequence[str],
    target_lang: str,
    source_lang: str = "en",
) -> list[str]:
    """Translate a batch of strings with a real service when available.

    Falls back to glossary-based translation so the app remains deterministic
    when no external translation service credentials are configured.
    """
    normalized = [text or "" for text in texts]
    if not normalized or target_lang == source_lang:
        return list(normalized)

    provider = settings.TRANSLATION_PROVIDER.lower().strip()
    if provider in {"azure", "auto"}:
        try:
            return _azure_translate_batch(normalized, target_lang, source_lang)
        except TranslationServiceError:
            if provider == "azure":
                raise

    if provider in {"google", "auto"}:
        try:
            return _google_translate_batch(normalized, target_lang, source_lang)
        except TranslationServiceError:
            if provider == "google":
                raise

    return [translate_text_segment(text, target_lang) for text in normalized]
