# PRD: Climate Preparedness Agent — Phase 1 (Foundation)

> **Purpose**: This document captures validated technical decisions, open questions, and scope boundaries for Phase 1 of the Climate Preparedness Agent project.

---

## 1. Vision & context

### 1.1 What are we building?

An AI agent that evaluates **agri-climate risk for food security preparedness** by
autonomously querying multiple heterogeneous climate data APIs through a unified
MCP (Model Context Protocol) gateway.

The agent answers questions like:

- "What is the drought risk for maize production in southern Brazil this season?"
- "How have temperature extremes changed over the last 20 years in the Pampas region?"
- "Which regions in South America show the highest climate vulnerability for soybean yields?"



### 1.2 Why this matters

Food security under climate change is one of the most impactful areas in climate tech.  
This project demonstrates:

1. **A novel architectural pattern**: Using MCP as an abstraction layer for heterogeneous
  climate data sources, with AgentCore Gateway auto-generating tools from OpenAPI specs.
2. **AI for Good principles applied in practice**: Human-in-the-loop evaluation,
  uncertainty quantification, and the Disaster Management "Preparedness" phase framework.
3. **Production-grade cloud infrastructure for climate science**: Reproducible IaC,
  observability, and enterprise-ready security patterns on AWS.



### 1.3 Disaster management framework alignment

This project focuses on the **Preparedness** phase of the 4-phase disaster management
cycle (Mitigation → Preparedness → Response → Recovery). Preparedness was chosen because:

- It is fundamentally a **data integration and risk assessment** problem
- It does not require real-time systems (unlike Response)
- It does not require post-event data (unlike Recovery)
- It does not require continuous monitoring infrastructure (unlike Mitigation)
- The output (risk assessments, vulnerability maps) is tangible and demonstrable



### 1.4 AI for Good principles (cross-cutting)

These principles apply across ALL phases of the project:

- **Human-in-the-loop (HITL)**: No automated climate conclusion without human review
- **Uncertainty quantification**: Every agent output must express confidence and data gaps
- **Transparency**: Full traceability of which APIs were queried, what data was used
- **Correlation ≠ causation**: Agent prompts must enforce epistemic rigor
- **Stochasticity awareness**: LLMs sample from probability distributions; outputs
may vary across runs. Evaluation must account for this non-determinism
- **Reproducibility**: Logged API calls, versioned prompts, deterministic infrastructure

---



## 2. Phase 1 scope: Foundation (weeks 1-4)



### 2.1 Goal

Get climate data flowing through AgentCore Gateway as MCP tools. Validate data
quality manually before connecting any Foundation Model.

### 2.2 What Phase 1 IS

- OpenAPI specifications for 2-3 climate data APIs
- An AgentCore Gateway endpoint exposing those APIs as MCP tools
- Manual exploration and documentation of data quality, gaps, and characteristics
- Infrastructure as Code (Terraform or CDK) for reproducibility
- A working MCP client that can invoke the tools



### 2.3 What Phase 1 is NOT

