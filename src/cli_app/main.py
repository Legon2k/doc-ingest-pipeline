"""
Entry point for the doc-ingest-pipeline.

Run with:
    uv run -m src.cli_app.main
    uv run -m src.cli_app.main --convert-templates-to-pdf
"""

import argparse

from src.core.config import Config
from src.core.exporters import compile_md_to_pdf
from src.core.tailorer import ResumeTailorerEngine


def convert_templates_to_pdf() -> None:
    """Convert every *.md template in TEMPLATES_DIR to a PDF file alongside it."""
    templates_dir = Config.TEMPLATES_DIR
    if not templates_dir.exists():
        print(f"[Convert] Templates directory not found: {templates_dir}")
        return

    md_files = sorted(templates_dir.glob("*.md"))
    if not md_files:
        print(f"[Convert] No *.md files found in {templates_dir}")
        return

    print(f"[Convert] Converting {len(md_files)} template(s) in {templates_dir}")
    for md_path in md_files:
        pdf_path = md_path.with_suffix(".pdf")
        md_text = md_path.read_text(encoding="utf-8")
        compile_md_to_pdf(md_text, pdf_path)
        print(f"[Convert]   {md_path.name} \u2192 {pdf_path.name}")

    print("[Convert] Done.")


def main() -> None:
    """Parse CLI arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(description="doc-ingest-pipeline")
    parser.add_argument(
        "--convert-templates-to-pdf",
        action="store_true",
        help="Convert all *.md templates in TEMPLATES_DIR to PDF and exit.",
    )
    args = parser.parse_args()

    if args.convert_templates_to_pdf:
        convert_templates_to_pdf()
        return

    engine = ResumeTailorerEngine()
    engine.run()


if __name__ == "__main__":
    main()
