.PHONY: install init fetch-markets snapshot-books dashboard test lint

install:
	pip install -e ".[dev]"

init:
	python -m polyalgo.cli init-db

fetch-markets:
	python -m polyalgo.cli fetch-markets --limit 100

snapshot-books:
	python -m polyalgo.cli snapshot-books --limit 20

dashboard:
	streamlit run src/polyalgo/dashboard/app.py

test:
	pytest -q

lint:
	ruff check .

