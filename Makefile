.PHONY: install test lint smoke-test search report reproduce notebook

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

smoke-test:
	python -m quantum_diffusion_search search --config configs/search_config.yaml --max-results-per-query 1 --sleep-seconds 0 --sources arxiv,ieee,springer

search:
	python -m quantum_diffusion_search search --config configs/search_config.yaml

report:
	python -m quantum_diffusion_search report --run-id $(RUN_ID)

reproduce:
	python -m quantum_diffusion_search reproduce --raw-run $(RAW_RUN)

notebook:
	python scripts/execute_notebook.py
