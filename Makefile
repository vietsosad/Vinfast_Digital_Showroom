.PHONY: install run test lint format check openapi docker-up docker-smoke

install:
	cd backend && pip install -r requirements-dev.txt

run:
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check src tests scripts

format:
	cd backend && ruff format src tests scripts

openapi:
	cd backend && python scripts/export_openapi.py

check: lint test

docker-up:
	docker compose up --build -d

docker-smoke:
	python backend/scripts/smoke_test.py --base-url http://127.0.0.1:$${HOST_PORT:-8000}
