# PretaVerdi

**Agri-climate risk assessment and food preparedness — powered by open climate data.**

PretaVerdi explores how freely available climate data can inform agricultural risk analysis and food system resilience. It connects to [Open-Meteo](https://open-meteo.com/) APIs to retrieve historical weather, climate projections, and forecasts for key agricultural regions worldwide.

## Motivation

Climate change is reshaping agriculture globally. Understanding historical patterns, current conditions, and future projections is a prerequisite for building tools that help communities prepare. This project takes a **data-first** approach: understand the data before building infrastructure.

## Status

**Phase 1** — Data exploration and quality assessment. Architecture decisions
and deviations from the [original PRD](docs/prd/phase1-foundation.md) are
recorded in [docs/architecture.md](docs/architecture.md).

- [x] Open-Meteo Archive API integration (historical reanalysis) — validated against the live API
- [x] Open-Meteo Climate API integration (CMIP6 projections) — validated against the live API, multi-model parsing included
- [x] Open-Meteo Forecast API integration — client ready, mock-tested
- [x] Data quality assessment for Pampa (AR) and Midwest (US) — see [docs/data-quality-report.md](docs/data-quality-report.md)
- [x] Multi-model CMIP6 exploration — see [notebooks/02-cmip6-multi-model-projections.ipynb](notebooks/02-cmip6-multi-model-projections.ipynb)
- [ ] Multi-region data quality assessment (Punjab, Central Kenya)
- [ ] Risk scenario prototyping
- [ ] AgentCore Gateway + MCP tools (deferred from PRD — see ADR-001)
- [ ] NASA POWER cross-comparison (deferred — see ADR-002)

## Quickstart

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

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
uv run pytest -m live   # optional: smoke tests against the real API
```

## Notebooks

Guided walkthroughs with outputs committed — they render directly on GitHub, no execution needed:

- [`01-open-meteo-exploration.ipynb`](notebooks/01-open-meteo-exploration.ipynb) — is open reanalysis data good enough to build agri-risk indicators on?
- [`02-cmip6-multi-model-projections.ipynb`](notebooks/02-cmip6-multi-model-projections.ipynb) — CMIP6 projections and why one climate model is never enough.

## Project Structure

```
pretaverdi/
├── src/pretaverdi/          # Python package
│   ├── client.py            # Open-Meteo API wrapper (cache + retry + logging)
│   ├── analysis.py          # Transforms and experiments over client data
│   ├── plots.py             # Figures over analysis results
│   └── variables.py         # Agri-climate variable constants
├── notebooks/               # Iterative exploration notebooks
├── docs/                    # PRDs, ADRs, data quality reports, API evaluation
└── tests/                   # Unit tests
```

## Data Sources

| API | Description | Coverage |
|-----|-------------|----------|
| [Archive](https://open-meteo.com/en/docs/historical-weather-api) | Historical reanalysis — by default Open-Meteo's Best Match blend of ECMWF IFS, ERA5 and ERA5-Land | 1940–present; ERA5 0.25° (~25 km), ERA5-Land 0.1° (~11 km), IFS 9 km |
| [Climate](https://open-meteo.com/en/docs/climate-api) | CMIP6 projections | 1950–2050; served downscaled to ~10 km from ~20–50 km native model grids |
| [Forecast](https://open-meteo.com/en/docs/forecast-api) | Weather forecast | Up to 16 days ahead |

All data is freely available via Open-Meteo's API (no API key required, 10k calls/day free tier).

## Agri-Climate Variables

Temperature, precipitation, evapotranspiration (FAO ET₀), soil moisture, and solar radiation — the core variables for assessing agricultural climate risk.

## AI for Good Principles

- **Traceability**: Every API query is logged with parameters and response metadata
- **Limitations documented**: Each notebook ends with a limitations section
- **Uncertainty**: Climate projections must report ranges across models, not single-point estimates — `get_climate_projections` returns all requested models as `(variable, model)` columns by default
- **Reproducibility**: All notebooks are executable from scratch with `uv run jupyter lab`. Notebook 02 makes large Climate API requests that can hit the free tier's per-minute limit; if that happens, wait a minute and re-run (responses are cached locally for 1 h)
- **Correlation ≠ causation**: Climate data alone does not predict crop yields

## Data Licensing & Attribution

- **Open-Meteo.** Weather and climate data by [Open-Meteo.com](https://open-meteo.com/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The notebooks show derived values (aggregates, statistics, figures), not the original data. The free API tier is for non-commercial use only.
- **ERA5 and ERA5-Land.** Contains modified Copernicus Climate Change Service information 2026. Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information it contains.
- **CMIP6.** We acknowledge the World Climate Research Programme, which coordinated CMIP6, and the modelling groups whose HighResMIP output is used here: the EC-Earth consortium, the Meteorological Research Institute (Japan) and the Chinese Academy of Sciences. The data reaches this project through Open-Meteo's downscaled Climate API under CC BY 4.0. See the [CMIP6 Terms of Use](https://pcmdi.llnl.gov/CMIP6/TermsOfUse).

Citations: Zippenfenig, P. (2023), *Open-Meteo.com Weather API*, Zenodo, [doi:10.5281/zenodo.7970649](https://doi.org/10.5281/zenodo.7970649). Hersbach, H. et al. (2023), *ERA5 hourly data on single levels from 1940 to present*, Copernicus Climate Change Service, [doi:10.24381/cds.adbb2d47](https://doi.org/10.24381/cds.adbb2d47).

## License

MIT covers the code in this repository. The climate data, including data embedded in notebook outputs, remains under its providers' licences.