- No Foundation Model integration (that's Phase 2)
- No UI or frontend
- No multi-region or disaster recovery (that's long-term vision)
- No custom ML models or fine-tuning

---



## 3. Validated API selections



### 3.1 Selection criteria

For Phase 1 MVP, APIs were evaluated on:


| Criterion                                | Weight   | Rationale                              |
| ---------------------------------------- | -------- | -------------------------------------- |
| REST JSON API available                  | Critical | Required for OpenAPI spec creation     |
| No auth or simple auth                   | High     | Reduces Phase 1 complexity             |
| Free tier sufficient                     | High     | No budget for data in MVP              |
| Agri-climate relevance                   | High     | Must serve the preparedness use case   |
| Existing OpenAPI spec or easily writable | High     | Core of the AgentCore Gateway approach |
| Historical + projection data             | Medium   | Enables both analysis and forecasting  |
| Good documentation                       | Medium   | Speeds up spec writing                 |




### 3.2 Selected: Open-Meteo (PRIMARY)

**Role in the project**: Historical weather data + climate change projections.

**Why chosen**:

- Free, no API key required, no rate limit for non-commercial use
- Clean REST JSON API with simple query parameters
- 80+ years of hourly weather data at 10km resolution (ERA5 reanalysis from 1940)
- Climate Change API with CMIP6 projections downscaled to 10km (1950-2050)
- Directly relevant variables: temperature, precipitation, soil moisture, soil temperature
- Open source (GitHub: open-meteo/open-meteo), data hosted on AWS Open Data

**Endpoints to expose as MCP tools**:


| Endpoint       | MCP Tool Name             | Purpose                             |
| -------------- | ------------------------- | ----------------------------------- |
| `/v1/archive`  | `get_historical_weather`  | ERA5 reanalysis data (1940-present) |
| `/v1/climate`  | `get_climate_projections` | CMIP6 daily projections (1950-2050) |
| `/v1/forecast` | `get_weather_forecast`    | Current forecast (14 days)          |


**Key parameters for agri-climate risk**:

- `temperature_2m_max`, `temperature_2m_min` (heat stress, frost risk)
- `precipitation_sum` (drought, flooding)
- `soil_moisture_0_to_7cm`, `soil_moisture_7_to_28cm` (crop water availability)
- `et0_fao_evapotranspiration` (water balance)
- `shortwave_radiation_sum` (solar energy for photosynthesis)

**OpenAPI spec status**: Does NOT have an existing OpenAPI spec. Must be written
from documentation. The API is well-documented with clear parameter lists, so this
is straightforward but manual work.

**Data quality notes**:

- ERA5 reanalysis: scientifically validated, consistent time series, but 9-25km resolution
means local microclimate effects are smoothed out
- CMIP6 projections: statistically downscaled, useful for trends but NOT for
precise point predictions. Multiple models available; recommend running with
several and comparing (EC_Earth3P_HR, MRI_AGCM3_2_S, FGOALS_f3_H, etc.)
- Important: climate projections should NOT be confused with weather forecasts



### 3.3 Selected: NASA POWER (SECONDARY)

**Role in the project**: Agro-meteorological data complementing Open-Meteo, with
parameters specifically designed for agricultural and energy applications.

**Why chosen**:

- Free, requires only a user identifier (not a traditional API key)
- REST JSON API, well-documented
- Has an existing openapi.json spec (for the Indicators endpoint) that has been
successfully used in similar projects (Climate GPT on OpenAI)
- Unique agri-climate parameters not available in Open-Meteo: growing degree days,
frost days, dew/frost point temperature, wind profile coefficients
- "ag" (agroclimatology) community parameter set designed specifically for agriculture

**Endpoints to expose as MCP tools**:


| Endpoint                          | MCP Tool Name           | Purpose                         |
| --------------------------------- | ----------------------- | ------------------------------- |
| `/api/temporal/daily/point`       | `get_power_daily`       | Daily agro-met data for a point |
| `/api/temporal/monthly/point`     | `get_power_monthly`     | Monthly aggregations            |
| `/api/temporal/climatology/point` | `get_power_climatology` | Long-term averages              |


**Key parameters for agri-climate risk**:

- `T2M`, `T2M_MAX`, `T2M_MIN` (temperature at 2 meters)
- `PRECTOTCORR` (precipitation corrected)
- `ALLSKY_SFC_SW_DWN` (solar radiation — critical for crop models)
- `RH2M` (relative humidity — disease pressure indicator)
- `GWETROOT` (root zone soil wetness — unique to POWER)
- `FROST_DAYS` (frost frequency — critical for crop planning)

**OpenAPI spec status**: The Indicators API has an openapi.json available. The
temporal endpoints (daily, monthly, climatology) need specs written but follow a
consistent pattern. Previous projects (Towards Data Science "Climate GPT") documented
the adjustments needed: parameter descriptions must be under 300 characters, and a
`servers` section needs to be added.

**Data quality notes**:

- Based on NASA's MERRA-2 assimilation model (meteorological) and CERES/SRB (solar)
- Solar radiation data is a significant differentiator vs Open-Meteo for crop modeling
- Maximum 20 parameters per single-point request (API limit)
- Regional requests limited to 1 parameter at a time
- Response times vary; hourly data requests can take up to a minute



### 3.4 Considered but deferred: FAOSTAT

**Why considered**: FAOSTAT provides agricultural production statistics (crop yields,
area harvested, production quantities) for 245+ countries from 1961 to present.
This is the "ground truth" for validating whether climate conditions actually
affected crop production.

**Why deferred to Phase 2**:

- No formal REST API with OpenAPI spec; data access is through a custom API
with non-standard parameter patterns (dataset codes, dimension codes)
- A Python library exists (`faostat` on PyPI) but it's designed for bulk
downloads, not real-time queries
- The data is updated annually, not in real-time, so it's more useful for
validation than for risk assessment
- Adding it in Phase 1 would increase complexity without improving the
core demo of the MCP + Gateway pattern

**Phase 2 plan**: Wrap FAOSTAT data access in an AWS Lambda function, expose
it through AgentCore Gateway as a Lambda target (not OpenAPI). This lets the
agent correlate climate conditions with actual historical crop yields.

### 3.5 Long-term API roadmap (beyond Phase 1)


| API                          | Role                                | Priority |
| ---------------------------- | ----------------------------------- | -------- |
| FAOSTAT (via Lambda)         | Historical crop yield ground truth  | Phase 2  |
| Copernicus CDS (ERA5 direct) | Higher-resolution reanalysis        | Phase 3  |
| NOAA NCEI                    | Station-level observations          | Phase 3  |
| Soil Grids API               | Soil type and properties            | Phase 3  |
| USDA FAS (crop reports)      | Near-real-time production estimates | Phase 3  |


---



## 4. Technical architecture



### 4.1 Core components

```
┌─────────────────────────────────────────────────────────┐
│                  AgentCore Gateway                       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Open-Meteo   │  │  NASA POWER   │  │  (Future:    │  │
│  │  OpenAPI      │  │  OpenAPI      │  │   Lambda     │  │
│  │  Target       │  │  Target       │  │   Targets)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │
│         │                  │                             │
│         └────────┬─────────┘                            │
│                  │                                       │
│         Unified MCP Endpoint                            │
│         (Streamable HTTP)                               │
│                  │                                       │
│         Semantic Tool Selection                         │
│         (x_amz_bedrock_agentcore_search)               │
└────────────┬────────────────────────────────────────────┘
             │
             │  MCP Protocol
             │
     ┌───────┴────────┐
     │   MCP Client   │
     │  (Phase 1:     │
     │   manual CLI)  │
     │  (Phase 2:     │
     │   Bedrock FM)  │
     └────────────────┘
```



### 4.2 AgentCore Gateway configuration

**Gateway type**: OpenAPI targets (Phase 1), Lambda targets (Phase 2+)

**Key capabilities used**:

- **Zero-code MCP tool creation**: Gateway parses OpenAPI specs and auto-generates
MCP-compatible tools without custom code
- **Semantic tool selection**: Built-in `x_amz_bedrock_agentcore_search` allows
discovering relevant tools via natural language queries. Critical when the tool
catalog grows beyond 3-5 APIs
- **Inbound auth**: OAuth-based (Cognito) for securing the MCP endpoint
- **Outbound auth**: IAM-based for Lambda targets; API key injection for external APIs
- **Observability**: CloudWatch integration for monitoring tool calls and latency

**Phase 2 server-side execution**: As of February 2026, Bedrock Responses API
supports specifying an AgentCore Gateway ARN as a tool connector. Bedrock
automatically discovers tools, presents them to the model during inference,
and executes tool calls server-side — eliminating client-side orchestration.

### 4.3 Infrastructure as Code

**Tool**: Terraform (preferred over CDK for broader community reach and
reproducibility outside AWS-centric teams)

**Resources to provision**:

- AgentCore Gateway endpoint
- Gateway targets (OpenAPI specs)
- IAM roles and policies
- Cognito user pool (for inbound auth)
- CloudWatch log groups and dashboards
- S3 bucket for OpenAPI spec storage and versioning



### 4.4 Repository structure (proposed)

```
climate-preparedness-agent/
├── README.md
├── LICENSE                          # MIT or Apache 2.0
├── docs/
│   ├── architecture.md              # Architecture decisions and diagrams
│   ├── data-quality.md              # Data quality findings from manual exploration
│   ├── api-evaluation.md            # Why these APIs were chosen
│   └── ai-for-good-principles.md   # Framework alignment documentation
├── specs/
│   ├── open-meteo-historical.yaml   # OpenAPI spec for Open-Meteo Archive API
│   ├── open-meteo-climate.yaml      # OpenAPI spec for Open-Meteo Climate API
│   ├── nasa-power-daily.yaml        # OpenAPI spec for NASA POWER Daily API
│   └── nasa-power-monthly.yaml      # OpenAPI spec for NASA POWER Monthly API
├── infra/
│   ├── main.tf                      # Terraform root module
│   ├── gateway.tf                   # AgentCore Gateway resources
│   ├── auth.tf                      # Cognito + IAM
│   ├── observability.tf             # CloudWatch dashboards
│   └── variables.tf
├── scripts/
│   ├── validate-specs.sh            # Validate OpenAPI specs before deploy
│   ├── test-tools.py                # Manual MCP tool invocation tests
│   └── data-quality-checks.py       # Data quality validation scripts
├── notebooks/                       # (Phase 2) Jupyter notebooks for exploration
└── .github/
    └── workflows/
        └── validate.yml             # CI: lint specs, validate terraform
```

---



## 5. Phase 1 detailed task breakdown



### Week 1: OpenAPI specs + local validation

**Goal**: Have working OpenAPI specs that accurately describe the climate APIs.

Tasks:

- [ ] Set up repo structure and README
- [ ] Write OpenAPI 3.0 spec for Open-Meteo Historical Weather API (`/v1/archive`)
  - Focus on agri-climate parameters only (not all 50+ variables)
  - Include parameter descriptions optimized for LLM tool selection (<300 chars)
  - Add response schema with example payloads
- [ ] Write OpenAPI 3.0 spec for Open-Meteo Climate API (`/v1/climate`)
  - Include model selection parameter (multiple CMIP6 models)
  - Document which variables are available in which models
- [ ] Validate specs: test against live APIs using curl/httpie
- [ ] Document any API quirks or limitations discovered

**Deliverable**: 2 validated OpenAPI specs in `specs/` directory.

### Week 2: NASA POWER specs + Gateway setup

**Goal**: Complete the API spec set and deploy AgentCore Gateway.

Tasks:

- [ ] Write/adapt OpenAPI spec for NASA POWER Daily API
  - Start from existing openapi.json for Indicators endpoint
  - Extend to temporal/daily endpoint pattern
  - Ensure parameter descriptions <300 chars (known issue from prior art)
  - Add `servers` section pointing to `https://power.larc.nasa.gov`
- [ ] Write OpenAPI spec for NASA POWER Monthly API
- [ ] Write Terraform for AgentCore Gateway
  - Gateway endpoint creation
  - OpenAPI targets for each spec
  - Inbound auth (Cognito, can be simplified for MVP)
  - IAM roles
- [ ] Deploy Gateway and verify tool synchronization
- [ ] Test MCP tool discovery via the gateway endpoint

**Deliverable**: Gateway deployed, 4 MCP tools discoverable.

### Week 3: Manual data exploration

**Goal**: Understand the data before any automation touches it.

Tasks:

- [ ] Write a Python script to invoke each MCP tool with representative queries:
  - Historical temperature and precipitation for southern Brazil (last 20 years)
  - Climate projections for the same region (multiple CMIP6 models)
  - NASA POWER solar radiation and soil wetness data for the same location
- [ ] Compare overlapping parameters between Open-Meteo and NASA POWER:
  - Temperature (T2M vs temperature_2m): do they agree?
  - Precipitation: same time period, same location — how much do they diverge?
  - Document any systematic biases or offsets
- [ ] Identify data gaps:
  - What's the latest available date for each API?
  - Are there temporal gaps or missing values?
  - What happens at the edges of spatial coverage?
- [ ] Test edge cases:
  - What happens with invalid coordinates?
  - What's the API behavior for dates outside the available range?
  - How do rate limits manifest?
- [ ] Document findings in `docs/data-quality.md`

**Deliverable**: Data quality report documenting characteristics, gaps, and
cross-API comparisons. This document is critical for Phase 2 prompt engineering.

### Week 4: Observability + hardening + documentation

**Goal**: Make the infrastructure production-ready and well-documented.

Tasks:

- [ ] Add CloudWatch dashboards for Gateway:
  - Tool invocation count by tool name
  - Latency percentiles (p50, p95, p99)
  - Error rates by target API
  - Cold start monitoring
- [ ] Add Gateway observability Terraform module
- [ ] Write comprehensive README:
  - Project vision
  - Architecture diagram
  - Quick start guide (deploy in <10 minutes)
  - API selection rationale
  - AI for Good framework alignment
- [ ] Write `docs/architecture.md` with:
  - ADRs (Architecture Decision Records) for key choices
  - Why AgentCore Gateway over custom MCP server
  - Why these specific APIs
  - Why Terraform over CDK
  - Data flow diagrams
- [ ] Create GitHub Actions workflow for CI:
  - OpenAPI spec linting (spectral or similar)
  - Terraform validate + plan
  - Basic integration test (invoke one tool, verify response shape)
- [ ] Tag v0.1.0 release

**Deliverable**: Production-ready Phase 1 repo with documentation, observability,
and CI pipeline. Ready for Phase 2 Foundation Model integration.

---



## 6. Key technical decisions to validate during implementation

These are the open questions that need hands-on exploration:

### 6.1 OpenAPI spec authoring

- **Question**: What's the optimal granularity for MCP tools? One tool per API endpoint,
or one tool per "climate question" pattern?
- **Trade-off**: Fine-grained tools (one per endpoint) give the FM more flexibility but
require more orchestration. Coarse-grained tools (e.g., `assess_drought_risk` that
internally calls multiple endpoints) are easier for the FM but less flexible.
- **Recommendation**: Start fine-grained (one per endpoint) in Phase 1. In Phase 2,
evaluate whether the FM struggles with multi-tool orchestration and add composite
tools if needed.



### 6.2 Parameter description optimization

- **Question**: How should tool/parameter descriptions be written to maximize the FM's
ability to select the right tool and construct correct queries?
- **Context**: AgentCore Gateway's semantic tool selection
(`x_amz_bedrock_agentcore_search`) uses these descriptions for tool discovery.
The FM also reads them when deciding which tool to call and what parameters to pass.
- **Recommendation**: Write descriptions from the perspective of what the data *means*
for climate risk, not just what the API parameter is. Example:
  - Bad: `"temperature_2m_max: Maximum air temperature at 2 meters (°C)"`
  - Good: `"temperature_2m_max: Maximum daily air temperature at 2 meters above ground in °C. Critical indicator for heat stress assessment in crops — values above 35°C during flowering can severely reduce yields for maize and soybeans."`



### 6.3 Gateway authentication model

- **Question**: What's the simplest auth setup for Phase 1 that's still secure?
- **Trade-off**: Full Cognito + OAuth is production-grade but complex to set up.
IAM-only auth is simpler but limits who can invoke the tools.
- **Recommendation**: For Phase 1 MVP, use IAM-based inbound auth (the caller
authenticates with AWS credentials). Add Cognito in Phase 2 when external
access is needed.



### 6.4 Data caching strategy

- **Question**: Should we cache API responses? Climate data for past dates doesn't change.
- **Trade-off**: Caching reduces API load and latency but adds infrastructure complexity.
Climate APIs are generally not rate-limited aggressively.
- **Recommendation**: Defer caching to Phase 2. In Phase 1, log all API calls
(request + response) to S3 for reproducibility. This log doubles as a cache
for known queries without adding caching infrastructure.

---



## 7. Success criteria for Phase 1


| Criterion                   | Measurement                                              |
| --------------------------- | -------------------------------------------------------- |
| Gateway operational         | All 4 MCP tools discoverable and invocable               |
| Data quality documented     | `data-quality.md` covers all APIs with cross-comparisons |
| Infrastructure reproducible | `terraform apply` from clean state succeeds in <10 min   |
| Observability working       | CloudWatch dashboard shows tool call metrics             |
| CI passing                  | GitHub Actions validates specs + infra on every push     |
| Documentation complete      | README enables a new developer to deploy in <15 min      |


---



## 8. Long-term vision (for context, not Phase 1 scope)



### Phase 2 (weeks 5-10): Agent + preparedness

- Connect Bedrock FM via Responses API with Gateway ARN as tool connector
- Implement agri-climate risk assessment prompts with:
  - Multi-variable queries ("drought risk for maize in Mato Grosso")
  - Uncertainty quantification in every response
  - Explicit correlation vs causation guardrails
- Add FAOSTAT via Lambda target for historical yield validation
- Human-in-the-loop evaluation framework



### Phase 3 (weeks 11-16): Demo

- Polished open source demo with interactive notebook



### Long-term architecture vision

- **Edge inference**: Compressed models for offline operation in disaster scenarios
- **Multi-region resilience**: Disaster recovery with cross-region failover
- **Satellite connectivity**: Starlink-based data sync for remote monitoring stations
- **Broader Disaster Management coverage**: Expand from Preparedness to Mitigation
(continuous monitoring) once the data pipeline is battle-tested

---



## 9. References & prior art

- [Towards Data Science: Developing a Climate GPT Using NASA's Power API](https://towardsdatascience.com/developing-a-climate-gpt-using-nasas-power-api-37b3d9e2a664/) — Demonstrates NASA POWER openapi.json integration with AI agents. Validated the approach but used OpenAI GPTs, not MCP/AgentCore.
- [AWS Blog: Introducing AgentCore Gateway](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-gateway-transforming-enterprise-ai-agent-tool-development/) — Official deep dive on Gateway architecture and capabilities.
- [MCPfying Tools at Scale with AgentCore Gateway](https://dev.to/aws-builders/mcpfying-tools-securely-at-scale-with-bedrock-agentcore-gateway-e3d) — Practical walkthrough of Gateway + Strands agent integration.
- [Open-Meteo Climate API documentation](https://open-meteo.com/en/docs/climate-api) — CMIP6 projections at 10km resolution.
- [NASA POWER API documentation](https://power.larc.nasa.gov/docs/services/api/) — Agro-meteorological data services.
- [CCAI x Environmental Data Science special collection](https://www.cambridge.org/core/journals/environmental-data-science/announcements/call-for-papers/call-for-papers-tackling-climate-change-with-machine-learning) — Research collection on machine learning applied to climate change.

---



## 10. Glossary


| Term                  | Definition                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------- |
| **MCP**               | Model Context Protocol — standardized protocol for AI agents to discover and invoke tools         |
| **AgentCore Gateway** | AWS managed service that converts APIs into MCP-compatible tools                                  |
| **OpenAPI spec**      | Machine-readable API description format (formerly Swagger)                                        |
| **ERA5**              | ECMWF Reanalysis v5 — gold standard reanalysis dataset from 1940                                  |
| **CMIP6**             | Coupled Model Intercomparison Project Phase 6 — IPCC climate projections                          |
| **Crop yield**        | Production per unit area (e.g., tonnes of maize per hectare)                                      |
| **HITL**              | Human-in-the-loop — requiring human validation of AI outputs                                      |
| **Preparedness**      | Disaster management phase focused on risk assessment and planning before events occur             |
| **MERRA-2**           | NASA's Modern-Era Retrospective analysis for Research and Applications, version 2                 |
| **Reanalysis**        | Technique that combines historical observations with models to create consistent climate datasets |


