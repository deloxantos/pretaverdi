"""Agri-climate variable constants and API endpoints for Open-Meteo."""

# Daily aggregations require the `_mean` suffix; the bare `soil_moisture_<band>`
# names are hourly-only and are rejected by the Archive API as `daily=` params.
AGRI_DAILY_DEFAULTS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "soil_moisture_0_to_7cm_mean",
    "soil_moisture_7_to_28cm_mean",
    "shortwave_radiation_sum",
]

# No soil moisture here: the Climate API's daily band is `soil_moisture_0_to_10cm_mean`,
# but EC_Earth3P_HR returns all-null series for it, so it is not a usable default.
CLIMATE_DEFAULTS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
]

SOIL_MOISTURE_MODELS = ["EC_Earth3P_HR", "MRI_AGCM3_2_S"]

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
CLIMATE_API_URL = "https://climate-api.open-meteo.com/v1/climate"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# Reference locations for agri-climate analysis
LOCATIONS = {
    "pampa_ar": {"lat": -34.6, "lon": -58.4, "name": "Pampa, Argentina"},
    "midwest_us": {"lat": 41.9, "lon": -89.1, "name": "Midwest, USA"},
    "punjab_in": {"lat": 30.9, "lon": 75.9, "name": "Punjab, India"},
    "kenya_ea": {"lat": -0.5, "lon": 37.3, "name": "Central Kenya"},
}
