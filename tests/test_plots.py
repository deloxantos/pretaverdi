"""Smoke tests for the pretaverdi plots module."""

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from pretaverdi.plots import _LINESTYLES, _MARKERS, plot_bias, plot_decadal_change, plot_model_spread

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


def _decadal_change_frame():
    """Two-panel two-row (panel, row) frame shaped like stacked decadal_change output."""
    temperature = pd.DataFrame(
        {
            "A": [1.5, -0.5],
            "B": [1.0, -1.0],
            "C": [0.7, -1.3],
            "mean": [1.1, -0.9],
            "spread": [0.8, 0.8],
        },
        index=pd.Index(["Pampa", "Kenya"], name="row"),
    )
    precipitation = pd.DataFrame(
        {
            "A": [40.0, -20.0],
            "B": [30.0, -25.0],
            "C": [25.0, -30.0],
            "mean": [31.7, -25.0],
            "spread": [15.0, 10.0],
        },
        index=pd.Index(["Pampa", "Kenya"], name="row"),
    )
    return pd.concat(
        {"Temperature (°C)": temperature, "Precipitation (%)": precipitation},
        names=["panel"],
    )


class TestPlotDecadalChange:
    def test_returns_a_figure(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        assert isinstance(fig, plt.Figure)

    def test_one_axis_per_panel(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        assert len(fig.axes) == 2

    def test_axis_title_is_the_panel_label(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        assert fig.axes[0].get_title() == "Temperature (°C)"

    def test_first_row_is_on_top(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        ax = fig.axes[0]
        assert (ax.get_yticklabels()[0].get_text(), ax.yaxis_inverted()) == ("Pampa", True)

    def test_range_segment_ignores_mean_and_spread(self):
        row = pd.DataFrame(
            {"A": [1.0], "B": [2.0], "C": [3.0], "mean": [50.0], "spread": [-50.0]},
            index=pd.Index(["Pampa"], name="row"),
        )
        frame = pd.concat({"Temperature (°C)": row}, names=["panel"])

        fig = plot_decadal_change(frame, "title")

        range_line = next(
            line for line in fig.axes[0].get_lines() if line.get_label() == "Model range"
        )
        assert (min(range_line.get_xdata()), max(range_line.get_xdata())) == (1.0, 3.0)

    def test_one_marker_per_model_with_distinct_shapes(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        markers_by_model = [
            {line.get_marker() for line in fig.axes[0].get_lines() if line.get_label() == model}
            for model in ("A", "B", "C")
        ]
        assert markers_by_model == [{marker} for marker in _MARKERS]

    def test_equal_changes_do_not_overlap(self):
        row = pd.DataFrame(
            {"A": [1.0], "B": [1.0], "C": [2.0], "mean": [1.3], "spread": [1.0]},
            index=pd.Index(["Pampa"], name="row"),
        )
        frame = pd.concat({"Temperature (°C)": row}, names=["panel"])

        fig = plot_decadal_change(frame, "title")

        y_positions = {
            line.get_ydata()[0]
            for line in fig.axes[0].get_lines()
            if line.get_label() in ("A", "B")
        }
        assert len(y_positions) == 2

    def test_mean_tick_sits_at_the_ensemble_mean(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        mean_line = next(
            line for line in fig.axes[0].get_lines() if line.get_label() == "Ensemble mean"
        )
        assert mean_line.get_xdata()[0] == 1.1

    def test_zero_line_on_every_axis(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        assert all(
            any(list(line.get_xdata()) == [0, 0] for line in ax.get_lines()) for ax in fig.axes
        )

    def test_axes_share_x_when_asked(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming", sharex=True)

        assert fig.axes[0].get_shared_x_axes().joined(fig.axes[0], fig.axes[1])

    def test_xlabel_set_when_given(self):
        fig = plot_decadal_change(
            _decadal_change_frame(), "Models agree on warming", xlabel="Change"
        )

        assert all(ax.get_xlabel() == "Change" for ax in fig.axes)

    def test_single_figure_level_legend(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        assert len(fig.legends) == 1

    def test_suptitle_is_the_title(self):
        fig = plot_decadal_change(_decadal_change_frame(), "Models agree on warming")

        assert fig.get_suptitle() == "Models agree on warming"
