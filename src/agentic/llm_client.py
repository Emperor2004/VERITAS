"""
LLM client factory for VERITAS agentic mode.

Reads the provider from environment variables and returns a LangChain
chat-model instance.  When no API key or provider is configured, returns
None — all agents that call this factory must fall back gracefully to
deterministic behaviour when the client is None.

Supported providers
-------------------
  VERITAS_LLM_PROVIDER=gemini   (default if GOOGLE_API_KEY is set)
  VERITAS_LLM_PROVIDER=ollama   (requires a running Ollama server)

Environment variables
---------------------
  VERITAS_LLM_PROVIDER       gemini | ollama  (default: gemini)
  VERITAS_LLM_MODEL          model name (default: gemini-1.5-flash / llama3.2)
  VERITAS_LLM_TEMPERATURE    float 0.0–1.0 (default: 0.0 for reproducibility)
  GOOGLE_API_KEY             required when provider=gemini
  OLLAMA_BASE_URL            base URL for Ollama (default: http://localhost:11434)

Privacy guarantee
-----------------
This factory only instantiates the model object.  It does NOT send any
data.  The callers (schema_inference.py, config_proposer.py, etc.) are
responsible for ensuring only column metadata -- never raw row values --
is included in prompts.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def build_llm_client() -> Optional[Any]:
    """
    Build and return a LangChain chat model based on environment config.

    Returns None if no provider is configured or if the required
    dependencies are not installed.  Callers treat None as deterministic
    mode.
    """
    provider = os.environ.get("VERITAS_LLM_PROVIDER", "").strip().lower()

    # Auto-detect: if GOOGLE_API_KEY is set and provider is not specified,
    # default to Gemini.
    if not provider and os.environ.get("GOOGLE_API_KEY"):
        provider = "gemini"

    if not provider:
        logger.info(
            "VERITAS_LLM_PROVIDER not set and GOOGLE_API_KEY not found. "
            "Running in deterministic mode (no LLM)."
        )
        return None

    if provider == "gemini":
        return _build_gemini_client()
    if provider == "ollama":
        return _build_ollama_client()

    logger.warning(
        "Unknown VERITAS_LLM_PROVIDER=%r. "
        "Falling back to deterministic mode.",
        provider,
    )
    return None


def _build_gemini_client() -> Optional[Any]:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        logger.warning(
            "VERITAS_LLM_PROVIDER=gemini but GOOGLE_API_KEY is not set. "
            "Falling back to deterministic mode."
        )
        return None

    model = os.environ.get("VERITAS_LLM_MODEL", "gemini-1.5-flash")
    temperature = float(os.environ.get("VERITAS_LLM_TEMPERATURE", "0.0"))

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

        client = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
        )
        logger.info("LLM client: Gemini model=%s temperature=%.2f", model, temperature)
        return client
    except ImportError:
        logger.warning(
            "langchain-google-genai is not installed. "
            "Run: pip install langchain-google-genai. "
            "Falling back to deterministic mode."
        )
        return None
    except Exception as exc:
        logger.warning("Failed to build Gemini client: %s. Deterministic mode.", exc)
        return None


def _build_ollama_client() -> Optional[Any]:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("VERITAS_LLM_MODEL", "llama3.2")
    temperature = float(os.environ.get("VERITAS_LLM_TEMPERATURE", "0.0"))

    try:
        from langchain_ollama import ChatOllama  # type: ignore

        client = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
        )
        logger.info(
            "LLM client: Ollama model=%s base_url=%s temperature=%.2f",
            model, base_url, temperature,
        )
        return client
    except ImportError:
        logger.warning(
            "langchain-ollama is not installed. "
            "Run: pip install langchain-ollama. "
            "Falling back to deterministic mode."
        )
        return None
    except Exception as exc:
        logger.warning("Failed to build Ollama client: %s. Deterministic mode.", exc)
        return None
