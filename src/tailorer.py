"""
Tailorer engine module.

Main orchestrator for the document ingestion and resume tailoring pipeline.

Directory layout expected at runtime:

    vacancies/
        architect/
            Acme_Solution_Architect.png
            BigCorp_Cloud_Architect.txt
        data-engineer/
            Startup_Senior_Data_Engineer.md

    templates/
        architect.md
        data-engineer.md

For each vacancy file found, the engine:
  1. Looks up the matching template by category name.
  2. Parses the vacancy file (vision OCR or direct read).
  3. Tailors the resume via the cloud/reasoning model.
  4. Exports all artifacts via LocalArchiveExporter.
"""

import time
from pathlib import Path

from src.config import Config
from src.exporters import LocalArchiveExporter
from src.models import LLMClient
from src.parser import VacancyParser

# Root directory for vacancy input files (relative to the project root).
_VACANCIES_DIR = Path("vacancies")

# File extensions the pipeline can process.
_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".txt", ".md"}
)


class ResumeTailorerEngine:
    """Orchestrates the full document-ingestion and resume-tailoring pipeline."""

    def __init__(self) -> None:
        llm = LLMClient()
        self._parser = VacancyParser(llm)
        self._llm = llm
        self._exporter = LocalArchiveExporter()

    def run(self) -> None:
        """Scan vacancies/ by category sub-folder and process every supported file."""
        if not _VACANCIES_DIR.exists():
            print(
                f"[Engine] Vacancies directory not found: {_VACANCIES_DIR.resolve()}\n"
                "[Engine] Create it and add vacancy files organised by category sub-folder."
            )
            return

        processed = 0
        skipped = 0
        start_time = time.perf_counter()

        for category_dir in sorted(_VACANCIES_DIR.iterdir()):
            if not category_dir.is_dir():
                continue

            category = category_dir.name
            template_path = Config.TEMPLATES_DIR / f"{category}.md"

            if not template_path.exists():
                print(
                    f"[Engine] No template for category '{category}' "
                    f"(expected: {template_path}). Skipping."
                )
                skipped += 1
                continue

            template_md = template_path.read_text(encoding="utf-8")
            print(f"\n[Engine] Category: {category}  |  Template: {template_path.name}")

            for vacancy_file in sorted(category_dir.iterdir()):
                if vacancy_file.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                    print(f"[Engine]   Skipping unsupported file: {vacancy_file.name}")
                    skipped += 1
                    continue

                print(f"[Engine]   → {vacancy_file.name}")
                self._process_file(vacancy_file, category, template_md)
                processed += 1

        elapsed = time.perf_counter() - start_time
        print(
            f"\n[Engine] Pipeline complete — "
            f"processed: {processed}, skipped: {skipped}.\n"
            f"[Engine] Execution time: {elapsed:.1f}s"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _process_file(
        self,
        vacancy_file: Path,
        category: str,
        template_md: str,
    ) -> None:
        """Run the two-stage pipeline for a single vacancy file.

        Stage 1: Parse vacancy → extract text (vision OCR or direct read).
        Stage 2: Tailor resume → send vacancy + template to cloud model.
        Stage 3: Export → archive artifacts to Google Drive and Obsidian.

        Filename convention:  <Company>_<Role_Word1>_<Role_Word2>.ext
        Example:              Acme_Solution_Architect.png
                              → company = "Acme"
                              → role    = "Solution Architect"
        """
        # Parse company name from the first "_"-separated token in the filename.
        parts = vacancy_file.stem.split("_")
        company = parts[0] if parts else "Unknown"

        try:
            # Stage 1 — extract vacancy text
            t0 = time.perf_counter()
            vacancy_text = self._parser.to_text(vacancy_file)
            t1 = time.perf_counter()
            print(f"[Engine]     Vacancy extracted ({len(vacancy_text):,} chars) in {t1 - t0:.2f}s")

            # Stage 2 — tailor the resume
            t0 = time.perf_counter()
            tailored_md = self._llm.tailor_resume_via_cloud(vacancy_text, template_md)
            t1 = time.perf_counter()
            print(f"[Engine]     Resume tailored  ({len(tailored_md):,} chars) in {t1 - t0:.2f}s")

            # Stage 3 — export all artifacts
            self._exporter.archive_all_artifacts(
                category=category,
                company=company,
                file_name_stem=vacancy_file.stem,
                source_file=vacancy_file,
                vacancy_text=vacancy_text,
                tailored_md=tailored_md,
            )

        except Exception as exc:  # noqa: BLE001
            # Log and continue — one failed file should not abort the whole batch.
            print(f"[Engine]     ERROR processing '{vacancy_file.name}': {exc}")
