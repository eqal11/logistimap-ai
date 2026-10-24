# Phase 7 — Engineering review

24 Oktober 2026. **Development complete for bounded local review. Visual browser acceptance pending.**
Phase 5 and Phase 6 browser checks remain pending; Phase 8 not started.

## Architecture and source changes

The existing React/FastAPI/PostGIS application is extended in place. No separate app,
new system installation, Docker, paid API activation or public deployment was used.

Backend `app/geoai/schemas.py` defines strict request/tool/output boundaries.
`tools.py` exposes 23 approved adapters to existing Phase1–6 services; all args validate
before any batch execution. `planner.py` is an explicitly limited bilingual command
grammar, not a full LLM. `provider.py` optionally plans validated function calls using
one configured HTTPS compatible endpoint. It discards model prose, never runs SQL/code,
and constrains proposed references to explicit question/context identifiers/places.
`service.py` executes dependent tools, stops on failure, reports partial completion and
builds numeric explanations exclusively from actual outputs. `state.py` bounds sessions,
turns, result history and rate/concurrency. `repository.py` requires explicit confirmation
for immutable snapshots; confirmation audits contain digests/status, not unrestricted reasoning.

Frontend `features/GeoAICopilot.tsx`, `services/geoai.ts` and `styles/geoai.css` supply
chat, tool forms, explicit context, results, charts, source metadata, visibility and export.
Existing `MapWorkspace` renders actual point/line/polygon/analysis layers with independent
GeoAI top/selection highlights and original feature geometry. Display IDs are namespaced;
export IDs/geometries remain original. Show-only context hides previous visible layers.
Progress polling is ignored after effect cleanup so late polls cannot overwrite final results.
The Vite GeoAI proxy timeout now matches bounded long-running confirmed operations.

Existing feature query service gains an optional server-validated reference feature UUID.
Ordinary Phase1–6 query behavior is unchanged; selected-feature proximity uses actual
PostGIS geography footprint separation instead of silently treating a park anchor as its boundary.
Saved scenario/solution/MCDA operations reuse production service layers and don't overwrite old data.

## Tool registry

- search_industrial_features, search_warehouses, search_logistics_hubs
- get_feature_details, create_buffer, intersect_features, nearest_facility
- analyze_industrial_clusters, compare_industrial_density
- calculate_network_accessibility, rank_warehouse_accessibility, calculate_road_route
- get_saved_routes, get_saved_analyses, get_logistics_scenarios
- optimize_vehicle_routes (preview/confirm), compare_optimization_scenarios (read-only)
- get_warehouse_candidates, evaluate_mcda_scenario, explain_mcda_ranking,
  run_mcda_sensitivity_analysis, filter_results, export_results

Tools/catalog and exact Pydantic schemas are available at GET /api/geoai/tools.
API routes/body limits/configuration/contracts are documented in docs/API.md and OpenAPI.

## Verification evidence

- Final full suite: **288 backend passed**, 0 failures/errors/skips; **17 live DB tests**.
- **89 frontend passed**, 18 files; 0 failed/pending. Typecheck/build/pip check passed.
- Tests cover bilingual intent, complete category extraction, ambiguity, invalid parameters,
  entire-batch validation, provider timeout/structured output (mocked external LLM), context
  references, injection/sensitive-text rejection, one-shot/cross-session/expired confirmations,
  changed scenario digest rejection, cancellation checkpoints, pagination, original geometry,
  CSV injection mitigation, MapLibre style validation, context clearing, show-only map state
  and persistence with transaction rollback.
- Fresh HTTP real-data scenarios: search, actual geodesic nearest/proximity, DBSCAN, OSRM
  route/matrix, confirmed OR-Tools solve/fleet comparison, MCDA/explanation/sensitivity,
  multi-turn filtering/exports and confirmed save/reload all passed.
- L/M/N are expected clarification/unavailable/safety outcomes; never successful spatial/LLM claims.
- Core API/proxy smoke returns HTTP200; latest dist served on4173; not browser/GPU evidence.
- Exports executed through actual frontend functions in Node:3 exact original geometries,
  CSV3 rows, one visible result layer after filtering. Shapely/metadata validation passed.
