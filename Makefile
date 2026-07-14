.PHONY: run run-k8 run-lenovo run-lggram install lint convert-templates md2pdf

run:
	uv run -m src.cli_app.main

run-k8:
	uv run --env-file .env.backup.k8plus -m src.cli_app.main

run-lenovo:
	uv run --env-file .env.backup.lenovo -m src.cli_app.main

run-lggram:
	uv run --env-file .env.backup.lggram -m src.cli_app.main

install:
	uv sync

lint:
	uv run ruff check src/

convert-templates:
	uv run -m src.cli_app.main --convert-templates-to-pdf

md2pdf:
	uv run -m src.cli_app.md2pdf "$(FILE)"
