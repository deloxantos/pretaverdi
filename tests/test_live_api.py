"""Opt-in smoke tests against the real Open-Meteo API.

Deselected by default (see addopts in pyproject.toml); run with:

    uv run pytest -m live

These tests pin the parts of the API contract that mocked tests cannot see:
which variable names the endpoints accept, and the shape of multi-model
climate responses. Small date ranges keep each call cheap (<2s).
"""

import pandas as pd
import pytest
from openmeteo_requests import OpenMeteoRequestsError

from pretaverdi.client import (
    get_climate_projections,
    get_forecast,
    get_historical_weather,
)
from pretaverdi.variables import (
    AGRI_DAILY_DEFAULTS,
    CLIMATE_DEFAULT_MODELS,
    CLIMATE_DEFAULTS,
)

pytestmark = pytest.mark.live


def test_archive_defaults_roundtrip():
    df = get_historical_weather(-34.6, -58.4, "2024-01-01", "2024-01-10")

    assert df.columns.tolist() == AGRI_DAILY_DEFAULTS
    assert len(df) == 10
    assert not df.isna().all().any()  # no variable came back all-null


def test_invalid_daily_variable_raises():
    # Bare soil moisture names are hourly-only; the daily API rejects them
    # (see docs/data-quality-report.md, Archive API data-contract note).
    with pytest.raises(OpenMeteoRequestsError):
        get_historical_weather(
            -34.6,
            -58.4,
            "2024-01-01",
            "2024-01-10",
            variables=["soil_moisture_0_to_7cm"],
        )


def test_climate_multimodel_parses_with_model_labels():
    df = get_climate_projections(-34.6, -58.4, "2030-01-01", "2030-01-10")

    assert isinstance(df.columns, pd.MultiIndex)
    assert set(df.columns.get_level_values("model")) == set(CLIMATE_DEFAULT_MODELS)
    assert df.shape == (10, len(CLIMATE_DEFAULTS) * len(CLIMATE_DEFAULT_MODELS))
    assert not df["temperature_2m_max"].isna().all().any()  # every model has data


def test_forecast_smoke():
    df = get_forecast(-34.6, -58.4, forecast_days=1)

    assert df.columns.tolist() == AGRI_DAILY_DEFAULTS
    assert len(df) == 1
