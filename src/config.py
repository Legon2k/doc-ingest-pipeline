"""
Configuration module.

Loads all settings from the .env file (or environment variables).
Import `Config` wherever you need access to application settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file: src/ -> project root)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


class Config:
    """Central configuration object populated from environment variables."""

    # ------------------------------------------------------------------
    # Local Ollama instance (vision + fast text)
    # ------------------------------------------------------------------
    LOCAL_LLM_URL: str = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
    LOCAL_LLM_KEY: str = os.getenv("LOCAL_LLM_KEY", "ollama")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "llava:latest")

    # ------------------------------------------------------------------
    # Cloud / reasoning model
    # Currently routed to the same local Ollama instance.
    # To switch to AWS Bedrock or OpenRouter, update CLOUD_LLM_URL,
    # CLOUD_LLM_KEY, and CLOUD_TEXT_MODEL in .env without touching code.
    # ------------------------------------------------------------------
    CLOUD_LLM_URL: str = os.getenv("CLOUD_LLM_URL", "http://localhost:11434/v1")
    CLOUD_LLM_KEY: str = os.getenv("CLOUD_LLM_KEY", "ollama")
    CLOUD_TEXT_MODEL: str = os.getenv("CLOUD_TEXT_MODEL", "llama3.1:latest")

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
        else Path(__file__).resolve().parent.parent / "templates"
    )
