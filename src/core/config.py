"""
Configuration module.

Loads all settings from the .env file (or environment variables).
Import `Config` wherever you need access to application settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (three levels up from this file: src/core/ -> src/ -> project root)
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


class Config:
    """Central configuration object populated from environment variables."""

    # ------------------------------------------------------------------
    # Local Ollama instance (vision + fast text)
    # ------------------------------------------------------------------
    LOCAL_LLM_URL: str = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
    LOCAL_LLM_KEY: str = os.getenv("LOCAL_LLM_KEY", "ollama")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "llava:latest")
    # Timeout for local vision OCR requests (seconds). Increase for large images.
    LOCAL_LLM_TIMEOUT: float = float(os.getenv("LOCAL_LLM_TIMEOUT", "180"))
    # Ollama context window size for vision requests. Must be large enough
    # to fit the image tokens + prompt. Increase if you get exceed_context_size_error.
    LOCAL_LLM_NUM_CTX: int = int(os.getenv("LOCAL_LLM_NUM_CTX", "8192"))
    # Text model running on the local Ollama instance (used for vacancy compression).
    LOCAL_TEXT_MODEL: str = os.getenv("LOCAL_TEXT_MODEL", "gemma4:e4b")
    # When true, runs the vacancy compression stage before tailoring.
    # When false, the raw OCR text is passed directly to the cloud tailoring model.
    # Accepts: true/1/yes  or  false/0/no  (case-insensitive). Default: false.
    USE_VACANCY_EXTRACTION: bool = os.getenv("USE_VACANCY_EXTRACTION", "false").strip().lower() in {"true", "1", "yes"}
    # Vision API mode:
    #   false (default) — OpenAI-compatible /v1/chat/completions
    #   true            — Ollama native /api/chat (reliably applies num_ctx)
    # Accepts: true/1/yes  or  false/0/no  (case-insensitive)
    LOCAL_LLM_CHAT_MODE: bool = os.getenv("LOCAL_LLM_CHAT_MODE", "false").strip().lower() in {"true", "1", "yes"}

    # ------------------------------------------------------------------
    # Cloud / reasoning model
    # Currently routed to the same local Ollama instance.
    # To switch to AWS Bedrock or OpenRouter, update CLOUD_LLM_URL,
    # CLOUD_LLM_KEY, and CLOUD_TEXT_MODEL in .env without touching code.
    # ------------------------------------------------------------------
    CLOUD_LLM_URL: str = os.getenv("CLOUD_LLM_URL", "http://localhost:11434/v1")
    CLOUD_LLM_KEY: str = os.getenv("CLOUD_LLM_KEY", "ollama")
    CLOUD_TEXT_MODEL: str = os.getenv("CLOUD_TEXT_MODEL", "llama3.1:latest")
    # Timeout for cloud reasoning requests (seconds). Increase for large resumes.
    CLOUD_LLM_TIMEOUT: float = float(os.getenv("CLOUD_LLM_TIMEOUT", "1800"))

    # ------------------------------------------------------------------
    # Storage paths
    # ------------------------------------------------------------------
    GOOGLE_DRIVE_PATH: Path = Path(os.getenv("GOOGLE_DRIVE_PATH", "./google_drive"))
    OBSIDIAN_VAULT_PATH: Path = Path(os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian_vault"))

    # Templates directory: use .env value if set, otherwise default to
    # the templates/ folder at the project root.
    _templates_env: str | None = os.getenv("TEMPLATES_DIR")
    TEMPLATES_DIR: Path = (
        Path(_templates_env)
        if _templates_env
        else Path(__file__).resolve().parent.parent.parent / "templates"
    )

    # Vacancies directory: use .env value if set, otherwise default to
    # the vacancies/ folder at the project root.
    _vacancies_env: str | None = os.getenv("VACANCIES_DIR")
    VACANCIES_DIR: Path = (
        Path(_vacancies_env)
        if _vacancies_env
        else Path(__file__).resolve().parent.parent.parent / "vacancies"
    )
