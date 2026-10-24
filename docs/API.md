# Phase 2 API contract

Interactive docs: http://127.0.0.1:8000/docs.
Generated snapshot: [openapi.json](openapi.json).

| Method | Path | Behavior |
| --- | --- | --- |
| GET | /health | Version, liveness, mode and configuration presence; no credentials |
| GET | /ready | Live PostGIS/schema verification or explicit fixture limited status |
| GET | /api/capabilities | Available operations and unavailable later phases |
| GET | /api/industrial/features | PostGIS or explicitly synthetic fixture FeatureCollection |
| POST | /api/spatial/measure | Validated WGS84 geodesic distance/perimeter/area |
| GET | /api/discovery/study-areas | Six initial search targets, no invented boundaries |
| GET | /api/locations/search?q=... | Explicit Malaysia place lookup, up to five OSM references |
| POST | /api/discovery/jobs | Start bounded Overpass query and PostGIS import; HTTP 202 |
| GET | /api/discovery/jobs | Most recent 30 persisted discovery jobs and reports |
| GET | /api/discovery/jobs/{id} | Job status, parameters and coverage/failure report |

## Querying imported data

- Repeat categories for every category. Values: industrial, industrial_park,
  warehouse, logistics_hub, port, airport, road, rail, study_area.
- q: case-insensitive substring of imported names, maximum 200 characters.
- bbox: west,south,east,north in EPSG:4326. Tests full geometry intersection.
- center: longitude,latitude, paired with radius_km above 0 and at most 200 km.
  Uses PostGIS geography ST_DWithin in meters.
- limit: 1–1000, default 250; offset: 0–100000.
- If both bbox and radius are supplied, both restrictions apply.
- All selected categories use union semantics. Objects have one ID and retain
  every tag-derived category membership, including overlaps.

```text
/api/industrial/features?categories=warehouse&categories=industrial&categories=port&bbox=101.2,2.7,101.9,3.4
```

RFC 7946-compatible FeatureCollection; meta includes mode, EPSG:4326, total,
returned, offset, limit, has_more, category_counts, missing_categories,
failed_categories, warnings and attribution. Counts are before pagination.
Feature properties include source, license, source_id, dataset_id, imported_at,
synthetic, boundary_status, raw OSM tags, OSM version/timestamp and source URL.

The frontend loads 1,000-object pages for its complete map/export result, capped
at 10,000 with a visible warning. The table uses independent 250-object pages.
A page export exports only that page; the heading export exports loaded map
results with metadata/attribution. Selected-feature export preserves source/license.

## Discovery/import

```json
{
  "categories":["warehouse","industrial","logistics_hub","port"],
  "center":[101.3966735,3.0027625],
  "radius_km":5,
  "label":"Port Klang — OSM town reference"
}
```

Alternatively supply bbox instead of center/radius_km. Exactly one scope is
required. Radius maximum 10 km; boxes maximum 400 km² and 1 degree per side.
These are user search footprints, not official facility boundaries.
Maximum eight category selections; study_area is not an OSM discovery category.
Arbitrary QL, SQL, Python, provider URLs and unsupported fields are rejected.

POST returns {"id":"UUID","status":"queued"} immediately after saving the job.
Poll history/status at a moderate interval. States: queued, running, completed,
failed, interrupted (server restarted without this process owning the job).
Reports contain requested category counts (including zeros), missing and failed
categories, skipped-record counts/examples, OSM snapshot time, provider cache
status, inserted/updated/preserved-newer counts, parameters and limitations.
One combined provider query either succeeds or marks every requested category
failed; partial Overpass timeout responses are never imported as complete data.

Valid source objects commit in one transaction with category links and report.
Invalid/incomplete geometry is skipped and counted; source geometry is not
silently repaired, replaced by a centroid or invented. A database error rolls
back the transaction. Stable IDs deduplicate by OSM type/id in one canonical dataset.

Discovery and location endpoints require enabled discovery, a loopback client,
an allowed local Host, and an allowed Origin if supplied. Imports/history also
require PostGIS mode. They are local development operations, not public APIs.
Bind to loopback and use one process; do not run CLI imports concurrently with UI imports.

## Limits and errors

