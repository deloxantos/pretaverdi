"""Thin wrapper over openmeteo-requests for agri-climate data retrieval."""

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests_cache
from openmeteo_sdk.Model import Model as _Model
from retry_requests import retry

from pretaverdi.variables import (
    AGRI_DAILY_DEFAULTS,
    ARCHIVE_API_URL,
    CLIMATE_API_URL,
    CLIMATE_DEFAULT_MODELS,
    CLIMATE_DEFAULTS,
    FORECAST_API_URL,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(os.environ.get("PRETAVERDI_CACHE_DIR", _PROJECT_ROOT / ".cache"))
QUERY_LOG_PATH = CACHE_DIR / "query_log.jsonl"

# Reverse map: FlatBuffers model enum id -> API model name. The enum attribute
# names match the names the Climate API accepts (e.g. EC_Earth3P_HR = 46).
_MODEL_NAMES = {v: k for k, v in vars(_Model).items() if isinstance(v, int)}


def _validate_coords(lat: float, lon: float) -> None:
    """Reject coordinates outside valid WGS84 ranges."""
    if not -90 <= lat <= 90:
        raise ValueError(f"latitude must be in [-90, 90], got {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"longitude must be in [-180, 180], got {lon}")


def _validate_date_range(start_date: str, end_date: str) -> None:
    """Reject malformed dates or inverted ranges."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            "dates must be YYYY-MM-DD, got "
            f"start_date={start_date!r} end_date={end_date!r}"
        ) from exc
    if start > end:
        raise ValueError(f"start_date {start_date} is after end_date {end_date}")


@lru_cache(maxsize=1)
def _get_session() -> openmeteo_requests.Client:
    """Create an Open-Meteo client with cache and retry."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_session = requests_cache.CachedSession(
        str(CACHE_DIR / "open_meteo_cache"), expire_after=3600
    )
    retry_session = retry(cache_session, retries=3, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def log_query(endpoint: str, params: dict, response_shape: tuple[int, ...]) -> None:
    """Append query metadata to the local query log."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "params": {k: v for k, v in params.items() if k != "apikey"},
        "response_shape": list(response_shape),
    }
    with open(QUERY_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _daily_to_dataframe(daily, variables: list[str], url: str) -> pd.DataFrame:
    """Build a date-indexed frame from one response message's Daily block."""
    if daily.VariablesLength() != len(variables):
        raise RuntimeError(
            f"expected {len(variables)} variables in response from {url}, "
            f"got {daily.VariablesLength()}"
        )
    data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    # Open-Meteo returns variables in the requested order; the count guard
    # above rejects responses where that assumption cannot hold.
    for i, var in enumerate(variables):
        data[var] = daily.Variables(i).ValuesAsNumpy()

    return pd.DataFrame(data).set_index("date")


def _fetch_daily_dataframe(
    url: str, params: dict, variables: list[str]
) -> pd.DataFrame:
    """Invoke an Open-Meteo endpoint and build a date-indexed daily DataFrame."""
    client = _get_session()
    responses = client.weather_api(url, params=params)
    if not responses:
        raise RuntimeError(f"Open-Meteo returned no results for {url}")

    df = _daily_to_dataframe(responses[0].Daily(), variables, url)
    log_query(url, params, df.shape)
    return df


def _fetch_daily_multimodel(
    url: str, params: dict, variables: list[str], models: list[str]
) -> pd.DataFrame:
    """Fetch one message per model and assemble (variable, model) columns."""
    client = _get_session()
    responses = client.weather_api(url, params=params)
    if len(responses) != len(models):
        raise RuntimeError(
            f"expected one response per model ({len(models)}) from {url}, "
            f"got {len(responses)}"
        )
    frames = {
        _MODEL_NAMES.get(r.Model(), f"unknown_{r.Model()}"): _daily_to_dataframe(
            r.Daily(), variables, url
        )
        for r in responses
    }
    if set(frames) != set(models):
        raise RuntimeError(
            f"response models {sorted(frames)} do not match requested {models}"
        )
    df = pd.concat(frames, axis=1).swaplevel(axis=1)
    df = df[[(var, model) for var in variables for model in models]]
    df.columns.names = ["variable", "model"]
    log_query(url, params, df.shape)
    return df


def get_historical_weather(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    variables: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch historical weather data from Open-Meteo Archive API.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        variables: List of daily variable names. Defaults to AGRI_DAILY_DEFAULTS.

    Returns:
        DataFrame with date index and requested variables as columns.
    """
    _validate_coords(lat, lon)
    _validate_date_range(start_date, end_date)
    if variables is None:
        variables = AGRI_DAILY_DEFAULTS

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": variables,
        "timezone": "auto",
    }
    return _fetch_daily_dataframe(ARCHIVE_API_URL, params, variables)


def get_climate_projections(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    models: list[str] | None = None,
    variables: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch CMIP6 climate projections from Open-Meteo Climate API.

    The API returns one response message per requested model. With a single
    model the result keeps the flat shape of the other endpoints; with several
    models the columns become a (variable, model) MultiIndex, so e.g.
    ``df["temperature_2m_max"]`` is a date × models frame ready for
    min/mean/max spread bands across the ensemble.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        models: List of CMIP6 model names. Defaults to CLIMATE_DEFAULT_MODELS.
        variables: List of daily variable names. Defaults to CLIMATE_DEFAULTS.

    Returns:
        DataFrame with date index; flat variable columns for one model, or
        (variable, model) MultiIndex columns for several.
    """
    _validate_coords(lat, lon)
    _validate_date_range(start_date, end_date)
    if models is None:
        models = CLIMATE_DEFAULT_MODELS
    if variables is None:
        variables = CLIMATE_DEFAULTS

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "models": models,
        "daily": variables,
        "timezone": "auto",
    }
    if len(models) == 1:
        return _fetch_daily_dataframe(CLIMATE_API_URL, params, variables)
    return _fetch_daily_multimodel(CLIMATE_API_URL, params, variables, models)


def get_forecast(
    lat: float,
    lon: float,
    forecast_days: int = 14,
    variables: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch weather forecast from Open-Meteo Forecast API.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        forecast_days: Number of forecast days (1-16).
        variables: List of daily variable names. Defaults to AGRI_DAILY_DEFAULTS.

    Returns:
        DataFrame with date index and requested variables as columns.
    """
    _validate_coords(lat, lon)
    if not 1 <= forecast_days <= 16:
        raise ValueError(f"forecast_days must be in [1, 16], got {forecast_days}")
    if variables is None:
        variables = AGRI_DAILY_DEFAULTS

    params = {
        "latitude": lat,
        "longitude": lon,
        "forecast_days": forecast_days,
        "daily": variables,
        "timezone": "auto",
    }
    return _fetch_daily_dataframe(FORECAST_API_URL, params, variables)
