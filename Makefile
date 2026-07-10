.PHONY: run run-k8 run-lenovo run-lggram install lint convert-templates md2pdf

run:
	uv run main.py

run-k8:
	uv run --env-file .env.backup.k8plus main.py

run-lenovo:
	uv run --env-file .env.backup.lenovo main.py

run-lggram:
	uv run --env-file .env.backup.lggram main.py

install:
	uv sync

lint:
	uv run ruff check src/ main.py

convert-templates:
	uv run main.py --convert-templates-to-pdf

md2pdf:
	uv run md2pdf.py "$(FILE)"