Providers are configurable backend environment variables. HTTP TLS verification
uses the OS certificate store. Overpass: 60-second declared query timeout,
32 MiB declared server memory, 85-second HTTP timeout, 25 MB decoded response
limit and 12,000-object limit. No automatic provider retries or endpoint rotation.
24-hour response cache; 12-second minimum request spacing. 429/503/504 establish
a cooldown (at least 60 seconds; integer Retry-After honored up to one hour).
Nominatim: explicit submits only, identifying User-Agent, Malaysia country filter,
1.1-second minimum spacing, 7-day cache. Cache holds at most 100 files per provider.

Errors use {"error":{"code":"...","message":"...","details":[]}}.
422 invalid inputs; 403 local access denied; 409 wrong mode/import busy;
429 per-process API throttling; 502 place provider error; 503 database unavailable.
Background provider failures appear as failed job reports. No fixtures replace
an empty or failed real search. Successful calls include X-Request-ID and nosniff.

## Geodesic measurements and later phases

```json
{"geometry":{"type":"LineString","coordinates":[[0,0],[1,0]]},"crs":"EPSG:4326"}
```

Returns length_km (about 111.31949), area_sq_km, CRS and methodology.
Arbitrary upload, optimization and GeoAI endpoints remain absent.
Phase 3 routing is available locally as documented below.

## Phase 3 routing

All paths below require enabled routing, a loopback client, an allowed local Host
and exact allowed Origin if supplied. POST save and feature-anchor/nearest
operations require PostGIS. They are not public unauthenticated production APIs.
OpenAPI snapshot: [openapi.json](openapi.json).

| Method/path | Result |
| --- | --- |
| GET /api/routing/provider | Configuration, last upstream status/cooldown, limits and attribution; no live probe |
| POST /api/routing/route | Provider routes, geometry, metrics, legs, snapped waypoints and provenance |
| GET /api/routing/features/{uuid}/anchor | Actual nonsynthetic imported feature reference and source metadata |
| GET /api/routing/features/{uuid}/nearest-warehouse | Geographic nearest different warehouse, not network nearest |
| POST /api/routing/saved | Idempotently save selected validated cached route to routing_references |

Example request (public town reference coordinates from recorded geocoder results):

```json
{"points":[{"coordinates":[101.5234848,3.6900079],"label":"Tanjong Malim town reference"},{"coordinates":[101.3966735,3.0027625],"label":"Port Klang town reference"}],"profile":"car","alternatives":true,"max_snap_m":1000}
```

A point accepts exactly one of coordinates or feature_id (UUID), plus an optional
label of at most 160 characters. Feature coordinates are resolved on the server.
Extra fields are forbidden. Finite WGS84 longitude/latitude; 2–8 ordered points;
consecutive references at least 1 m apart; geodesic chain at most 3,000 km.
Profile only car; max_snap_m integer 25–2,000. Alternatives are queried only for
two points and may be absent. Multi-stop order is never optimized.

Success includes calculation_id, routes[{index,geometry,distance_m,duration_s,
legs}], waypoints[{coordinates,snapped_coordinates,snap_distance_m,road_name,
label,anchor_method,...}], provider, profile, heavy_vehicle_verified=false,
retrieved_at, cached, alternatives_requested/queried, CRS, warnings and attribution.
Geometry is a detailed LineString in EPSG:4326. Units are meters/seconds.
Maximum 3 routes, 50,000 vertices/route. Invalid provider geometry/metrics are
rejected, never replaced with fabricated results.

Save request:

```json
{"calculation_id":"64-character-lowercase-hex-from-route-response","route_index":0}
```

The example calculation ID is a placeholder. Save reads only a validated
server cache entry. It does not accept client geometry, SQL or file paths.
Expired cache returns 409 (recalculate). Success returns id/status/distance_m/
duration_s/message. Same calculation retrieval + index returns the same row ID.

422 invalid coordinates/stops/snap/profile or no road route/segment; 403 local
access denied; 404 feature/warehouse missing; 409 wrong mode/cache expired;
429 API/provider rate limit/busy/cooldown; 502 malformed upstream result;
503 provider disabled/unavailable or sanitized DB/cache error. Retry-After may
be present; the frontend displays the structured error. No automatic fallback.

