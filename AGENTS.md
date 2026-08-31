# AGENTS.md — PretaVerdi

## Project Overview

Agri-climate risk assessment tool. Phase 1 focuses on understanding Open-Meteo climate data before building infrastructure.

## Commands

```bash
uv sync                          # Install dependencies
uv sync --all-extras             # Install with dev dependencies (pytest, ruff)
uv run pytest tests/             # Run tests (mocked; live tests deselected)
uv run pytest -m live            # Opt-in smoke tests against the real API
uv run ruff check .              # Lint (same command as CI)
uv run jupyter lab               # Launch notebooks
```

## Stack

- Python 3.12+ with `uv`
- `openmeteo-requests` SDK with `requests-cache` (SQLite) and `retry-requests`
- Pandas for data manipulation
- Matplotlib for visualization
- JupyterLab for exploration

## APIs

All three Open-Meteo endpoints (no API key needed):
- **Archive API**: Historical ERA5 reanalysis data (1940–present)
- **Climate API**: CMIP6 climate projections (1950–2050)
- **Forecast API**: Weather forecast (up to 16 days)

## Architecture

```
src/pretaverdi/
├── client.py      # Thin wrapper: 3 functions (historical, projections, forecast)
│                  # Each returns a DataFrame, logs metadata to .cache/query_log.jsonl
└── variables.py   # Constants: variable lists, API URLs, reference locations
```

## Conventions

- Query metadata is logged to `.cache/query_log.jsonl` (append mode, gitignored)
- API responses are cached in `.cache/open_meteo_cache.sqlite` (1h TTL)
- Notebooks end with a Findings & Limitations section
- Notebook outputs are committed; GitHub rendering is the portfolio artifact. Always Restart & Run All (or `uv run jupyter nbconvert --to notebook --execute --inplace <nb>`) before committing so outputs match code
- `docs/data-quality-report.md` is the canonical quality record; notebooks are the narrative walkthrough — each cross-links the other
- Unit tests mock the SDK; a small opt-in live suite (`uv run pytest -m live`) hits the real API. CI runs mocked tests only
- Cache and query log live in `<repo-root>/.cache/` regardless of cwd; override with `PRETAVERDI_CACHE_DIR`
