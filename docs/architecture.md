# Architecture Decision Records

## ADR-001: Data-first Phase 1 with direct SDK instead of AgentCore Gateway

**Status:** Accepted (2026-07-27, retroactive — documents a pivot made during Phase 1)

**Context:** The PRD (`docs/prd/phase1-foundation.md` §1.2, §4) defines the core
pattern as OpenAPI specs exposed as MCP tools through AWS AgentCore Gateway,
provisioned with Terraform. Building that first would have meant deploying
infrastructure before understanding the data it serves.

**Decision:** Phase 1 explores the data directly through the `openmeteo-requests`
SDK behind a thin client (`src/pretaverdi/client.py`). Gateway, MCP tools and
Terraform move to the next phase, where the OpenAPI specs can be written from
validated knowledge of the endpoints (`variables.py` already enumerates the
exact parameters each spec needs).

**Consequences:** The MCP/Gateway pattern is deferred, not dropped. PRD Weeks 2 and 4 (Gateway, CloudWatch, Terraform) are re-scoped to
the next phase. Geographic scope also widened from the PRD's southern Brazil focus
to four reference regions (Pampa, Midwest, Punjab, Central Kenya); only the two
western-hemisphere ones are explored so far. The Climate API integration also
remained partial at the time: multi-model response parsing was deferred.
_Update 2026-08-31: multi-model parsing landed; the Climate API integration is
no longer partial (see `docs/data-quality-report.md`, Climate API "Findings")._

## ADR-002: NASA POWER deferred to the next phase

**Status:** Accepted (2026-07-27)

**Context:** The PRD (§3.3, Week 2-3) includes NASA POWER as the secondary API,
required for cross-API comparisons and for parameters Open-Meteo lacks
(GWETROOT, FROST_DAYS, solar radiation for crop models).

**Decision:** Phase 1 ships with Open-Meteo only. NASA POWER — and with it the
cross-API data-quality comparison — moves to the next phase.

**Consequences:** `docs/data-quality-report.md` covers a single provider; the
PRD success criterion "data quality with cross-comparisons" is partially met and
carries over.

## ADR-003: Local SQLite cache + JSONL query log instead of PRD §6.4 (no cache, S3 log)

**Status:** Accepted (2026-07-27)

**Context:** PRD §6.4 recommends deferring caching and logging request+response
to S3 for reproducibility.

**Decision:** For local-only exploration, requests-cache (SQLite, 1h TTL) plus a
JSONL metadata log in `.cache/` gives the same reproducibility benefits with zero
infrastructure. S3 logging becomes relevant when AWS infrastructure exists (next
phase). Tests are isolated from the real log via `tests/conftest.py`.

**Consequences:** Reproducibility artifacts are machine-local: the SQLite cache
and JSONL log are gitignored and not shared. Only request params and response
shape are persisted (not full payloads), so S3-grade audit logging remains a
next-phase item. The 1h TTL means notebook re-runs within an hour replay cached
responses instead of hitting the live API.
