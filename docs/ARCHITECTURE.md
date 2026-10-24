# Architecture and Phase 4 boundaries

Browser → React/Vite → FastAPI → explicit provider (fixture or PostGIS).
OpenFreeMap supplies the geographic basemap directly to MapLibre; it is separate
from queried industrial records. Drawn geometries stay in the local app/backend. Explicit place searches send public place names to the configured geocoder; discovery sends the selected search area/categories to Overpass. Database credentials never go to either provider.

## Frontend

TanStack Query owns API loading, errors, retries, cache and AbortSignal cancellation.
Zustand owns selection, active tool, category visibility and display order.
Study extents are approximate map views and can be overridden by custom bounds.
No proprietary facility data, exact industrial boundaries, credentials or fake
statistics are embedded. Read-only source summaries use actual API counts.

MapLibre uses one source per display category. Overlapping memberships are
assigned to the first enabled category so each feature is drawn once. Map-side
copies carry a stable internal feature identifier because renderers may transform
GeoJSON feature IDs. That internal property does not mutate exported API records.
User sketches are a separate source.
MapLibre 6.4.1 is the pinned patched release. A predev/prebuild esbuild step
bundles its official worker as a local classic .cjs worker; Vite and Netlify set
the JavaScript MIME type. This avoids the observed module-worker compatibility
issue in the in-app browser and preserves local-only worker loading. Feature labels use DOM textContent, never
untrusted HTML.

The button primitive follows the source-owned shadcn/ui Radix Slot/CVA model.
This is a tailored GIS interface, not an imported dashboard template.
Dark mode changes application surfaces; basemap style has its own explicit control.

## Backend and data

Pydantic enforces WGS84 coordinate bounds, finite numbers, supported geometry
types, closed polygon rings, valid Shapely geometry, maximum nesting and a
10,000-vertex limit. Measurements use PyProj WGS84 ellipsoidal length/area with
polygon hole orientation normalized. Length on a polygon is perimeter.
Calculations are suited to the Malaysian study scope, not global polygons larger
than a hemisphere. Radius filtering on fixtures projects geometry into a local
azimuthal equidistant CRS; PostGIS uses geography ST_DWithin in meters.
No planar degree arithmetic is used as kilometer distance.

Phase 2 adds local-only, typed background discovery imports; geometry measurement remains stateless. No file
uploads, SQL execution endpoint, Python execution or LLM execution exists.
CORS uses configured exact origins. Error responses hide provider credentials.
A bounded per-process request guard is a local safeguard; authentication,
distributed quotas and production gateway limits remain later work.

## Schema

Twelve normalized tables:

| Table | Responsibility |
| --- | --- |
| datasets | Source, license, synthetic flag, import log |
| categories | Controlled infrastructure category dictionary |
| spatial_features | Geometry, name, source ID, provenance link, boundary status |
| feature_categories | Many-to-many category memberships |
| study_areas | User-defined multipolygon study areas and provenance |
| analysis_jobs | Operation, parameters, status, study area FK |
| analysis_results | Job FK, geometry and structured summaries |
| candidate_sites | Spatial feature FK, criteria and analysis FK |
| optimization_scenarios | Named optimization scenario and parameters |
| vehicles | Scenario/depot FKs, positive capacity and units |
| shipments | Scenario/destination FKs, positive demand, units, optional windows |
| routing_references | Provider/profile/geometry/provenance and scenario FK |

Industrial parks, facilities, warehouses, logistics hubs, ports, airports, roads
and rail share the same spatial_feature/provenance model and normalized category
memberships. This avoids duplicate geometries for multi-category facilities.
Foundation vehicles/shipments remain unchanged. Phase 5 implements logistics workflows using optimization_scenarios snapshots and additive logistics_* / optimization job/solution/assignment/comparison tables; see PHASE5_ACCEPTANCE.md at repository root.

Alembic creates PostGIS if necessary, spatial and lookup indexes, foreign keys,
deduplication constraints and row-level security. Migrations never seed facilities.
The optional read group script grants only necessary Phase 1 reads. The connection
uses NullPool to avoid duplicating Supabase session pooling; use a session pooler
or direct connection in Phase 1, not untested transaction-pooler semantics.
DDL compilation and live Supabase/PostGIS migration were verified on 2026-10-24.
See DATABASE_INTEGRATION.md for actual schema and integration test results.

