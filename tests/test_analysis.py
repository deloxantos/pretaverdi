"""Tests for the pretaverdi analysis module."""

from unittest.mock import patch

import pandas as pd

from pretaverdi.analysis import (
    TEMPERATURE_VARIABLES,
    annual_mean_temperature,
    annual_precipitation,
    decadal_change,
    hindcast_annual,
    inter_model_spread,
    mean_levels,
    nan_share,
)


def _daily_frame(means_by_year: dict[int, float], spread: float = 5.0):
    """Daily tmax/tmin frame whose (tmax + tmin) / 2 is flat within each year."""
    index = pd.date_range("2020-01-01", "2021-12-31", freq="D", name="date")
    base = pd.Series([means_by_year[ts.year] for ts in index], index=index)
    return pd.DataFrame(
        {"temperature_2m_max": base + spread, "temperature_2m_min": base - spread}
    )


def _multi_model_daily_frame(means_by_model: dict[str, dict[int, float]]):
    """(variable, model) MultiIndex frame, one daily frame per model."""
    frames = {model: _daily_frame(means) for model, means in means_by_model.items()}
    df = pd.concat(frames, axis=1).swaplevel(axis=1)
    df = df[
        [(var, model) for var in TEMPERATURE_VARIABLES for model in means_by_model]
    ]
    df.columns.names = ["variable", "model"]
    return df


def _precip_frame(values: list[float], start: str = "2020-01-01") -> pd.DataFrame:
    """Daily precipitation_sum frame, one row per value starting at `start`."""
    index = pd.date_range(start, periods=len(values), freq="D", name="date")
    return pd.DataFrame({"precipitation_sum": values}, index=index)


def _multi_model_precip_frame(values_by_model: dict[str, list[float]]):
    """(variable, model) MultiIndex precipitation frame, one series per model."""
    frames = {model: _precip_frame(values) for model, values in values_by_model.items()}
    df = pd.concat(frames, axis=1).swaplevel(axis=1)
    df.columns.names = ["variable", "model"]
    return df


def _annual_frame(values_by_model: dict[str, dict[int, float]]) -> pd.DataFrame:
    """Year-indexed frame with one column per model, shaped like annual_mean_temperature output."""
    return pd.DataFrame(values_by_model)


def _stacked_annual_frame(
    values_by_site: dict[str, dict[str, dict[int, float]]],
) -> pd.DataFrame:
    """(site, model) MultiIndex frame, built the way callers stack per-site annual frames."""
    return pd.concat(
        {site: _annual_frame(models) for site, models in values_by_site.items()},
        axis=1,
        names=["site"],
    )


def _hindcast_frame(raw: dict, served: dict, reference: dict, years=(2020, 2021)):
    """Year-indexed (version, model) frame shaped like hindcast_annual output."""
    index = pd.Index(years, name="date")
    frame = pd.concat(
        {
            "raw": pd.DataFrame(raw, index=index),
            "served": pd.DataFrame(served, index=index),
            "reference": pd.DataFrame(reference, index=index),
        },
        axis=1,
    )
    frame.columns.names = ["version", "model"]
    return frame


class TestAnnualMeanTemperature:
    def test_flat_frame_returns_series(self):
        annual = annual_mean_temperature(_daily_frame({2020: 15.0, 2021: 17.0}))

        assert isinstance(annual, pd.Series)

    def test_flat_frame_averages_max_and_min(self):
        annual = annual_mean_temperature(_daily_frame({2020: 15.0, 2021: 17.0}))

        assert annual.tolist() == [15.0, 17.0]

    def test_index_is_integer_year(self):
        annual = annual_mean_temperature(_daily_frame({2020: 15.0, 2021: 17.0}))

        assert annual.index.tolist() == [2020, 2021]

    def test_multimodel_frame_returns_year_by_model_frame(self):
        annual = annual_mean_temperature(
            _multi_model_daily_frame(
                {"A": {2020: 15.0, 2021: 17.0}, "B": {2020: 16.0, 2021: 18.0}}
            )
        )

        assert annual.columns.tolist() == ["A", "B"]

    def test_multimodel_frame_averages_each_model(self):
        annual = annual_mean_temperature(
            _multi_model_daily_frame(
                {"A": {2020: 15.0, 2021: 17.0}, "B": {2020: 16.0, 2021: 18.0}}
            )
        )

        assert annual["B"].tolist() == [16.0, 18.0]