- Browser tool returns Local browser use is disabled in Work settings. No browser pass or
  screenshot is fabricated/reused; manual G01–G19 checklist remains unexecuted.

## Bugs found and fixed during development

- Current MCDA weights question originally entered the weight-edit clarification branch;
  explicit ranking intent now has correct precedence and regression coverage.
- Generic explanation wording originally parsed “candidate ranks” as an exact candidate ID;
  filler words are excluded; missing IDs use explicitly displayed top two saved candidates.
- Early assertions expected GeoAI to remain a future unavailable module; updated to verify
  implemented navigation while preserving forbidden SQL/code endpoint checks.
- TypeScript optional navigation phase/unknown result field errors fixed before final build.
- Whole candidate pages, actual source geometry and pagination metadata are retained;
  second-page/incomplete warehouse ranking is rejected instead of using a partial set.
- Show-only result context now changes visible map layers, not just the returned table.
- Pending confirmation is invalidated by a new question; explicit null clears context;
  confirmation rechecks the immutable scenario digest and cannot replay or cross sessions.
- Progress-poll cleanup and Vite proxy limits were corrected to support long bounded operations.

## Database and security findings

Migration0004_geoai adds geoai_sessions and geoai_confirmations only, with RLS and revokePUBLIC.
Offline SQL review found two CREATE TABLE and no destructive statements; guarded transaction
committed and verified. Database now26 tables/RLS,8 spatial geometry/GiST columns, SSL/PostGIS3.3.7.
All original24-table row fingerprints/counts match baseline, including every OSM record,
saved route, analysis, optimization scenario/solution/comparison and MCDA evaluation.
Only three new GeoAI snapshots and14 new audit records were created by live acceptance;
unit/live test rows were rolled back. Existing .env is byte-for-byte unchanged.

Local Host/Origin validation, strict schemas, bounded requests, rate limits, server-derived
facts and minimal provider context reduce attack surface. Feature labels/imported text are
untrusted data, never instructions. There is no arbitrary execution or model-granted consent.
This is not proof against every possible prompt injection or production-grade user isolation.
The optional HTTPS endpoint is administrator-configured; no user/model arbitrary URL tool exists.
No real LLM API credential was available, so live model compatibility/quality/cost remain unverified.

## Limits and remaining acceptance

Deterministic grammar recognizes six known study references and exact selected/saved UUIDs;
unknown places/implicit radii/arbitrary multi-intent prose require clarification or a typed tool.
Search pages <=200, maps <=2000/result, raw output <=4MB, last6 results/20 messages,
32 sessions/24h idle expiry;12 requests/minute/two concurrent sessions. Bounded requests retain
existing public OSRM quotas/cache; do not use public demos for unarranged production loads.
The optional planner has one request/turn,1200 tokens,30/hour/process,<=6calls and25s default timeout.
LLM failure is explicit; deterministic mode remains independently usable.

OR-Tools confirmed solving <=12stops/10s per variant/3variants/6vehicles. Added fleet members
clone the first supplied vehicle specification, explicitly hypothetical; multi-depot size
comparison requires separately configured scenarios. Fewer served stops can reduce distance;
comparison tables expose assigned/unassigned demand. No global optimality claim.
MCDA changes use saved raw values, not live data refresh; weights/demand are assumptions.
Car road fastest-path metrics are not verified truck access, tolls, live traffic or guaranteed
shortest-distance paths. Town/airport representative anchors are not verified cargo/terminal gates.
No official flood/zoning/land-cost/raster/isochrone data or legal developability was invented.

Session memory is single-process and is lost on restart unless explicitly saved. Snapshot
retrieval expires after7 days; at most100 snapshots and1000 audit rows. Physical expired-row
cleanup requires reviewed operator maintenance; no silent eviction. Production authentication,
shared quotas, distributed jobs and actual external-model evaluation are not implemented.

Phase7 code/API ready for review; full visual acceptance awaits checklist sign-off. Phase8
readiness is conditional, especially if LLM service is to be enabled. **No Phase8 work started.**