Provider timeout 20 s (connect 8 s), response cap 8 MiB, minimum 1.1 s spacing,
12 upstream calls/minute, one concurrent call. 24-hour normalized cache capped
at 128 route files. 429/503/504 cooldown minimum 60 s, integer Retry-After up to
one hour. Cache does not change the original retrieval time. These safeguards
are single-process/local, not production shared quotas. Road matrices and
network isochrones remain unavailable; no circular service-area substitutes.

## Phase 4 spatial analytics and saved history

All operations require ANALYTICS_ENABLED, local loopback/allowed Host/Origin and
DATA_MODE=postgis. Matrix also requires enabled routing. No fixture fallback.

POST /api/spatial/analyze:

```json
{
  "operation":"buffer",
  "title":"Warehouse 5 km coverage",
  "a":{"ids":["REAL_IMPORTED_FEATURE_UUID"]},
  "b":{"query":{"categories":["industrial"],"bbox":[101.25,2.72,101.87,3.4]}},
  "distance_m":5000,
  "crs":"EPSG:4326"
}
```

UUID is a placeholder; choose a real imported record. LayerInput accepts exactly
one of ids (≤200), query (bounded bbox or center/radius, categories; no offset/q),
features (≤200 objects {id,name,geometry}), or saved_id (UUID of Phase 4 analysis).
Full bounded query is used up to 2,000 records; larger input returns 422 rather
than silently truncating. Coordinates and geometries are validated. EPSG:4326 only.

operation allowlist: buffer, intersection, clip, union, dissolve, difference,
spatial_join, nearest, aggregate, clusters, grid. B required for binary operations.
Parameters: distance_m >0..50000; predicate intersects/within/contains/nearest;
eps_m 25..20000; min_points 2..100; grid_m 100..20000; dissolve_by all/category.
Buffer optionally matches supplied B. Clip/aggregate B requires polygon geometry.
Empty intersections/clips are successful empty collections.

Response: FeatureCollection with title/operation/status, features, input_features,
statistics, rows, inputs, parameters, crs, calculation_crs, executed_at,
processing_ms, attribution, warnings, calculation_id. GeoJSON is WGS84; metric
operations use local AEQD meters. Full contract and methods: PHASE4_ACCEPTANCE.md.

POST /api/analysis/regions:
{origins:[RoutePoint...],radius_km:5,categories:["industrial","industrial_park"]}.
1–6 origin references, radius 0.1–50 km. Unique mapped object counts/density,
road source segment counts and nearest footprint geography distance to warehouse,
port, airport and hub. No road access inferred from a segment count.

POST /api/routing/matrix:
{origins:[RoutePoint...],destinations:[RoutePoint...],max_snap_m:1000,
score_reference_minutes:60}. 1–5 per side. Phase 3 coordinates OR feature_id
schema applies. Real OSRM distance/duration matrices, null unreachable pairs,
nearest supplied candidate by time and explicit heuristic score. Car only;
distance follows fastest path. No fallback_speed, no fabricated route lines.

GET /api/network/capabilities returns isochrone:false and reason.
POST /api/network/isochrone returns 501 (unsupported), never a buffer polygon.

POST /api/analysis/saved: {calculation_id:"validated-64-hex"}.
GET /api/history/{analyses|routes}?limit=25&offset=0 (limit 1–100).
GET /api/history/{kind}/{uuid}: full persisted result with saved_id.
POST /api/history/{kind}/{uuid}/archive: {confirmed:true}; preserves row/geometry.
POST /api/history/{kind}/{uuid}/restore: {confirmed:true}; removes archived_at.
No permanent DELETE endpoint. Wrong kind/UUID/schema rejected. Phase 2 discovery
results cannot be archived through Phase 4 analysis endpoints. Saving a previously
archived calculation restores its metadata; no input features are overwritten.

403 local access denied; 409 wrong mode; 422 invalid/missing/too-large geometry,
query/selection/history record; 501 unsupported isochrone; 503 DB/cache/provider
unavailable; routing errors preserve their controlled status. No arbitrary SQL,
Python, shell or unrestricted file paths. See openapi.json for schemas.


## Phase 5 — local logistics optimization

All /api/optimization endpoints require the enabled loopback workspace, allowed Host
and exact configured Origin, plus live PostGIS. Responses use existing structured
error envelopes. Raw database/provider exceptions are never returned.

