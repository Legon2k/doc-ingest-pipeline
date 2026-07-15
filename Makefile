.PHONY: run run-k8 run-lenovo run-lggram run-ui install lint convert-templates md2pdf

run:
	uv run -m src.cli_app.main

run-k8:
	uv run --env-file .env.backup.k8plus -m src.cli_app.main

run-lenovo:
	uv run --env-file .env.backup.lenovo -m src.cli_app.main

run-lggram:
	uv run --env-file .env.backup.lggram -m src.cli_app.main

# Run the Streamlit UI with PYTHONPATH set to resolve monorepo imports
run-ui:
	$(eval export PYTHONPATH=.)
	uv run --package web-ui streamlit run src/web_ui/app.py
		
install:
	uv sync

lint:
	uv run ruff check src/

convert-templates:
	uv run -m src.cli_app.main --convert-templates-to-pdf

# Convert a Markdown file to PDF
# Usage: make md2pdf FILE=document.md
md2pdf:
ifndef FILE
	$(error FILE variable is not set. Usage: make md2pdf FILE=path/to/file.md)
endif
	uv run -m src.cli_app.md2pdf "$(FILE)"
