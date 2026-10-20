# Puertos por defecto alineados con config.ini
API_PORT ?= 8000
UI_PORT ?= 8501

.PHONY: dev api ui test evaluar cargar-json

# Levanta backend y UI juntos; Ctrl+C detiene ambos
dev:
	$(MAKE) -j2 api ui

api:
	uv run uvicorn app.api.main:app --host 127.0.0.1 --port $(API_PORT) --reload

ui:
	uv run streamlit run app/ui/main.py --server.port $(UI_PORT) --server.headless true

test:
	uv run pytest

# Contra el Conjunto de referencia de tests/data/; llama a la API real de Claude.
# Ejemplos: make evaluar, make evaluar ARGS=--detalle, make evaluar ARGS="--simultaneas 5"
evaluar:
	uv run python -m tests.evaluacion $(ARGS)

# Carga manual de los JSON esperados de tests/data/ (no llama a Claude)
cargar-json:
	uv run streamlit run tests/carga_manual.py --server.port 8502 --server.headless true
