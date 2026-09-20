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

# Fixed per model-position marker shape, cycled the same way as _LINESTYLES,
# for plots where models are points rather than trajectories.
_MARKERS = ["o", "s", "^"]


def plot_bias(
    levels: pd.DataFrame,
    reference_label: str = "ERA5-Land (reference)",
    title: str | None = None,
) -> plt.Figure:
    """Plot each model's bias before and after correction, one axis per site.

    Args:
        levels: `mean_levels` frames stacked by site with
            `pd.concat({...}, names=["site"])`.
        reference_label: Legend label for the zero line.
        title: Figure-level title; a sentence that states the conclusion.
            None draws no suptitle.

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
        ax.set_title(site)

    axes[0][0].set_ylabel("Difference from reference (°C)")
    if title is not None:
        fig.suptitle(title)
    # One shared legend below the axes: it can never sit on top of a data point.
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=3, fontsize=9)
    return fig


def plot_model_spread(
    annual: pd.DataFrame,
    ylabel: str,
    title: str,
    divider_year: float | None = None,
    year_notes: dict[float, str] | None = None,
) -> plt.Figure:
    """Plot each model's trajectory and the inter-model range, one axis per site.

    Args:
        annual: Year-indexed frame with (site, model) MultiIndex columns, as
            built by the caller with
            `pd.concat({site: annual_frame, ...}, axis=1, names=["site"])`.
        ylabel: Y-axis label, shown on every axis.
        title: Figure-level title; a sentence that states the conclusion.
        divider_year: Where to draw the divider: years to its left overlap
            the reanalysis record, years to its right are projection only.
            Drawn as a dashed line with a label at the bottom, on every
            axis. None skips the divider.
        year_notes: Year to short label, for years where a data gap would
            otherwise look like a plotting error — not the same thing as
            `divider_year`, which marks a boundary in the data's meaning
            rather than a gap in it. Drawn as thin dotted lines with a
            label at the top, on every axis. None skips the notes.

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
        ax.set_title(site)
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
        if year_notes is not None:
            for year, text in year_notes.items():
                ax.axvline(year, color="0.6", linestyle=":", linewidth=0.8)
                ax.annotate(
                    text,
                    xy=(year, 0.98),
                    xycoords=("data", "axes fraction"),
                    fontsize=9,
                    color="#555",
                    va="top",
                    rotation=90,
                    ha="right",
                )

    fig.suptitle(title)
    # One shared legend below the axes: it can never sit on top of a data point.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=4, fontsize=9)
    return fig


def _row_offsets(n_models: int) -> list[float]:
    """Deterministic vertical offsets so models sharing a rounded change stay visible.

    Args:
        n_models: Number of models to offset.

    Returns:
        One offset per model, evenly spaced within ±0.12, centred on 0.
    """
    if n_models <= 1:
        return [0.0] * n_models
    step = 0.24 / (n_models - 1)
    return [-0.12 + position * step for position in range(n_models)]


def plot_decadal_change(
    changes: pd.DataFrame, title: str, xlabel: str | None = None, sharex: bool = False
) -> plt.Figure:
    """Plot per-model decadal change as a forest plot: do models agree on the sign?

    Each row shows every model's change as a point on a shared axis, with a
    grey range bar and a black ensemble-mean tick. The zero line is the sign
    boundary: when a row's markers straddle it, the models disagree on
    whether the quantity increases or decreases, not just by how much.

    Args:
        changes: Rows are a 2-level (panel, row) MultiIndex, built by the
            caller with `pd.concat({"panel label": frame, ...})`; columns
            are what `analysis.decadal_change` returns for stacked sites:
            one column per model, then "mean" and "spread". Panels and rows
            keep the order given.
        title: Figure-level title; a sentence that states the conclusion.
        xlabel: X-axis label, set on every axis when given. Left as None
            when panels mix units — each panel then states its own unit in
            its title instead.
        sharex: Whether the panel axes share their x-axis. False by default,
            since panels commonly mix units.

    Returns:
        The Figure, unshown, so the caller decides where it goes.
    """
    panels = changes.index.get_level_values(0).unique()
    models = [column for column in changes.columns if column not in ("mean", "spread")]
    max_rows = changes.groupby(level=0, sort=False).size().max()

    fig, axes = plt.subplots(
        1,
        len(panels),
        figsize=(14, 1.6 + 0.9 * max_rows),
        layout="constrained",
        squeeze=False,
        sharex=sharex,
        sharey=False,
    )
    offsets = _row_offsets(len(models))
    for ax, panel in zip(axes[0], panels):
        panel_frame = changes.xs(panel, level=0, drop_level=True)
        positions = range(len(panel_frame))
        ax.set_yticks(list(positions), panel_frame.index.tolist())
        ax.invert_yaxis()

        for row_position, (_, row) in zip(positions, panel_frame.iterrows()):
            model_values = row[models]
            ax.plot(
                [model_values.min(), model_values.max()],
                [row_position, row_position],
                color="0.6",
                linewidth=3,
                alpha=0.6,
                zorder=1,
                label="Model range" if row_position == 0 else None,
            )
            for model_position, model in enumerate(models):
                ax.plot(
                    row[model],
                    row_position + offsets[model_position],
                    color=f"C{model_position}",
                    marker=_MARKERS[model_position % len(_MARKERS)],
                    markersize=9,
                    zorder=3,
                    label=model,
                )
            ax.plot(
                row["mean"],
                row_position,
                color="black",
                marker="|",
                markersize=18,
                markeredgewidth=2,
                linestyle="none",
                zorder=4,
                label="Ensemble mean",
            )

        ax.axvline(0, color="black", linestyle="--", linewidth=1)
        ax.margins(y=0.35)
        ax.set_title(panel)
        if xlabel is not None:
            ax.set_xlabel(xlabel)

    fig.suptitle(title)
    # One shared legend, de-duplicated: every row repeats the model and
    # ensemble-mean labels, but the legend should list each once.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(
        by_label.values(), by_label.keys(), loc="outside lower center", ncols=5, fontsize=9
    )
    return fig
