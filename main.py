"""
Entry point for the doc-ingest-pipeline.

Run with:
    uv run main.py
"""

from src.tailorer import ResumeTailorerEngine


def main() -> None:
    """Initialize and run the resume tailoring pipeline."""
    engine = ResumeTailorerEngine()
    engine.run()


if __name__ == "__main__":
    main()
