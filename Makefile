# Ladewüste. See CLAUDE.md "Commands".
.PHONY: setup download pipeline profile test api web clean

setup:            ## install Python deps (web deps arrive in milestone 5)
	uv sync
	@if [ -f web/package.json ]; then cd web && npm install; fi

download:         ## fetch the register CSV (CC BY 4.0) + Germany boundary into data/
	uv run python -m pipeline.download

pipeline:         ## raw CSV -> bronze -> mess report -> dbt build (models + tests) -> quality_report.json
	@ls data/raw/Ladesaeulenregister*.csv >/dev/null 2>&1 || $(MAKE) download
	uv run python -m pipeline.load_bronze
	uv run python -m pipeline.profile
	uv run python -m pipeline.run_dbt build
	uv run python -m pipeline.report

profile:          ## regenerate docs/mess_report.md from the existing bronze table
	uv run python -m pipeline.profile

test:             ## pytest + dbt tests (needs `make pipeline` once); tsc joins in milestone 5
	uv run pytest -q
	uv run python -m pipeline.run_dbt test

api:
	@echo "API arrives in milestone 4"

web:
	@echo "Web app arrives in milestone 5"

clean:            ## remove derived data (keeps the downloaded raw file)
	rm -f data/ladewueste.duckdb data/ladewueste.duckdb.wal
	rm -rf data/gold pipeline/dbt/target pipeline/dbt/logs
