.PHONY: install run ingest scan help

help:
	@echo "Available commands:"
	@echo "  make install   Install all dependencies into the active venv"
	@echo "  make run       Start the Streamlit app"
	@echo "  make ingest    Ingest URLs from data/urls_to_ingest.txt into ChromaDB"
	@echo "  make scan      Scan repository for secrets with gitleaks"

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

ingest:
	python scripts/ingest_urls.py

scan:
	gitleaks detect --source . --redact --no-git
