"""Smoke tests for the pretaverdi plots module."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from pretaverdi.plots import _LINESTYLES, plot_bias, plot_model_spread

matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def close_figures():
    """Never leak figures between tests."""
    yield
    plt.close("all")


def _levels_frame(sites=("Pampa",)):
    """Minimal (site, model) frame shaped like stacked mean_levels output."""
    site_levels = pd.DataFrame(
        {"raw − ref": [0.7, -0.1], "served − ref": [-0.1, -0.2]},
        index=pd.Index(["A", "B"], name="model"),
    )
    return pd.concat({site: site_levels for site in sites}, names=["site"])


def _legend_labels(fig):
    return [text.get_text() for text in fig.legends[0].get_texts()]


def test_returns_a_figure():
    fig = plot_bias(_levels_frame())

    assert isinstance(fig, plt.Figure)


def test_one_axis_per_site():
    fig = plot_bias(_levels_frame(sites=("Pampa", "Central Kenya")))

    assert len(fig.axes) == 2


def test_axis_title_names_the_site():
    fig = plot_bias(_levels_frame())

    assert fig.axes[0].get_title() == "Model bias — Pampa"


def test_x_axis_lists_the_models():
    fig = plot_bias(_levels_frame())

    assert [tick.get_text() for tick in fig.axes[0].get_xticklabels()] == ["A", "B"]


def test_legend_lists_both_versions_and_the_reference():
    fig = plot_bias(_levels_frame())

    assert _legend_labels(fig) == [
        "Raw model output",
        "Served (bias-corrected)",
        "ERA5-Land (reference)",
    ]


def test_reference_label_is_configurable():
    fig = plot_bias(_levels_frame(), reference_label="ERA5 (reference)")

    assert _legend_labels(fig)[-1] == "ERA5 (reference)"


def _spread_frame(sites=("Pampa", "Kenya"), models=("A", "B", "C")):
    """Two-site three-model (site, model) frame shaped like a stacked annual frame."""
    values = {"A": [10.0, 11.0, 12.0], "B": [12.0, 13.0, 14.0], "C": [15.0, 16.0, 18.0]}
    years = pd.Index([2020, 2021, 2022], name="year")
    site_frame = pd.DataFrame({model: values[model] for model in models}, index=years)
    return pd.concat({site: site_frame for site in sites}, axis=1, names=["site"])


class TestPlotModelSpread:
    def test_returns_a_figure(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        assert isinstance(fig, plt.Figure)

    def test_one_axis_per_site(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        assert len(fig.axes) == 2

    def test_axes_share_x(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        assert fig.axes[0].get_shared_x_axes().joined(fig.axes[0], fig.axes[1])

    def test_band_spans_min_to_max(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        band_y = fig.axes[0].collections[0].get_paths()[0].vertices[:, 1]
        assert (band_y.min(), band_y.max()) == (10.0, 18.0)

    def test_one_line_per_model(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        assert len(fig.axes[0].get_lines()) == 3

    def test_models_have_distinct_linestyles(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        assert [line.get_linestyle() for line in fig.axes[0].get_lines()] == _LINESTYLES

    def test_divider_drawn_when_year_given(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread", divider_year=2021)

        lines = fig.axes[0].get_lines()
        assert any(list(line.get_xdata()) == [2021, 2021] for line in lines)

    def test_divider_omitted_when_none(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread", divider_year=None)

        assert len(fig.axes[0].texts) == 0

    def test_single_figure_level_legend(self):
        fig = plot_model_spread(_spread_frame(), "°C", "Model spread")

        assert len(fig.legends) == 1

    def test_nan_year_leaves_a_gap_in_the_line(self):
        site_frame = pd.DataFrame(
            {"A": [10.0, float("nan"), 12.0]},
            index=pd.Index([2020, 2021, 2022], name="year"),
        )
        frame = pd.concat({"Pampa": site_frame}, axis=1, names=["site"])

        fig = plot_model_spread(frame, "°C", "Model spread")

        assert np.isnan(fig.axes[0].get_lines()[0].get_ydata()[1])