| Method and path | Behaviour |
| --- | --- |
| POST /api/optimization/scenarios | Validate and save an immutable Scenario snapshot; 201 + id/scenario. GIS feature anchors resolved from real PostGIS. |
| GET /api/optimization/scenarios | limit 1–100, offset ≤10000, archived=false/true; metadata and latest summary. |
| GET /api/optimization/scenarios/{UUID} | Reload parameters; archived snapshots readable. |
| POST /api/optimization/scenarios/{UUID}/duplicate | Copy into a new snapshot, preserve original and normalized records. |
| POST /api/optimization/scenarios/{UUID}/archive | {confirmed:true}; recoverable archive. |
| POST /api/optimization/scenarios/{UUID}/restore | {confirmed:true}; restore. |
| POST /api/optimization/scenarios/{UUID}/solve | 202 job_id. At most one active job; 429 when busy. |
| GET /api/optimization/jobs/{UUID} | queued/running/completed/failed/cancelled/interrupted and safe processing stage. |
| POST /api/optimization/jobs/{UUID}/cancel | {confirmed:true}; cooperative cancellation. |
| GET /api/optimization/scenarios/{UUID}/results | Latest saved complete solution, provider metadata, matrix, schedules, geometry, unassigned and warnings. |
| POST /api/optimization/matrix | Scenario body; validated 2–24 node OSRM road matrix, no geometry/fallback. Prefer solve jobs for larger workloads. |
| POST /api/optimization/compare | {ids:[2–4 saved scenario UUIDs],name}; persisted comparison snapshot. |
| GET /api/optimization/vehicles?scenario_id=UUID | Snapshot fleet. Editing fleet is performed by saving a new complete scenario. |
| POST /api/optimization/import | {format:csv/geojson,content,demand_context}; validate 1–20 candidate stops, no filesystem access. |

Scenario schema: name, capacity_unit, demand_context (hypothetical/user_supplied), notes,
depots[1–4], vehicles[1–6], stops[1–20], objective
(distance/time/cost/vehicles/balance), allow_unassigned, solver_seconds 1–20,
max_snap_m 25–2000. Locations contain id, name, coordinates [longitude,latitude],
optional feature_id/source_id and window [start_s,end_s]. Vehicles contain enabled,
integer capacity, start_depot/end_depot IDs, window, max_distance_m,
max_duration_s and explicit cost_per_km/fixed_cost/driver_cost_per_hour/
fuel_l_per_100km/fuel_price_per_l. Stops contain positive integer demand, service_s,
priority 1–10, mandatory, kind delivery/pickup, optional pickup_id. Extra fields rejected.

Result status: best_found/optimal with a feasible validated solution, infeasible only
when established, timeout, or no_solution_found. solver_status/code, elapsed/time_limit,
proven_optimal, method and objective units are retained. Successful optional service can
still leave unassigned stops. Matrix summary and final routed_summary are distinct.
route.geometry is MultiLineString or null. road_geometry_constraints_verified explicitly
indicates final road timing/distance checks; missing geometry never becomes a substitute
line. Final via-point estimates may differ from matrix objective/schedule.
No standard car result is certified for heavy vehicles.

The public OSRM guard, timeout/cooldown, matrix dimensions, response validation and
loopback controls apply. POST bodies above 1.5 MB are rejected before JSON parsing.
The production template leaves optimization disabled pending authentication, durable
jobs and an appropriately provisioned routing service.


## Phase 5 acceptance-review corrections

Malformed optimization GeoJSON (including array/null/invalid Feature objects) returns
HTTP 422 with a controlled message. No arbitrary input or connection error is exposed.
The independent solver validator now checks node identity, service duration and
intermediate depot placement. Optional-service penalties include all depot cost arcs.
Assignment/schedule CSV exports with zero routes include a context row
`record_type=no_vehicle_routes`, status, unassigned stops, assumptions and attribution.
No API shape, database migration or Phase 1–4 endpoint was removed.

Fresh evidence and incomplete/unsupported/untested feature inventory:
[PHASE5_REVIEW.md](PHASE5_REVIEW.md). Comparison snapshots are stored by POST compare,
but listing/reopening comparison history has no endpoint/UI yet. Standard-car routing
and locally guarded optimization must not be treated as verified truck dispatch.


