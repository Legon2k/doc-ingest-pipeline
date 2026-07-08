"""
Vacancy parser module.

Converts an input vacancy file into plain text / Markdown,
regardless of whether it is an image or a text-based document.
"""

from pathlib import Path

from src.models import LLMClient

# File extensions handled by each parsing strategy
_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})
_TEXT_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md"})


class VacancyParser:
    """Converts vacancy files to Markdown text using the appropriate strategy."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def to_text(self, file_path: Path) -> str:
        """Convert a vacancy file to plain Markdown text.

        Routing logic:
            - .png / .jpg / .jpeg  → local vision model (OCR)
            - .txt / .md           → direct file read

        Args:
            file_path: Path to the vacancy file.

        Returns:
            Extracted or raw content as a string.

        Raises:
            ValueError: If the file extension is not supported.
            FileNotFoundError: If the file does not exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Vacancy file not found: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix in _IMAGE_EXTENSIONS:
            return self._llm.extract_text_from_screenshot(file_path)

        if suffix in _TEXT_EXTENSIONS:
            try:
                return file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Fallback for files saved with Windows ANSI encoding (CP1252).
                # Common when copying text from browsers or Word on Windows.
                return file_path.read_text(encoding="cp1252")

        supported = sorted(_IMAGE_EXTENSIONS | _TEXT_EXTENSIONS)
        raise ValueError(
            f"Unsupported file extension {suffix!r} for '{file_path.name}'. "
            f"Supported extensions: {', '.join(supported)}"
        )
