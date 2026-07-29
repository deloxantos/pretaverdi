"""Tests for the pretaverdi client module."""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from pretaverdi.client import (
    get_climate_projections,
    get_forecast,
    get_historical_weather,
    log_query,
)
from pretaverdi.variables import (
    AGRI_DAILY_DEFAULTS,
    ARCHIVE_API_URL,
    CLIMATE_API_URL,
    CLIMATE_DEFAULTS,
    FORECAST_API_URL,
    SOIL_MOISTURE_MODELS,
)


def _mock_daily(num_vars: int, num_days: int = 10):
    """Create a mock Daily response object."""
    daily = MagicMock()
    # Time as unix timestamps (seconds since epoch)
    daily.Time.return_value = 1704067200  # 2024-01-01 00:00:00 UTC
    daily.TimeEnd.return_value = 1704067200 + num_days * 86400
    daily.Interval.return_value = 86400  # daily
    daily.VariablesLength.return_value = num_vars

    def make_var(idx):
        var = MagicMock()
        var.ValuesAsNumpy.return_value = np.random.rand(num_days).astype(np.float32)
        return var

    daily.Variables.side_effect = make_var
    return daily


def _mock_response(num_vars: int, num_days: int = 10):
    """Create a mock Open-Meteo API response."""
    response = MagicMock()
    response.Daily.return_value = _mock_daily(num_vars, num_days)
    return response


class TestGetHistoricalWeather:
    @patch("pretaverdi.client._get_session")
    def test_returns_dataframe(self, mock_session):
        num_vars = len(AGRI_DAILY_DEFAULTS)
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [_mock_response(num_vars)]
        mock_session.return_value = mock_client

        df = get_historical_weather(-34.6, -58.4, "2024-01-01", "2024-01-10")

        assert isinstance(df, pd.DataFrame)
        assert df.index.name == "date"
        assert len(df.columns) == num_vars

    @patch("pretaverdi.client._get_session")
    def test_uses_default_variables(self, mock_session):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [
            _mock_response(len(AGRI_DAILY_DEFAULTS))
        ]
        mock_session.return_value = mock_client

        get_historical_weather(-34.6, -58.4, "2024-01-01", "2024-01-10")

        call_args = mock_client.weather_api.call_args
        assert call_args[0][0] == ARCHIVE_API_URL
        assert call_args[1]["params"]["daily"] == AGRI_DAILY_DEFAULTS

    @patch("pretaverdi.client._get_session")
    def test_custom_variables(self, mock_session):
        custom_vars = ["temperature_2m_max", "precipitation_sum"]
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [_mock_response(len(custom_vars))]
        mock_session.return_value = mock_client

        df = get_historical_weather(
            -34.6, -58.4, "2024-01-01", "2024-01-10", variables=custom_vars
        )

        assert len(df.columns) == len(custom_vars)


class TestGetClimateProjections:
    @patch("pretaverdi.client._get_session")
    def test_returns_dataframe(self, mock_session):
        num_vars = len(CLIMATE_DEFAULTS)
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [_mock_response(num_vars)]
        mock_session.return_value = mock_client

        df = get_climate_projections(-34.6, -58.4, "2030-01-01", "2030-12-31")

        assert isinstance(df, pd.DataFrame)
        assert df.index.name == "date"

    @patch("pretaverdi.client._get_session")
    def test_uses_default_models(self, mock_session):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [
            _mock_response(len(CLIMATE_DEFAULTS))
        ]
        mock_session.return_value = mock_client

        get_climate_projections(-34.6, -58.4, "2030-01-01", "2030-12-31")

        call_args = mock_client.weather_api.call_args
        assert call_args[0][0] == CLIMATE_API_URL
        assert call_args[1]["params"]["models"] == SOIL_MOISTURE_MODELS