## Phase 5 completion: saved comparison history and multi-solution maps

The earlier note about missing comparison retrieval is superseded by these endpoints:

| Method/path | Behaviour |
| --- | --- |
| GET /api/optimization/comparisons?limit=25&offset=0 | Paginated name/time/scenario-count history; limit 1–100, offset 0–10000 |
| GET /api/optimization/comparisons/{id} | Stored comparison rows, warnings, matrix/final-road metrics and snapshot metadata |
| GET /api/optimization/comparisons/{id}/solutions | Exact historical saved solutions, bounded to 2–4; read-only |
| POST /api/optimization/compare | Existing endpoint; now persists schema_version=2 and exact solution IDs |

Missing snapshots return 404. Invalid IDs/limits return 422. Legacy snapshots resolve
solutions at snapshot creation time and check metrics; mismatch/unavailable history returns
409 without substituting latest geometry. All use existing local Host/Origin guards.
No schema migration or legacy record backfill is performed.

Frontend overlays namespace scenario/solution/vehicle identities, colour scenarios, dash
vehicles and apply documented pixel-only line offsets. GeoJSON exports preserve original
EPSG:4326 road coordinates and include visibility/provenance metadata. The client rejects
more than 300,000 visible vertices; it does not silently truncate. Comparison CSV preserves
stored matrix and final-road metrics separately. Standard car profile, not truck verified.


## Phase6 site-selection API (v0.6.0)

| Method/path | Contract |
| --- | --- |
| GET /api/sites/catalog | Criteria labels, units, native availability, descriptions and limits |
| POST /api/sites/ahp | matrix square1–8; returns eigenvector weights,lambda_max,CI,RI,CR/consistent |
| POST /api/sites/prepare | Validated SiteScenario; actual resolved geometries/anchors/criterion values/status/provenance, no scores |
| POST /api/sites/evaluate | SiteScenario; calculated GeoJSON,rankings,normalized values,contributions,ranges,weights,AHP,sensitivity,calculation_id |
| POST /api/sites/import | format csv/geojson,content;1–12 valid WGS84 user candidate geometries, no DB writes |
| POST /api/sites/saved | calculation_id of validated cache≤24h; transactionally persists immutable scenario/candidates/values/result, idempotent repeated save |
| GET /api/sites/saved?limit=&offset= | Bounded saved evaluation history |
| GET /api/sites/saved/{id} | Exact saved result+scenario/saved IDs, no re-query of providers |

SiteScenario fields: name,candidates,criteria,method wlc/ahp,ahp_matrix,allow_inconsistent,
missing_policy reject/exclude_criterion/exclude_candidate,radius_m,targets(port/airport/network),
max_snap_m,sensitivity_delta. Candidate chooses feature_id OR point/polygon geometry;kind
hypothetical_site/reported_existing_facility;values per criterion require finite nonnegative
value and provenance note. Mapped UUIDs are re-resolved from PostGIS, not caller geometry.
Criteria whitelist: source gis/network/user, direction cost/benefit, nonnegative weight.
Unavailable official data cannot use source gis. Network criteria need exact selected target.
AHP weights criteria then WLC scores alternatives. Missing values are never filled with zero.

All POST/expensive GET use existing local analytics Host/Origin/PostGIS guard; no fixture
analysis fallback. HTTP422 invalid/missing input or absent saved result;413 oversized body;
403 foreign/disabled workspace;503 controlled DB/provider operation failure. Provider
unavailability appears as missing criterion evidence; scoring follows explicit missing policy.
12 candidates/8 criteria/25k combined vertices,1MB import/1.5MB POST/4MB result;SQL parameterized.
Migration0003 only adds four site tables. Updated complete schemas are in openapi.json.


## Phase 7 — GeoAI Copilot

