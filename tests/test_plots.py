"""Smoke tests for the pretaverdi plots module."""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from pretaverdi.plots import plot_bias

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