class TestGetForecast:
    @patch("pretaverdi.client._get_session")
    def test_returns_dataframe(self, mock_session):
        num_vars = len(AGRI_DAILY_DEFAULTS)
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [_mock_response(num_vars, num_days=14)]
        mock_session.return_value = mock_client

        df = get_forecast(-34.6, -58.4)

        assert isinstance(df, pd.DataFrame)
        assert df.index.name == "date"

    @patch("pretaverdi.client._get_session")
    def test_custom_forecast_days(self, mock_session):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [
            _mock_response(len(AGRI_DAILY_DEFAULTS), num_days=7)
        ]
        mock_session.return_value = mock_client

        get_forecast(-34.6, -58.4, forecast_days=7)

        call_args = mock_client.weather_api.call_args
        assert call_args[1]["params"]["forecast_days"] == 7


class TestLogQuery:
    def test_logs_to_file(self, isolated_cache):
        log_query(ARCHIVE_API_URL, {"latitude": -34.6, "longitude": -58.4}, (10, 7))

        lines = isolated_cache.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["endpoint"] == ARCHIVE_API_URL
        assert entry["response_shape"] == [10, 7]
        assert "timestamp" in entry

    def test_appends_multiple_entries(self, isolated_cache):
        log_query(ARCHIVE_API_URL, {"lat": 1}, (5, 3))
        log_query(FORECAST_API_URL, {"lat": 2}, (10, 7))

        lines = isolated_cache.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_excludes_apikey(self, isolated_cache):
        log_query(ARCHIVE_API_URL, {"lat": 1, "apikey": "secret"}, (5, 3))

        entry = json.loads(isolated_cache.read_text().strip())
        assert "apikey" not in entry["params"]


class TestResponseGuards:
    @patch("pretaverdi.client._get_session")
    def test_empty_response_raises_clear_error(self, mock_session):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = []
        mock_session.return_value = mock_client

        with pytest.raises(RuntimeError, match="no results"):
            get_forecast(-34.6, -58.4)

    @patch("pretaverdi.client._get_session")
    def test_variable_count_mismatch_raises(self, mock_session):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [_mock_response(3)]
        mock_session.return_value = mock_client

        with pytest.raises(RuntimeError, match="expected 7"):
            get_historical_weather(-34.6, -58.4, "2024-01-01", "2024-01-10")

    @patch("pretaverdi.client._get_session")
    def test_multi_model_climate_request_raises_with_hint(self, mock_session):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [_mock_response(6)]
        mock_session.return_value = mock_client

        with pytest.raises(RuntimeError, match="multi-model"):
            get_climate_projections(-34.6, -58.4, "2030-01-01", "2030-12-31")


class TestInputValidation:
    def test_rejects_latitude_out_of_range(self):
        with pytest.raises(ValueError, match="latitude"):
            get_historical_weather(-91, -58.4, "2024-01-01", "2024-01-10")

    def test_rejects_longitude_out_of_range(self):
        with pytest.raises(ValueError, match="longitude"):
            get_forecast(-34.6, 181)

    def test_rejects_bad_date_format(self):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            get_historical_weather(-34.6, -58.4, "01-01-2024", "2024-01-10")

    def test_rejects_start_after_end(self):
        with pytest.raises(ValueError, match="after"):
            get_climate_projections(-34.6, -58.4, "2031-01-01", "2030-01-01")

    def test_rejects_forecast_days_out_of_range(self):
        with pytest.raises(ValueError, match="forecast_days"):
            get_forecast(-34.6, -58.4, forecast_days=17)


class TestSessionReuse:
    def test_get_session_returns_same_client(self):
        import pretaverdi.client as client_module

        first = client_module._get_session()
        second = client_module._get_session()

        assert first is second


class TestFetchLogging:
    @patch("pretaverdi.client._get_session")
    def test_fetch_writes_query_log(self, mock_session, isolated_cache):
        mock_client = MagicMock()
        mock_client.weather_api.return_value = [
            _mock_response(len(AGRI_DAILY_DEFAULTS))
        ]
        mock_session.return_value = mock_client

        get_historical_weather(-34.6, -58.4, "2024-01-01", "2024-01-10")

        entries = isolated_cache.read_text().strip().split("\n")
        assert len(entries) == 1
        assert json.loads(entries[0])["endpoint"] == ARCHIVE_API_URL