All execution/history/context routes use existing enabled local Host/Origin/PostGIS guard.
`GET /api/geoai/health` returns allowlisted configuration status, never keys.
`GET /api/geoai/tools` publishes 23 typed, allowlisted tool schemas.
`POST /api/geoai/sessions` creates bounded in-memory context (no database write).
`POST /api/geoai/chat`: {session_id?, message<=1800, language:auto|ms|en,
mode:deterministic|llm, selected_feature_ids?:UUID[<=20], scenario_id?:UUID|null,
mcda_id?:UUID|null}. Explicit null clears saved-scenario context; omitted references retain it.
`POST /api/geoai/execute`: {session_id?, language:ms|en, calls:[{tool,arguments}]}.
Entire batch (<=6) validates before first execution. No arbitrary SQL/code/URL/file tool.
`GET /api/geoai/context/{id}` returns progress/context; 24h idle expiry, 32 active sessions.
`POST /api/geoai/sessions/{id}/cancel` requests cooperative cancellation and invalidates pending consent.
Cancellation cannot interrupt an in-flight provider call or OR-Tools search.
`POST /api/geoai/save`: {session_id} returns a preview, not an automatic DB write.
`POST /api/geoai/confirm`: {session_id,token,confirmed:true} consumes a random five-minute,
session-bound token once. Optimization rechecks the exact scenario digest against preview.
`GET /api/geoai/sessions?limit=25&offset=0` lists explicitly saved snapshots.
`GET /api/geoai/sessions/{saved_uuid}` reloads an unexpired snapshot into a new context ID;
pending confirmations are never replayed.

Chat/execute/confirm returns {session,results,text,language,mode,partial,provider}.
Clarification is an HTTP200 structured response with clarification:true/results:[];
it never masquerades as successful GIS output. Each result includes status, data,
features, rows, summary, CRS, timestamp, methodology, attribution and limitations.
Stop dependent tools after any failure; partial completion is explicit. Confirmation
previews are pending_confirmation, never completed solver results.

Read-only defaults: search, feature attributes, GIS analysis, route/matrix calculations,
saved histories, MCDA snapshot evaluation/explanation/sensitivity and saved-solution
comparison. Buffer distance is metres. Radius is km. Geometry EPSG:4326.
Feature-reference proximity uses actual PostGIS geography footprint distance;
named-town radius uses an existing geocoded search reference. Routing uses actual
OSRM car fastest-path metres/seconds, not verified truck routing or guaranteed shortest distance.
Warehouse ranking requires a complete first search page with <=23 warehouses;
large sets request narrowing rather than silently omitting candidates. Source search
pages <=200, explicit offset. Spatial tool map output <=2000; raw data <=4MB.
12 execution requests/minute, two concurrent sessions, 90s between-tool budget;
GIS statements retain existing bounds. Existing provider quotas/cache still apply.
Confirmed solving uses supplied/hypothetical saved scenarios, <=12 stops, <=10s/variant,
<=3 fleet variants, <=6 vehicles; no overwriting saved scenario/solutions. New fleet
members explicitly clone the first supplied vehicle specification. Multi-depot
fleet-size comparison is rejected unless configured as separate saved scenarios.

Optional provider: GEOAI_PROVIDER=openai_compatible, backend-only GEOAI_API_KEY,
GEOAI_MODEL, HTTPS GEOAI_BASE_URL and GEOAI_TIMEOUT_S. Default disabled.
One non-streaming tool-planning request/turn, max_completion_tokens1200,
<=6 calls, <=100KB response, <=30 model requests/hour/process, no retry storm.
Model prose/reasoning is discarded; numeric/factual explanations are deterministic
from validated GIS outputs. The adapter uses the Chat Completions function-tool
contract; it requires a compatible model/provider and does not imply every model
supports this legacy-compatible protocol. Missing/invalid credentials: structured
clarification directs the user to deterministic mode; no fake model answer.
Only explicit question/context IDs/places can be used by model tools. Backend validates
all arguments and never accepts model-granted confirmation. No prompts or secrets in HTTP logs.

Persistence migration0004_geoai adds only geoai_sessions/geoai_confirmations (RLS/revokePUBLIC).
Saved snapshots <=4MB, maximum100; retrieval expires after7 days. Audit metadata <=1000rows;
no raw chain-of-thought or API keys stored. Expired physical rows are retained until
operator-reviewed cleanup; quota prevents unbounded growth and no record is silently evicted.
Local access controls do not constitute production multi-user authorization.

Provider contract references, fetched24 Oct2026:
[Function calling](https://developers.openai.com/api/docs/guides/function-calling) and
[Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
