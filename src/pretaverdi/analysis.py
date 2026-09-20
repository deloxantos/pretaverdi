"""Transforms over client frames, plus the experiments that compose them."""

import pandas as pd

from pretaverdi.client import get_climate_projections, get_historical_weather

# Daily mean temperature needs both ends of the day; nothing else is fetched
# for the hindcast, so the requests stay small and the frames stay readable.
TEMPERATURE_VARIABLES = ["temperature_2m_max", "temperature_2m_min"]


def annual_mean_temperature(df: pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Reduce a daily tmax/tmin frame to annual mean temperature.

    Args:
        df: Date-indexed frame with flat variable columns, or with the
            (variable, model) MultiIndex columns of a multi-model fetch.

    Returns:
        Year-indexed Series for a flat frame; year × model DataFrame for a
        MultiIndex one.
    """
    tmean = (df["temperature_2m_max"] + df["temperature_2m_min"]) / 2
    annual = tmean.resample("YE").mean()
    annual.index = annual.index.year
    return annual


def annual_precipitation(
    df: pd.DataFrame,
    min_valid_days: int = 300,
    floor_mm: float | None = 300.0,
) -> pd.Series | pd.DataFrame:
    """Reduce a daily precipitation frame to annual totals, masking bad years.

    A partial year is not a total, so years with fewer than `min_valid_days`
    valid days are NaN. Some sites also log zero-precipitation days that are
    missing data stored as zeros, not weather — `floor_mm` masks annual
    totals implausibly low to catch that.

    Args:
        df: Date-indexed frame with a "precipitation_sum" column, flat or
            with the (variable, model) MultiIndex columns of a multi-model
            fetch.
        min_valid_days: Minimum number of valid daily values a year needs to
            report a total; short of that the year is NaN.
        floor_mm: Minimum plausible annual total; years below it become NaN.
            None skips this check and returns the raw totals.

    Returns:
        Year-indexed Series for a flat frame; year × model DataFrame for a
        MultiIndex one.
    """
    annual = df["precipitation_sum"].resample("YE").sum(min_count=min_valid_days)
    annual.index = annual.index.year
    if floor_mm is not None:
        annual = annual.mask(annual < floor_mm)
    return annual


def hindcast_annual(
    location: dict,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    models: list[str] | None = None,
    reference: str = "era5_land",
) -> pd.DataFrame:
    """Fetch the annual temperature a hindcast compares: models vs reanalysis.

    Fetches the same past period three times: the projections as Open-Meteo
    serves them (bias-corrected against ERA5-Land), the raw model output, and
    the reanalysis used as the reference. Comparing the three shows how much
    of the agreement with the reference comes from the correction.

    Args:
        location: A LOCATIONS-style mapping with `lat` and `lon`.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        models: List of CMIP6 model names. Defaults to the client's default.
        reference: Archive API reanalysis dataset to compare against.

    Returns:
        Year-indexed DataFrame with (version, model) columns: one pair per
        model for "raw" and "served", plus a single "reference" column.
    """
    lat, lon = location["lat"], location["lon"]
    fetched = {
        "raw": get_climate_projections(
            lat,
            lon,
            start_date,
            end_date,
            models=models,
            variables=TEMPERATURE_VARIABLES,
            disable_bias_correction=True,
        ),
        "served": get_climate_projections(
            lat,
            lon,
            start_date,
            end_date,
            models=models,
            variables=TEMPERATURE_VARIABLES,
        ),
    }
    annual = {version: annual_mean_temperature(df) for version, df in fetched.items()}
    # The reanalysis has no model dimension; name its column after the dataset
    # so the second column level stays meaningful across all three versions.
    annual["reference"] = annual_mean_temperature(
        get_historical_weather(
            lat,
            lon,
            start_date,
            end_date,
            variables=TEMPERATURE_VARIABLES,
            model=reference,
        )
    ).to_frame(reference)

    hindcast = pd.concat(annual, axis=1)
    hindcast.columns.names = ["version", "model"]
    return hindcast


def mean_levels(annual: pd.DataFrame) -> pd.DataFrame:
    """Collapse a hindcast frame to one period-mean level per model.

    Args:
        annual: Frame as returned by `hindcast_annual`.

    Returns:
        Model-indexed DataFrame with the three levels and the two deltas
        against the reference, rounded to 2 decimals.
    """
    # The SDK delivers float32; widen first so rounding gives clean decimals.
    period = annual.mean().astype(float)
    reference = period["reference"].iloc[0]
    levels = pd.DataFrame({"raw": period["raw"], "served": period["served"]})
    levels["reference"] = reference
    levels["raw − ref"] = levels["raw"] - reference
    levels["served − ref"] = levels["served"] - reference
    return levels.round(2)


def _rounded(values: pd.Series | pd.DataFrame, decimals: int) -> pd.Series | pd.DataFrame:
    """Round after widening to float64.

    The SDK delivers float32, and rounding float32 prints values like
    17.639999 instead of 17.64 — widen first so the rounding is clean.

    Args:
        values: Series or DataFrame to round.
        decimals: Number of decimal places to keep.

    Returns:
        Same shape as `values`, rounded.
    """
    return values.astype(float).round(decimals)


def nan_share(df: pd.DataFrame) -> pd.Series:
    """Share of missing values per column of one frame, in percent.

    Per column rather than per frame: in multi-model data each model is its
    own dataset, so a whole-frame share would hide a model that lacks a
    variable or a year behind the others' complete data.

    Args:
        df: Frame to check, flat or with (variable, model) MultiIndex
            columns.

    Returns:
        Column-indexed Series of missing shares, rounded to 1 decimal and
        named "% NaN".
    """
    return _rounded(df.isna().mean() * 100, 1).rename("% NaN")


def inter_model_spread(levels: pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Measure how far apart the models sit, before and after bias correction.

    Args:
        levels: Frame as returned by `mean_levels`, either for one site or for
            several stacked with `pd.concat({...}, names=["site"])`.

    Returns:
        Series with "raw" and "served" for a single site; one row per site,
        in the order given, for a stacked frame. Rounded to 2 decimals.
    """
    versions = levels[["raw", "served"]]
    if versions.index.nlevels == 1:
        return (versions.max() - versions.min()).round(2)

    by_site = versions.groupby(level=versions.index.names[0], sort=False)
    return (by_site.max() - by_site.min()).round(2)
