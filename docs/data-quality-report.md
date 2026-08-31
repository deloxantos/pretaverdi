# Data Quality Report

> This document is built incrementally as we explore Open-Meteo data. Each section documents findings from notebook exploration.

## Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| Completeness | Complete | 730/730 daily rows × 7/7 variables for both locations — no gaps |
| Temporal coverage | As expected | 2022-01-01 → 2023-12-31, 730 rows per location (two full non-leap years) |
| Missing values | None | 0 NaN in every variable at both locations |
| Value ranges | Plausible | All variables inside expected physical bounds (see Findings) |
| Resolution | ~9km | ERA5 grid — does not capture micro-climate variation |

_Observed on 2026-07-28 UTC by executing `notebooks/01-open-meteo-exploration.ipynb` against the live Archive API for Pampa, AR (-34.6, -58.4) and Midwest, US (41.9, -89.1)._

## Archive API (ERA5 Reanalysis)

### Known Limitations
- Recent data (last 5-7 days) may have gaps until ERA5 processing catches up
- Spatial resolution ~9km — not suitable for field-level analysis
- Soil moisture is modeled, not measured — ground-truth validation needed

### Findings

- **No gaps at all.** Both locations returned exactly `(730, 7)` and `isnull().sum()` is 0 for all
  seven variables. The documented "recent data may be missing" caveat did not bite: the window ends
  2023-12-31, far outside the ERA5 processing lag. A window ending near today should be re-checked
  before trusting this result for live use.
- **Temperature ranges are physically sound and regionally distinct.** Pampa spans 9.20 → 38.90 °C
  (max) and -0.25 → 29.00 °C (min); Midwest spans -19.35 → 36.55 °C (max) and -26.65 → 26.10 °C
  (min). Both sit well inside the -40..50 °C plausibility band, and the Midwest's far wider spread
  (std 11.58 vs 6.17 °C on daily max) matches a continental vs. humid-subtropical climate.
- **Seasonality is present and correctly phased for opposite hemispheres.** The daily temperature
  chart shows Pampa peaking in Dec-Feb and troughing in Jun-Aug, with the Midwest exactly
  anti-phased. This is a useful sanity check that latitude/longitude are not being swapped or
  mis-signed anywhere in the client.
- **Soil moisture is in range but behaves very differently by depth and region.** Values stay within
  0.14-0.50 m³/m³ everywhere (physical band 0..1). At Pampa the 0-7cm layer is far spikier than the
  7-28cm layer and repeatedly flattens at its 0.15 m³/m³ minimum for days at a time — consistent
  with a dry-limit floor in the model rather than measured variation. At the Midwest the two depths
  track each other closely.
- **Precipitation is the weakest-correlated variable in the matrix.** Daily precipitation shows only
  a pale, near-zero correlation with every other variable, including same-day soil moisture. The
  strong structure is elsewhere: temperature, ET₀ and shortwave radiation correlate strongly and
  positively with each other, all three correlate strongly and *negatively* with both soil-moisture
  layers, and the two soil layers correlate strongly with each other. Practical consequence:
  same-day rainfall is a poor proxy for soil water — lagged/accumulated precipitation will be needed
  for any drought or water-balance indicator.
- **Data-contract note.** Daily soil moisture must be requested as `soil_moisture_<band>_mean`; the
  bare `soil_moisture_<band>` names are hourly-only and the Archive API rejects them outright
  (`Cannot initialize ForecastVariableDaily from invalid String value ...`). Requested column names
  become DataFrame column names, so this propagates to downstream code.

## Climate API (CMIP6 Projections)

### Known Limitations
- Soil moisture is not usable across the default CMIP6 models:
  `soil_moisture_0_to_10cm_mean` returns an all-null series for `EC_Earth3P_HR`
  and `FGOALS_f3_H`; only `MRI_AGCM3_2_S` returns data (live probes, 2026-07-28
  and 2026-08-31 UTC). The API returns the all-null series without any error.
  This is why soil moisture is excluded from `CLIMATE_DEFAULTS` in
  `src/pretaverdi/variables.py`.
- Resolution ~25km — coarser than ERA5
- Projections carry inherent uncertainty — always report model ranges (the
  client's default is now three models for exactly this reason)

### Findings

_Observed on 2026-08-31 UTC by probing the live Climate API for Pampa, AR
(-34.6, -58.4)._

- **Multi-model responses arrive as one message per model.** A request for N
  models returns N FlatBuffers messages, in requested order, each carrying the
  requested variables in requested order (verified via the SDK's
  `Variable()`/`Aggregation()` codes) and identified by `response.Model()`. The
  earlier reading of the response shape — "models × variables series in a
  single response" (recorded here on 2026-07-28) — was incorrect: the old
  variable-count guard never fired on multi-model requests, and the client
  silently returned only the first model's data. `get_climate_projections()`
  now parses all messages into `(variable, model)` columns and verifies the
  returned model set against the request.
- **`timezone=auto` is accepted** and shifts the daily index to local midnight,
  matching the Archive and Forecast endpoints. Without it, climate frames sat
  at 00:00 UTC while archive frames sat at local midnight — a raw timestamp
  join between baseline and projections would have silently misaligned by 3-5
  hours.
- **`FGOALS_f3_H` returns complete data** (0% null) for the three
  `CLIMATE_DEFAULTS` variables, so it joined the default model list —
  three models make the default a range, not a pair.
- **Soil moisture availability by model** (`soil_moisture_0_to_10cm_mean`,
  Jan 2030): `EC_Earth3P_HR` 100% null, `FGOALS_f3_H` 100% null,
  `MRI_AGCM3_2_S` full data. See Known Limitations above.

## Forecast API

### Known Limitations
- Forecast skill degrades significantly beyond 7 days
- Available up to 16 days ahead

### Findings
_To be filled in future exploration._
