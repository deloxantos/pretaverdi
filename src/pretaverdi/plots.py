"""Figures over analysis frames."""

import matplotlib.pyplot as plt
import pandas as pd

# Colour and marker shape both change, so the two versions stay apart in
# greyscale and under colour-vision deficiency.
_VERSIONS = [
    ("raw − ref", "C1", "o", "Raw model output"),
    ("served − ref", "C0", "s", "Served (bias-corrected)"),
]

# Fixed per model-position line style, cycled if there are more models than
# styles, so models stay distinguishable without relying on colour.
_LINESTYLES = ["-", "--", "-."]


def plot_bias(
    levels: pd.DataFrame, reference_label: str = "ERA5-Land (reference)"
) -> plt.Figure:
    """Plot each model's bias before and after correction, one axis per site.

    Args:
        levels: `mean_levels` frames stacked by site with
            `pd.concat({...}, names=["site"])`.
        reference_label: Legend label for the zero line.

    Returns:
        The Figure, unshown, so the caller decides where it goes.
    """
    sites = levels.index.get_level_values(0).unique()
    fig, axes = plt.subplots(
        1, len(sites), figsize=(14, 5), layout="constrained", sharey=True, squeeze=False
    )
    for ax, site in zip(axes[0], sites):
        bias = levels.loc[site]
        x = range(len(bias))
        ax.vlines(x, bias["raw − ref"], bias["served − ref"], color="gray", linewidth=1)
        for column, color, marker, label in _VERSIONS:
            ax.scatter(
                x, bias[column], color=color, marker=marker, s=90, label=label, zorder=2
            )
        ax.axhline(0, color="black", linestyle="--", linewidth=1.8, label=reference_label)
        ax.set_xticks(x, bias.index)
        ax.margins(x=0.25, y=0.15)
        ax.set_title(f"Model bias — {site}")

    axes[0][0].set_ylabel("Difference from reference (°C)")
    # One shared legend below the axes: it can never sit on top of a data point.
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=3, fontsize=9)
    return fig


def plot_model_spread(
    annual: pd.DataFrame,
    ylabel: str,
    title: str,
    divider_year: float | None = None,
) -> plt.Figure:
    """Plot each model's trajectory and the inter-model range, one axis per site.

    Args:
        annual: Year-indexed frame with (site, model) MultiIndex columns, as
            built by the caller with
            `pd.concat({site: annual_frame, ...}, axis=1, names=["site"])`.
        ylabel: Y-axis label, shown on every axis.
        title: Title prefix; each axis reads f"{title} — {site}".
        divider_year: Where to draw the divider: years to its left overlap
            the reanalysis record, years to its right are projection only.
            None skips the divider.

    Returns:
        The Figure, unshown, so the caller decides where it goes.
    """
    sites = annual.columns.get_level_values(0).unique()
    fig, axes = plt.subplots(
        len(sites),
        1,
        figsize=(14, 4.5 * len(sites)),
        layout="constrained",
        sharex=True,
        squeeze=False,
    )
    for ax, site in zip(axes[:, 0], sites):
        site_frame = annual[site]
        ax.fill_between(
            site_frame.index,
            site_frame.min(axis=1),
            site_frame.max(axis=1),
            alpha=0.25,
            label="Model range",
        )
        for position, model in enumerate(site_frame.columns):
            ax.plot(
                site_frame.index,
                site_frame[model],
                linewidth=1,
                linestyle=_LINESTYLES[position % len(_LINESTYLES)],
                label=model,
            )
        ax.set_title(f"{title} — {site}")
        ax.set_ylabel(ylabel)
        if divider_year is not None:
            ax.axvline(divider_year, color="gray", linestyle="--", linewidth=1)
            ax.text(
                divider_year,
                site_frame.min().min(),
                "  ← comparable to observations | projected →",
                fontsize=10,
                color="#555",
                va="bottom",
            )

    # One shared legend below the axes: it can never sit on top of a data point.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=4, fontsize=9)
    return fig
