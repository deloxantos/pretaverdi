# Open-Meteo API Evaluation

Technical evaluation of Open-Meteo as a data source for agri-climate risk assessment.

## Overview

[Open-Meteo](https://open-meteo.com/) provides free access to weather and climate data through a RESTful API. No API key required for the free tier.

## Endpoints Used

### 1. Archive API (Historical Weather)
- **URL**: `https://archive-api.open-meteo.com/v1/archive`
- **Source**: ERA5 reanalysis (ECMWF)
- **Coverage**: 1940–present
- **Resolution**: ~9km (0.25°)
- **Latency**: Near real-time, with 5-7 day processing delay for latest data
- **Agri variables**: Temperature, precipitation, ET₀, soil moisture, radiation

### 2. Climate API (Projections)
- **URL**: `https://climate-api.open-meteo.com/v1/climate`
- **Source**: CMIP6 model ensemble
- **Coverage**: 1950–2050 (some models to 2100)
- **Resolution**: ~25km
- **Soil moisture models**: Only EC_Earth3P_HR and MRI_AGCM3_2_S
- **Agri variables**: Temperature, precipitation, soil moisture (limited models)

### 3. Forecast API
- **URL**: `https://api.open-meteo.com/v1/forecast`
- **Source**: Multiple NWP models (ICON, GFS, etc.)
- **Coverage**: Up to 16 days ahead
- **Resolution**: Varies by model (1-11km)
- **Agri variables**: Same as Archive API

## Rate Limits

| Tier | Calls/day | Notes |
|------|-----------|-------|
| Free | 10,000 | No API key, non-commercial use |
| Commercial | Unlimited | API key required, paid plans |

## SDK

Using `openmeteo-requests` Python SDK (v1.3+):
- Handles FlatBuffers response parsing
- Compatible with `requests-cache` for local SQLite caching
- Compatible with `retry-requests` for automatic retries

## Strengths for Agri-Climate Use
- Free, no registration required
- Comprehensive agri-climate variables (ET₀, soil moisture)
- Historical + projections + forecast in one platform
- Good Python SDK ecosystem

## Limitations for Agri-Climate Use
- Soil moisture is modeled (ERA5-Land), not measured
- CMIP6 soil moisture limited to 2 models
- No crop-specific data (growing degree days must be computed)
- No pest/disease risk indicators
- 9-25km resolution too coarse for field-level decisions

## Verdict

Excellent starting point for regional agri-climate analysis. The combination of historical, projection, and forecast data from a single API with a good SDK makes it ideal for Phase 1 exploration. For field-level precision, would need to supplement with higher-resolution or ground-truth data sources.