## Phase boundaries

1. Foundation (complete).
2. Live industrial discovery/normalization/imports and coverage reporting.
3. Routing provider abstraction with actual road geometry and explicit profiles (complete locally).
4. Buffer/overlay, clustering and network matrices (complete locally); isochrones explicitly unsupported.
5. OR-Tools constrained logistics optimization using validated road matrices and real route geometry (complete locally).
6. Explainable warehouse MCDA and sensitivity.
7. English/Malay GeoAI with strict allowlisted tool arguments and provenance.
8. Authentication, shared throttling, monitoring, broader performance/security QA.

Future providers must never masquerade straight lines as routed road geometry,
buffers as network service areas, or unavailable live sources as synthetic results.


## Real data discovery (Phase 2)

Browser → local FastAPI discovery API → cached Nominatim / Overpass → validated
OSM points/ways/multipolygon relations → transactional PostGIS canonical dataset.
There is no fixture fallback. Discovery uses existing datasets, spatial_features,
feature_categories, analysis_jobs and analysis_results; no new migration is required.
Phase 2 used 0001_foundation. The current verified schema is 0002_logistics after the additive Phase 5 migration.

Each OSM type/id maps to a stable UUID5. A canonical dataset plus unique source
constraint deduplicates overlapping areas. Tag-derived memberships are recalculated
on refresh and source versions prevent older caches replacing newer objects.
Geometry, category links, report and job completion commit together. Raw OSM
provenance is retained; invalid objects are counted and omitted. Overlapping ways
and relations with different IDs are retained. Source deletions are not reconciled.

Queries run ST_Intersects on geometry and ST_DWithin on geography. Geometry GiST
indexes serve bbox queries; the geography cast has no separate expression index.
Radius performance has been exercised on the current ~5,000-object dataset;
larger datasets need query-plan review and likely a geography index migration.

One process owns one background import. Job results persist, but work is not
resumed after a crash/restart. Reports mark orphaned running jobs interrupted.
Caches and provider locks are local to one machine/process, not distributed.
Production discovery is disabled until authentication, shared quotas and a suitable
provider arrangement are in place. CORS alone is not authentication.

The map/export query accumulates all pages up to 10,000 objects, with a visible
cap warning. The attribute table paginates independently. Both use actual PostGIS
queries, cancellation signals, loading and error states. Source labels use escaped
text. Credentials remain backend-only and SQLAlchemy hides statement parameters.

Primary policy sources: Nominatim usage policy, Overpass resource guidance and
OpenStreetMap copyright/ODbL (linked in README and the interface).

## Road-network routing (Phase 3)

Browser route store → strict FastAPI routing API → server-resolved PostGIS
feature anchors / explicit user references → bounded normalized route cache →
RoutingProvider protocol → OSRM-compatible HTTPS provider. Geometry is provider
LineString, not an imported road overlay or a straight-line construction.
Distance/duration/legs are preserved after sanity and consistency validation.

The server resolves feature UUIDs to ST_PointOnSurface or source points, rejects
synthetic records, and preserves source IDs/anchor method. Geographic nearest
warehouse uses ST_Distance geography on actual footprints and explicitly does not
claim driving-distance ranking. It then supplies a reference to the road planner.

Cache identity includes provider/profile/points/labels/snap settings and schema.
A 24-hour cached DTO keeps original retrieval time; a fresh fetch gets a new
timestamp. Save uses cache ID + selected index only. UUID5 of calculation ID,
retrieval time and index gives idempotent rows in routing_references with
LineString EPSG:4326 and full provenance/metrics. No migrations were required.

OSRM calls are serialized with 1.1-second spacing and 12 upstream calls/minute.
HTTP 429/503/504 establishes cooldown; no retry storm or alternate-provider
rotation. Timeouts, decoded-response/vertex/stop limits and strict metric,
leg, snap and geometry validation bound resource use. Errors produce no route.
Provider metadata states configured/last success/failure; configuration alone is
not asserted availability. No periodic upstream availability probes are sent.