class TestAnnualPrecipitation:
    def test_full_year_sums_precipitation(self):
        annual = annual_precipitation(_precip_frame([1.0] * 366, start="2020-01-01"))

        assert annual.loc[2020] == 366.0

    def test_year_below_min_valid_days_becomes_nan(self):
        annual = annual_precipitation(_precip_frame([5.0] * 100, start="2020-01-01"))

        assert pd.isna(annual.loc[2020])

    def test_year_below_floor_becomes_nan(self):
        annual = annual_precipitation(_precip_frame([0.5] * 366, start="2020-01-01"))

        assert pd.isna(annual.loc[2020])

    def test_floor_none_keeps_low_totals(self):
        annual = annual_precipitation(
            _precip_frame([0.5] * 366, start="2020-01-01"), floor_mm=None
        )

        assert annual.loc[2020] == 183.0

    def test_all_nan_year_with_min_valid_days_zero_returns_zero(self):
        annual = annual_precipitation(
            _precip_frame([float("nan")] * 366, start="2020-01-01"),
            min_valid_days=0,
            floor_mm=None,
        )

        assert annual.loc[2020] == 0.0

    def test_index_is_integer_year(self):
        df = pd.concat(
            [
                _precip_frame([1.0] * 366, start="2020-01-01"),
                _precip_frame([1.0] * 365, start="2021-01-01"),
            ]
        )

        annual = annual_precipitation(df)

        assert annual.index.tolist() == [2020, 2021]

    def test_multimodel_frame_returns_year_by_model_frame(self):
        annual = annual_precipitation(
            _multi_model_precip_frame({"A": [1.0] * 366, "B": [2.0] * 366})
        )

        assert annual.columns.tolist() == ["A", "B"]


@patch("pretaverdi.analysis.get_historical_weather")
@patch("pretaverdi.analysis.get_climate_projections")
class TestHindcastAnnual:
    location = {"lat": -34.6, "lon": -58.4, "name": "Pampa, Argentina"}

    @staticmethod
    def _wire(mock_projections, mock_historical):
        mock_projections.return_value = _multi_model_daily_frame(
            {"A": {2020: 15.0, 2021: 17.0}, "B": {2020: 16.0, 2021: 18.0}}
        )
        mock_historical.return_value = _daily_frame({2020: 14.0, 2021: 16.0})

    def test_columns_cover_both_versions_and_the_reference(
        self, mock_projections, mock_historical
    ):
        self._wire(mock_projections, mock_historical)

        annual = hindcast_annual(self.location)

        assert annual.columns.tolist() == [
            ("raw", "A"),
            ("raw", "B"),
            ("served", "A"),
            ("served", "B"),
            ("reference", "era5_land"),
        ]

    def test_column_levels_are_named(self, mock_projections, mock_historical):
        self._wire(mock_projections, mock_historical)

        annual = hindcast_annual(self.location)

        assert list(annual.columns.names) == ["version", "model"]

    def test_index_is_integer_year(self, mock_projections, mock_historical):
        self._wire(mock_projections, mock_historical)

        annual = hindcast_annual(self.location)

        assert annual.index.tolist() == [2020, 2021]

    def test_one_projection_fetch_disables_bias_correction(
        self, mock_projections, mock_historical
    ):
        self._wire(mock_projections, mock_historical)

        hindcast_annual(self.location)

        flags = [
            call.kwargs.get("disable_bias_correction", False)
            for call in mock_projections.call_args_list
        ]
        assert sorted(flags) == [False, True]

    def test_reference_defaults_to_era5_land(
        self, mock_projections, mock_historical
    ):
        self._wire(mock_projections, mock_historical)

        hindcast_annual(self.location)

        assert mock_historical.call_args.kwargs["model"] == "era5_land"

    def test_fetches_temperature_variables_only(
        self, mock_projections, mock_historical
    ):
        self._wire(mock_projections, mock_historical)

        hindcast_annual(self.location)

        assert mock_projections.call_args.kwargs["variables"] == TEMPERATURE_VARIABLES

    def test_models_default_to_the_client_default(
        self, mock_projections, mock_historical
    ):
        self._wire(mock_projections, mock_historical)

        hindcast_annual(self.location)

        assert mock_projections.call_args.kwargs["models"] is None


