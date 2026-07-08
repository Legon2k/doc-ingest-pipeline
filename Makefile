.PHONY: run run-k8 run-lenovo run-lggram install lint

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
