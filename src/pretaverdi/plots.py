"""Figures over analysis frames."""

import matplotlib.pyplot as plt
import pandas as pd

# Colour and marker shape both change, so the two versions stay apart in
# greyscale and under colour-vision deficiency.
_VERSIONS = [
    ("raw − ref", "C1", "o", "Raw model output"),
    ("served − ref", "C0", "s", "Served (bias-corrected)"),
]


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