class TestMeanLevels:
    hindcast = _hindcast_frame(
        raw={"A": [10.0, 12.0], "B": [14.0, 16.0]},
        served={"A": [11.0, 13.0], "B": [13.0, 15.0]},
        reference={"era5_land": [12.0, 14.0]},
    )

    def test_index_lists_the_models(self):
        levels = mean_levels(self.hindcast)

        assert levels.index.tolist() == ["A", "B"]

    def test_columns_pair_levels_with_deltas(self):
        levels = mean_levels(self.hindcast)

        assert levels.columns.tolist() == [
            "raw",
            "served",
            "reference",
            "raw − ref",
            "served − ref",
        ]

    def test_levels_are_period_means(self):
        levels = mean_levels(self.hindcast)

        assert levels["raw"].tolist() == [11.0, 15.0]

    def test_reference_is_shared_by_every_model(self):
        levels = mean_levels(self.hindcast)

        assert levels["reference"].tolist() == [13.0, 13.0]

    def test_deltas_are_relative_to_the_reference(self):
        levels = mean_levels(self.hindcast)

        assert levels["served − ref"].tolist() == [-1.0, 1.0]

    def test_values_are_rounded_to_two_decimals(self):
        hindcast = _hindcast_frame(
            raw={"A": [10.0, 11.0, 11.0], "B": [14.0, 16.0, 15.0]},
            served={"A": [11.0, 13.0, 12.0], "B": [13.0, 15.0, 14.0]},
            reference={"era5_land": [12.0, 14.0, 13.0]},
            years=(2020, 2021, 2022),
        )

        levels = mean_levels(hindcast)

        assert levels.loc["A", "raw"] == 10.67

    def test_float32_input_rounds_to_clean_decimals(self):
        hindcast = _hindcast_frame(
            raw={"A": [17.64, 17.64], "B": [18.45, 18.45]},
            served={"A": [17.49, 17.49], "B": [17.64, 17.64]},
            reference={"era5_land": [17.74, 17.74]},
        ).astype("float32")

        levels = mean_levels(hindcast)

        assert levels.loc["A", "raw"] == 17.64


class TestInterModelSpread:
    levels = pd.DataFrame(
        {"raw": [11.0, 15.0], "served": [12.0, 14.0], "reference": [13.0, 13.0]},
        index=pd.Index(["A", "B"], name="model"),
    )

    def test_plain_model_index_returns_a_series(self):
        spread = inter_model_spread(self.levels)

        assert spread.index.tolist() == ["raw", "served"]

    def test_spread_is_max_minus_min_across_models(self):
        spread = inter_model_spread(self.levels)

        assert spread["raw"] == 4.0

    def test_site_index_returns_one_row_per_site(self):
        stacked = pd.concat(
            {"pampa_ar": self.levels, "kenya_ea": self.levels}, names=["site"]
        )

        spread = inter_model_spread(stacked)

        assert spread.index.tolist() == ["pampa_ar", "kenya_ea"]

    def test_site_rows_carry_both_versions(self):
        stacked = pd.concat(
            {"pampa_ar": self.levels, "kenya_ea": self.levels}, names=["site"]
        )

        spread = inter_model_spread(stacked)

        assert spread.columns.tolist() == ["raw", "served"]

    def test_site_spread_is_computed_within_each_site(self):
        stacked = pd.concat(
            {"pampa_ar": self.levels, "kenya_ea": self.levels * 2}, names=["site"]
        )

        spread = inter_model_spread(stacked)

        assert spread.loc["kenya_ea", "raw"] == 8.0

    def test_values_are_rounded_to_two_decimals(self):
        levels = pd.DataFrame(
            {"raw": [10.0, 10.0 + 1 / 3], "served": [12.0, 14.0]},
            index=pd.Index(["A", "B"], name="model"),
        )

        spread = inter_model_spread(levels)

        assert spread["raw"] == 0.33