Routing and save endpoints require local loopback + allowed Host/Origin.
The Render preparation blueprint disables routing and discovery. A shared cache,
quotas, authentication and properly scoped writer role are production work.

Frontend Zustand stores ordered stops, result, selected alternative and map
picking state across module changes. AbortController + revision tokens ignore
stale route/nearest results, and save receipts belong to the selected route.
MapLibre route sources/layers restore after style changes, sit above feature
layers, and use basemap-supported Noto Sans marker glyphs. Completed GIS sketches
also persist across map unmounts in the workspace store; reload resets memory.

The classic official MapLibre worker/proxy fixes remain intact. Routing receives
its own longer Vite proxy timeout. Standard-car provider estimates carry no truck,
live-traffic, cargo-gate or legal-access verification.


## Advanced spatial processing (Phase 4)

Strict LayerInput → bounded PostGIS query/selected IDs/user sketch/saved result →
validated GEOS geometry → local PyProj AEQD meter coordinates → Shapely overlay,
buffer, STRtree joins/nearest, spatial-hash DBSCAN or metric grid → WGS84 output
with Geod area/separation, source provenance and validated result limits.
No coordinates measured as planar longitude/latitude degrees. Polygon holes
are oriented for ellipsoidal area. Combined extent limited to 250 km from the
projection center in the Malaysian region, not a national single projection.

Inputs are snapshotted in result.input_features for traceability/map context.
Matrix/region comparisons use the same result contract and server-only cache.
Save resolves only a calculation hash from that validated cache, storing a
GeometryCollection + full JSONB FeatureCollection in existing analysis tables.
UUID5 makes save idempotent; JSONB archived_at soft deletion preserves geometry
and supports restore. Saved route records retain Phase 3 metric/provenance.
History queries extract just list metadata in SQL before pagination; full result
geometry is read on Open, avoiding geometry JSON transfer for every history row.

OSRM Table uses the Phase 3 provider abstraction and the same serialized upstream
HTTP/rate/cooldown guard. Each null pair remains unreachable. No fallback_speed
or straight-line substitution. Metrics follow fastest car routes. Matrix produces
reference points, not fake route lines. Per-origin fastest candidate and a
documented travel-time heuristic score are reported. No isochrone adapter or
validated directed graph is configured; the capability is explicitly false/501.

Regional windows use bounded geography queries for unique mapped counts,
mapped-road-segment counts and geography nearest infrastructure proximity.
This is coverage/concentration, not economic output or proof of legal access.
Reference circles and cluster hulls are not authoritative industrial boundaries.

React AdvancedWorkspace shares up to five result layers in Zustand across modules.
MapLibre supports mixed geometries, grid fill, cluster/noise colors, heatmap of
actual representative points, result selection, visibility and style restoration.
The results panel contains inputs, params, time, warnings, stats/charts and paged
attributes; GeoJSON and CSV exports preserve provenance. CSV strings are quoted
and formula-like prefixes escaped. API errors create no fabricated layers.

Limits: 2,000 query objects/input, 200 selected/inline inputs, 4,000 output
geometries, 200,000 output vertices, 10,000 join pairs, 8 MB response; one geometry
operation at a time. SQL statements bounded to 20 s and processing checks a
20 s best-effort budget. Browser cancellation stops rendering stale results;
already-started server work may finish/cache. No distributed worker or quotas.
Public analytics disabled in the Render preparation template.


## Phase 5 execution and persistence
Browser → guarded local optimization API → immutable scenario snapshot →
one bounded worker → cached/validated asymmetric OSRM table → OR-Tools RoutingModel →
independent hard-constraint validation → actual OSRM geometry chunks →
separate final-road limit/cost checks → normalized PostGIS solution/assignments.

Job stages are persisted; process-local concurrency is one. Cancellation is cooperative.
Restart marks unfinished jobs interrupted. Public distributed processing remains unsupported.
Depots/stops use POINT4326, assignments MULTILINESTRING4326 with GiST and RLS;
all legacy GIS/route/analysis records are preserved. Inputs/results are bounded.
Detailed API contracts and actual acceptance evidence are in API.md and ../PHASE5_ACCEPTANCE.md.
