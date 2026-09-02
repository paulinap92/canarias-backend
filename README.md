# Canarias Backend Starter

Minimalny starter backendu dla projektu Canarias.

## Start

```powershell
uv sync
uv run uvicorn app.main:app --reload
```

API:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/api/islands
- http://127.0.0.1:8000/docs

## Kontrole

```powershell
uv run mypy app
uv run ruff check .
```

Następny krok:
- endpoint `/api/islands/{slug}`
- potem PostgreSQL
