# Ladewüste. See CLAUDE.md "Commands".
.PHONY: setup download pipeline profile types test lint parity api web docker-pipeline up clean

setup:            ## install Python deps (web deps arrive in milestone 5)
	uv sync
	@if [ -f web/package.json ]; then cd web && npm install; fi

download:         ## fetch the register CSV (CC BY 4.0) + Germany boundary into data/
	uv run python -m pipeline.download

pipeline:         ## raw CSV -> bronze -> mess report -> dbt build (models + tests) -> gold parquet + quality_report.json
	uv run python -m pipeline.run_all

profile:          ## regenerate docs/mess_report.md from the existing bronze table
	uv run python -m pipeline.profile

types:            ## FastAPI models -> api/openapi.json -> web/src/lib/api-types.ts
	uv run python -m api.export_openapi
	cd web && npm run -s types

test:             ## pytest + dbt tests (needs `make pipeline` once) + TypeScript typecheck
	uv run ruff check .
	uv run pytest -q
	uv run python -m pipeline.run_dbt test
	cd web && npm run -s lint && npm run -s typecheck && npm test --silent

lint:             ## ruff + eslint
	uv run ruff check .
	cd web && npm run -s lint

docker-pipeline:  ## build ./data inside Docker (downloads the register if needed)
	docker compose --profile pipeline run --rm pipeline

up:               ## run API + web in Docker: http://localhost:8080
	docker compose up --build

parity:           ## browser coverage (web/src/lib/coverage.ts) == Python planner; needs `make api` running
	cd web && LADEWUESTE_API_URL=http://127.0.0.1:8000 npx vitest run coverage.parity

api:              ## FastAPI on :8000 (docs at http://localhost:8000/docs)
	uv run uvicorn api.app.main:app --reload --port 8000

web:              ## Vite dev server on :5173 (calls the API through /api; run `make api` too)
	cd web && npm run dev

clean:            ## remove derived data (keeps the downloaded raw file)
	rm -f data/ladewueste.duckdb data/ladewueste.duckdb.wal
	rm -rf data/gold pipeline/dbt/target pipeline/dbt/logs