class TestNanShare:
    def test_values_are_percentages(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0, None]})

        share = nan_share(df)

        assert share["a"] == 50.0

    def test_fully_missing_column_is_100(self):
        df = pd.DataFrame({"a": [None, None, None]})

        share = nan_share(df)

        assert share["a"] == 100.0

    def test_values_rounded_to_one_decimal(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0]})

        share = nan_share(df)

        assert share["a"] == 33.3

    def test_index_keeps_variable_and_model_names(self):
        df = _multi_model_precip_frame({"A": [1.0, 2.0], "B": [float("nan"), 3.0]})

        share = nan_share(df)

        assert share.index.names == ["variable", "model"]

    def test_series_is_named_percent_nan(self):
        df = pd.DataFrame({"a": [1.0, None]})

        share = nan_share(df)

        assert share.name == "% NaN"


class TestDecadalChange:
    def test_change_is_late_mean_minus_early_mean(self):
        annual = _annual_frame(
            {"A": {2015: 10.0, 2016: 12.0, 2041: 14.0, 2042: 16.0}}
        )

        change = decadal_change(annual, early=(2015, 2016), late=(2041, 2042))

        assert change["A"] == 4.0

    def test_mean_is_average_of_model_changes(self):
        annual = _annual_frame(
            {"A": {2015: 10.0, 2041: 14.0}, "B": {2015: 10.0, 2041: 12.0}}
        )

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert change["mean"] == 3.0

    def test_spread_is_max_minus_min_of_model_changes(self):
        annual = _annual_frame(
            {"A": {2015: 10.0, 2041: 14.0}, "B": {2015: 10.0, 2041: 12.0}}
        )

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert change["spread"] == 2.0

    def test_values_rounded_to_one_decimal(self):
        annual = _annual_frame(
            {
                "A": {
                    2015: 10.0,
                    2016: 10.0,
                    2017: 10.0,
                    2041: 11.0,
                    2042: 11.0,
                    2043: 12.0,
                }
            }
        )

        change = decadal_change(annual, early=(2015, 2017), late=(2041, 2043))

        assert change["A"] == 1.3

    def test_float32_input_rounds_to_clean_decimals(self):
        annual = _annual_frame({"A": {2015: 17.64, 2041: 18.45}}).astype("float32")

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert change["A"] == 0.8

    def test_nan_year_in_late_window_is_skipped(self):
        annual = _annual_frame(
            {"A": {2015: 10.0, 2041: 10.0, 2042: float("nan"), 2043: 14.0}}
        )

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2043))

        assert change["A"] == 2.0

    def test_stacked_sites_return_one_row_per_site(self):
        annual = _stacked_annual_frame(
            {
                "kenya_ea": {"A": {2015: 10.0, 2041: 12.0}},
                "pampa_ar": {"A": {2015: 10.0, 2041: 14.0}},
            }
        )

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert change.index.tolist() == ["kenya_ea", "pampa_ar"]

    def test_stacked_columns_are_models_plus_mean_and_spread(self):
        annual = _stacked_annual_frame(
            {
                "kenya_ea": {"A": {2015: 10.0, 2041: 12.0}, "B": {2015: 10.0, 2041: 14.0}},
                "pampa_ar": {"A": {2015: 10.0, 2041: 14.0}, "B": {2015: 10.0, 2041: 16.0}},
            }
        )

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert change.columns.tolist() == ["A", "B", "mean", "spread"]

    def test_stacked_matches_single_site_call(self):
        models = {"A": {2015: 10.0, 2041: 14.0}, "B": {2015: 10.0, 2041: 12.0}}
        annual = _stacked_annual_frame({"pampa_ar": models})

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert (
            change.loc["pampa_ar"].tolist()
            == decadal_change(
                _annual_frame(models), early=(2015, 2015), late=(2041, 2041)
            ).tolist()
        )

    def test_stacked_sites_keep_given_order(self):
        annual = _stacked_annual_frame(
            {
                "pampa_ar": {"A": {2015: 10.0, 2041: 14.0}},
                "kenya_ea": {"A": {2015: 10.0, 2041: 12.0}},
            }
        )

        change = decadal_change(annual, early=(2015, 2015), late=(2041, 2041))

        assert change.index.tolist() == ["pampa_ar", "kenya_ea"]
