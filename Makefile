.PHONY: run install lint

run:
	uv run main.py

install:
	uv sync

lint:
	uv run ruff check src/ main.py
