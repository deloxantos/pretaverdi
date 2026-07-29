# PretaVerdi

**Agri-climate risk assessment and food preparedness — powered by open climate data.**

PretaVerdi explores how freely available climate data can inform agricultural risk analysis and food system resilience. It connects to [Open-Meteo](https://open-meteo.com/) APIs to retrieve historical weather, climate projections, and forecasts for key agricultural regions worldwide.

## Motivation

Climate change is reshaping agriculture globally. Understanding historical patterns, current conditions, and future projections is a prerequisite for building tools that help communities prepare. This project takes a **data-first** approach: understand the data before building infrastructure.

## Status

**Phase 1** — Data exploration and quality assessment. Architecture decisions
and deviations from the [original PRD](docs/prd/phase1-foundation.md) are
recorded in [docs/architecture.md](docs/architecture.md).

- [x] Open-Meteo Archive API integration (historical ERA5 reanalysis) — validated against the live API
- [ ] Open-Meteo Climate API integration (CMIP6 projections) — partial: mock-tested only; multi-model response parsing pending
- [x] Open-Meteo Forecast API integration — client ready, mock-tested
- [x] Data quality assessment for Pampa (AR) and Midwest (US) — see [docs/data-quality-report.md](docs/data-quality-report.md)
- [ ] Multi-region data quality assessment (Punjab, Central Kenya)
- [ ] Risk scenario prototyping
- [ ] AgentCore Gateway + MCP tools (deferred from PRD — see ADR-001)
- [ ] NASA POWER cross-comparison (deferred — see ADR-002)

## Quickstart

```bash
# Clone and setup
git clone https://github.com/deloxantos/pretaverdi.git
cd pretaverdi
uv sync

# Run the exploration notebook
uv run jupyter lab
# Open notebooks/01-open-meteo-exploration.ipynb

# Run tests
uv sync --all-extras
uv run pytest
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

## Project Structure

```
pretaverdi/
├── src/pretaverdi/          # Python package
│   ├── client.py            # Open-Meteo API wrapper (cache + retry + logging)
│   └── variables.py         # Agri-climate variable constants
├── notebooks/               # Iterative exploration notebooks
├── docs/                    # PRDs, ADRs, data quality reports, API evaluation
└── tests/                   # Unit tests
```

## Data Sources

| API | Description | Coverage |
|-----|-------------|----------|
| [Archive](https://open-meteo.com/en/docs/historical-weather-api) | ERA5 reanalysis (historical) | 1940–present, ~9km resolution |
| [Climate](https://open-meteo.com/en/docs/climate-api) | CMIP6 projections | 1950–2050, ~25km resolution |
| [Forecast](https://open-meteo.com/en/docs/forecast-api) | Weather forecast | Up to 16 days ahead |

All data is freely available via Open-Meteo's API (no API key required, 10k calls/day free tier).

## Agri-Climate Variables

Temperature, precipitation, evapotranspiration (FAO ET₀), soil moisture, and solar radiation — the core variables for assessing agricultural climate risk.

## AI for Good Principles

- **Traceability**: Every API query is logged with parameters and response metadata
- **Limitations documented**: Each notebook ends with a limitations section
- **Uncertainty**: Climate projections must report ranges across models, not single-point estimates (planned — multi-model parsing is not yet implemented)
- **Reproducibility**: All notebooks are executable from scratch with `uv run jupyter lab`
- **Correlation ≠ causation**: Climate data alone does not predict crop yields

## License

MIT
