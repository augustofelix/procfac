# Puertos por defecto alineados con config.ini
API_PORT ?= 8000
UI_PORT ?= 8501

.PHONY: dev api ui test

# Levanta backend y UI juntos; Ctrl+C detiene ambos
dev:
	$(MAKE) -j2 api ui

api:
	uv run uvicorn app.api.main:app --host 127.0.0.1 --port $(API_PORT) --reload

ui:
	uv run streamlit run app/ui/main.py --server.port $(UI_PORT) --server.headless true

test:
	uv run pytest
