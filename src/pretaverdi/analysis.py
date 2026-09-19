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


def hindcast_annual(
    location: dict,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    models: list[str] | None = None,
    reference: str = "era5_land",
) -> pd.DataFrame:
    """Fetch the annual temperature a hindcast compares: models vs reanalysis.

    Runs the same recent period three ways — the projections Open-Meteo serves
    (bias-corrected against ERA5-Land), the raw model output behind them, and
    the reanalysis both are judged against — so the served correction can be
    read as the gap it closes.

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
