"""Standalone utility: convert a Markdown file to PDF.

Usage:
    uv run md2pdf.py <path/to/file.md>

The output PDF is written next to the source file with the same stem.
"""

import sys
from pathlib import Path

from src.exporters import compile_md_to_pdf


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run md2pdf.py <path/to/file.md>")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"[md2pdf] ERROR: file not found: {input_path}")
        sys.exit(1)

    if input_path.suffix.lower() != ".md":
        print(f"[md2pdf] WARNING: expected a .md file, got '{input_path.suffix}'")

    md_text = input_path.read_text(encoding="utf-8")
    output_path = input_path.with_suffix(".pdf")

    compile_md_to_pdf(md_text, output_path)
    print(f"[md2pdf] PDF saved → {output_path}")


if __name__ == "__main__":
    main()
