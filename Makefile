.PHONY: run test lint format check

run:
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest tests/ -v

lint:
	cd backend && ruff check src/ tests/

format:
	cd backend && ruff format src/ tests/

check: lint test
