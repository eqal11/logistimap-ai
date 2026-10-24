# Windows development

Requirements: Windows x64, Node 24.x/npm 11.x, Python 3.12, Git. No Docker,
WSL, local PostgreSQL or local routing engine is required.

## Fresh checkout setup

Open PowerShell at the repository root (the directory containing this file).
Commands use npm.cmd and the venv Python directly; no execution-policy changes
or activation scripts are required.

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.lock.txt
Set-Location frontend
npm.cmd ci
Set-Location ..
```

Runtime-only Python installation uses backend/requirements.lock.txt.
requirements.txt and requirements-dev.txt describe version ranges; lock files
record the versions actually tested. Recreate a virtual environment if you move
this directory to another path: Python virtual environments are not portable.

## Run (two terminals)

Terminal 1, repository root:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, repository root:

```powershell
Set-Location frontend
npm.cmd run dev
```

App: http://127.0.0.1:5173/ ; API docs: http://127.0.0.1:8000/docs ;
liveness: http://127.0.0.1:8000/health ; readiness: http://127.0.0.1:8000/ready .

Ports are fixed. Close the existing process if a port is occupied rather than
silently starting a second frontend on another port. Both bind to loopback.
Do not expose the development servers to the public network.

## Configuration

No .env is necessary for defaults. If needed, copy the examples:

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
```

.env files are ignored by Git. Settings resolve backend/.env relative to source,
not whichever shell directory happens to be current.

| Backend variable | Meaning |
| --- | --- |
| DATA_MODE | fixture (default) or postgis. No automatic fallback. |
| DATABASE_URL | Optional complete backend-only PostgreSQL URL; never a frontend variable. |
| DATABASE_HOST / PORT / NAME / USER | Non-secret split connection settings. |
| DATABASE_PASSWORD | Local secret; URL.create handles special characters. |
| DATABASE_SSL_MODE | require (encrypted) or verify-full (identity verified with a trusted CA). |
| CORS_ORIGINS | JSON array of exact frontend origins; localhost and 127.0.0.1 are different. |
| REQUEST_LIMIT_PER_MINUTE | Per-process/IP guard, default 120. External shared limit needed for multiple instances. |

Frontend: VITE_API_URL is public and is the only needed frontend environment
variable. Empty uses Vite's proxy to 127.0.0.1:8000. Production requires the HTTPS
backend origin, without trailing slash. Rebuild after changing VITE variables.

## Testing and builds

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.cache/pytest
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic upgrade head --sql
Set-Location ../frontend
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high
```

The test launcher supplies a project-local .cache/test-temp directory for
Windows sandboxes that cannot write their default temporary directory.
Offline backend tests use test fixtures/mocked providers; live tests opt in below.
Offline migration compilation does not contact a DB.
A Starlette/httpx test-client deprecation warning is currently upstream;
HTTPX remains functional and tests pass. No warning is hidden.

## Switch to Supabase/PostGIS

For the current prepared session-pooler setup and safe transactional runner, see
[docs/DATABASE_INTEGRATION.md](docs/DATABASE_INTEGRATION.md).
The agent will use integrate_db.py --apply --activate after a local password is available.


1. Provision a Supabase project yourself; enable PostGIS with its SQL editor.
   This has not been performed by this project.
2. Use the actual connection values provided by Supabase. URL-encode special
   password characters. Use a direct connection or session pooler for migrations.
3. Set DATABASE_URL in backend/.env. The code forces psycopg3 and SSL. Connection
   and statement timeouts are 5 and 10 seconds. search_path is public,extensions.
4. Deliberately run the migration with a migration owner:
   `backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head`
   from the repository root, or `python -m alembic upgrade head` from backend.
   Run from backend using the venv as shown above for consistent module paths.
5. Provision a separate backend login and grant it the optional
   database/reader-role.sql read group. This script enables read policies for that
   group only; it is not an anonymous access policy. Add extensions schema usage
   if PostGIS is installed there. Never put owner credentials in the browser.
6. Set DATA_MODE=postgis and restart FastAPI.
7. From backend: `.venv/Scripts/python.exe check_db.py`. It checks PostGIS,
   expected migration revision and feature table access without printing secrets.
8. GET /ready must be 200 and report a verified connection. Otherwise queries
   fail with 503. No fixtures are substituted.
9. An empty migrated database returns an honest empty result. Phase 1 does not
   implement ingestion or automatically seed any synthetic features into PostGIS.

The schema stores point/line/polygon geometry in EPSG:4326 with GiST indexes.
Queries combine category membership, name, spatial filters and pagination in SQL.

## Manual browser acceptance

- Load the app: 11 synthetic records, 8 populated categories, 3 geometry types.
- Search Warehouse: 3 unique records; search an unmapped string: honest empty state.
- Select TEST Warehouse Alpha from table or map: provenance and Unknown capacity.
- Disable Warehouses: Alpha stays visible via Logistics hubs; 9/11 remain visible.
- Select another study area: no records if fixture coverage is outside that extent.
- Search `101.455,3.07`: map flies to coordinate (longitude first).
- Draw vertices, Finish: validated sketch and geodesic result; export before reload.
- Switch to Minimal: overlays remain usable without remote basemap.
- Open any later module: explicit unavailable phase, no generated result.
- Stop backend and refresh: error banner appears; existing results, if any, are
  explicitly identified as last successful data.
- Settings > Check readiness: fixture limited status, database_verified=false.

Browser geolocation requires permission and HTTPS or localhost; permission
grant and the user's actual location were not exercised during automated QA.

## Troubleshooting

- npm TLS issuer errors under Windows: Node 24 can use the trusted system CA
  store for that process with `$env:NODE_USE_SYSTEM_CA='1'`. Keep TLS validation on.
- This Codex sandbox had an antivirus-injected SSLKEYLOGFILE pointing at an
  inaccessible device. Python pip worked after omitting that diagnostic variable
  only in the install process, and using a writable workspace temporary directory.
  No OS policies, antivirus controls or certificate validation were changed.
- PowerShell scripts may be restricted: use the direct commands above.
- Blank map: use a WebGL2 browser; otherwise table/query/export still work.
- Remote tiles blocked/offline: choose Minimal. It has no geographic basemap.
- Database unavailable: verify connection host/port, SSL, password escaping,
  migration privileges, extensions search path, network access and reader policies.
- Large MapLibre bundle warning: known; separate worker and renderer files are
  emitted. This is not a production performance certification.


## Phase 2 discovery

The delivered workspace already has PostGIS mode configured. Do not overwrite
backend/.env or paste its contents into chat. Open Real OSM discovery, choose an
initial target or enter a Malaysian location name, submit Find place, explicitly
choose the correct OSM reference, select categories/radius, then Import selected
categories. Alternatively use a bounded box (maximum 400 km²). Inspect the persisted
history and zero/failed category counts before interpreting results.

Discovery adds these backend settings: DISCOVERY_ENABLED (true for the local
workspace), OVERPASS_URL, GEOCODING_URL, OSM_USER_AGENT and PROVIDER_CACHE_DIR.
Defaults and usage limits are documented in docs/API.md. Providers use HTTPS
certificate validation with the OS trust store, not verify=False. Discovery is
local-only; use one server process and do not expose Vite/backend to the network.
The Render template sets DISCOVERY_ENABLED=false.

Initial six-area extraction was explicitly run once with:

    ./.venv/Scripts/python.exe import_study_areas.py --initial-six

Run that command from backend (use ./.venv/Scripts/python.exe there). It geocodes
six names serially and saves reports to docs/phase2-coverage.json; it is not an
automatic seed, startup hook or scheduled task. It refreshes existing source IDs.
Do not run it concurrently with UI imports. No manual import is needed to use
the real data already stored in the delivered Supabase database.

Live database tests remain opt-in and roll back their test rows:

```powershell
Set-Location backend
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
./.venv/Scripts/python.exe -m pytest -q --tb=no --basetemp=.cache/pytest-live
Remove-Item Env:RUN_SUPABASE_INTEGRATION_TESTS
```

Offline provider tests mock public responses; no tests automatically download
industrial data. See docs/PHASE2_ACCEPTANCE.md for executed live extraction,
HTTP/browser checks, source snapshot times and measured coverage.

## Phase 3 routing configuration and checks

backend/.env.example includes ROUTING_ENABLED, ROUTING_PROVIDER=osrm,
ROUTING_BASE_URL=https://routing.openstreetmap.de/routed-car,
ROUTING_OSRM_PROFILE=driving, ROUTING_PROVIDER_LABEL and ROUTING_POLICY_URL.
Defaults work without copying new settings into the existing secret .env.
ROUTING_PROVIDER=disabled or ROUTING_ENABLED=false makes operations unavailable.
OSM_USER_AGENT identifies public-provider requests; no API key is needed for
the bounded local demo. TLS verification stays enabled.

Do not pass a routing endpoint from browser input. Provider URL/profile are trusted
backend configuration. A different OSRM-compatible service can use the adapter;
a different protocol requires a new RoutingProvider implementation and tests.
The current adapter supports car only. No local routing engine is required.

Use one backend process bound to loopback. Routing uses a 20-second provider
timeout and 60-second frontend timeout; Vite gives routing its own longer proxy
timeout and closes upstream connections per request. Public-demo quotas/caches
are per process/machine, not distributed. Do not run load tests against it.

Live regression checks (from backend, password already in ignored .env):

```powershell
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -q --tb=no --basetemp=.cache/pytest-phase3-final --junitxml=../docs/phase3-backend-tests.xml
.\.venv\Scripts\python.exe -m pip check
# API8000 + preview4173 running; only read-only database/runtime verification:
.\.venv\Scripts\python.exe verify_phase3_final.py
# Optional scenario verification: calls geocoder/router (cached when fresh)
# and saves actual routes idempotently to Supabase:
.\.venv\Scripts\python.exe verify_phase3.py
```

Preview a new production build (from frontend):

```powershell
npm.cmd run build
npm.cmd run preview -- --port 4173 --strictPort
```

Open /#routing. Select exact place results or Imported GIS features, add/reorder
stops, calculate and inspect snapping. Export selected/all alternatives or save.
Save accepts the server calculation ID and route index; no client geometry.
Rows are in public.routing_references. Phase 4 Saved Route History now opens/compares/exports these persisted records.
Completed drawing sketches survive switching modules; reload clears memory-only
plans/sketches, so export/save important work. See docs/PHASE3_ACCEPTANCE.md.

## Phase 4 analytics

ANALYTICS_ENABLED=true is the local default; public deployment template sets it
false. Existing backend/.env is retained. No dependency or schema migration added.
Use one local backend process. Analysis/history APIs enforce local Host/Origin,
PostGIS mode and strict schemas. Production authentication remains future work.

Workflow: /#toolbox → operation → Input A/B → apply bbox/radius/categories →
preview/select multiple IDs (or choose completed sketch/saved layer) → parameters →
Run. Query sources are applied explicitly. Save results to use them as saved-layer
inputs. Results keep input/source metadata, exact parameters, CRS, timestamp,
warnings and statistics. Max five in-memory map layers; reload saved data from DB.

Cluster module: choose DBSCAN or grid, bounded study query, epsilon/min points or
grid meters. Grid includes one representative point per mapped feature; heatmap
is a zoom-dependent visualization. Category memberships can overlap. Regional
comparison uses first reported place match, or Name|lon,lat per line for exact
references. Inspect resolved inputs; do not assume gates.

Network module: add up to five origins and five destinations via names, coordinates,
map clicks or imported facilities. Calculate a real OSRM matrix; inspect the
fastest supplied destination and explicit score formula. Inspect pair in road
planner transfers exact references to Phase 3; calculate there for road geometry.
Isochrone controls explain unsupported capability rather than producing circles.

Saved analyses/routes: 25 history entries/page. Open multiple routes for map and
numeric comparison. Confirmed deletion adds archived_at, preserving row geometry.
Undo last deletion calls restore. Save again also restores the same calculation.
Browser memory resets on reload; export/save work that must persist.

Additional checks, from backend with API8000 + frontend4173 running:

```powershell
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -q --tb=no --basetemp=.cache/pytest-phase4-final2 --junitxml=../docs/phase4-backend-tests.xml
.\.venv\Scripts\python.exe verify_phase4.py
.\.venv\Scripts\python.exe verify_phase4_regions.py
.\.venv\Scripts\python.exe verify_phase4_final.py
```

verify_phase4.py runs bounded real queries and saves an actual clip result;
live DB integration tests archive/restore within rollback. Final verifier only
reads DB and validates API/export/secret safeguards (compute endpoints may cache).
No OSM feature or existing route is deleted. See docs/PHASE4_ACCEPTANCE.md.


## Phase 5 logistics optimization

Open #optimization from the navigation. Backend must be in live PostGIS mode.
OPTIMIZATION_ENABLED=true, ANALYTICS_ENABLED=true and ROUTING_ENABLED=true
are required locally. The Render template disables all costly local workflows.

1. Add an imported GIS warehouse or exact reference as depot. Review its representative
   coordinates; they are not verified gates. Add up to four depots.
2. Configure up to six vehicles. Capacity is one user-defined integer unit shared with
   all stop demands. Set start/end depots, operating windows, distance and working limits.
   First-depot vehicle defaults (capacity 10, zero prices) are explicitly editable assumptions.
3. Add up to 20 candidate stops. Demands are hypothetical by default. Set service duration,
   mandatory flag, priority and service-start window. Every pickup must have exactly one
   equal-demand paired delivery, with the same mandatory flag.
4. Save a snapshot, or Optimize routes to save then queue one bounded job. Edits create a
   new snapshot and invalidate the old UI result. Saved original snapshots are preserved.
5. Inspect solver status, unassigned stops, matrix metrics, final OSRM geometry/timing
   checks, cost assumptions and warnings. Compare 2–4 solved saved scenarios.
6. GeoJSON/CSV/print reports retain provider, demand context and limitations.
   Archive/restore use confirmation and retain original records.

Units: metres and seconds in APIs; MYR costs; seconds 0–86400 from scenario day start.
Windows constrain service start; return-to-depot must fit operating hours and working
duration. Driver cost includes waiting/service time. Distance operating cost, fixed
used-vehicle cost, optional explicit fuel and driver costs are additive; avoid double
counting. No toll tariffs, diesel price or actual vehicle specifications are supplied.

OR-Tools 9.15 uses parallel cheapest insertion plus guided local search, bounded to 1–20
seconds (default 3). CVRP includes depot-loaded deliveries and paired pickups with signed
on-board load. Multi-depot starts/ends are supported. Empty vehicles are not repositioned.
Optional service priority penalties dominate the selected objective; mandatory stops
cannot be dropped. Objectives: matrix distance, driving time, supplied cost, vehicle-count
then distance, or total distance + 20 × longest route. Cost model uses integer 0.0001-MYR
arc costs and rounded per-second driver rates. Reported estimates use full input precision.
Status success means a feasible best solution, not globally optimal. Only solver status
ROUTING_OPTIMAL establishes the rounded model's optimality; not real-world global optimality.

OSRM table returns asymmetric fastest-path distances and durations. Up to 16 nodes use
one table request; 17–24 nodes use up to nine 8×8 blocks. Cache is 24 hours, max 64
matrices; provider guard remains 12 upstream requests/minute and 1.1-second spacing.
Large requests can hit the quota; failures are explicit. No Euclidean/fallback-speed
matrix is accepted. Final route geometry uses chunks of at most eight references,
overlapping one waypoint; missing geometry remains null and is not drawn as a line.
Via-point turn continuity can change final routed distance/time compared with table
sums. Final road timing/distance limits and recalculated costs are reported separately.
A failed final check requires replanning; the matrix solution is not dispatch approval.

One process-local worker, one active job, bounded API input (1.5 MB), no automatic
unbounded retries. Cancellation is cooperative between calls and after the bounded
solver; it cannot interrupt an in-flight OSRM call. Backend restarts mark unfinished
jobs interrupted. Run a single Uvicorn worker. This is a local development job runner,
not a distributed durable production queue.

CSV import required headers: longitude,latitude,demand. Optional:
id,name,service_s,window_start_s,window_end_s,priority,mandatory,kind,pickup_id,source_id.
GeoJSON requires a FeatureCollection of 2D EPSG:4326 Points with properties.demand.
Maximum file size 1 MB and 20 records; imports never access server filesystem paths.
Loaded Saved Analyses point results can be reused; non-point analyses must be converted
to an explicit reference through a GIS facility selection or an exact map coordinate.

Migration 0002_logistics is additive and reviewed. Existing foundation vehicles/shipments
remain unchanged because their feature-only foreign keys cannot represent user-coordinate
depots/stops. New normalized logistics_* tables support both. Downgrade is blocked to
preserve records. Verify current integrity with:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe verify_phase5_db.py
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp=.cache/pytest-phase5
Set-Location ../frontend
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

Live scenario scripts are opt-in: backend/verify_phase5_live.py A, B, C, D2, D3, D4,
E, F and compare. Run serially, review provider quota, and reuse cache; each creates a
clearly labelled hypothetical-demand snapshot. Do not run them as a public load test.
Acceptance evidence and precise limits are in PHASE5_ACCEPTANCE.md.


## Fresh Phase 5 acceptance review (24 October 2026)

This review preserves all historical rows and does not run migrations. The recorded
final suites are 193 backend tests (10 live PostGIS) and 60 frontend tests. See
PHASE5_ACCEPTANCE.md and docs/PHASE5_REVIEW.md; browser acceptance is blocked by the
current Work local-browser setting, so Phase 5 is not fully accepted.

Commands actually executed (backend/frontend respective directories):

```powershell
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests --basetemp=.cache/pytest-review5-final-cost -q --junitxml=../docs/phase5-review-backend-final.xml
.\.venv\Scripts\python.exe -m pip check
npm.cmd test -- --reporter=json --outputFile=../docs/phase5-review-frontend-final.json
npm.cmd run typecheck
npm.cmd run build
```

Review helpers: backend/review_phase5_integrity.py is read-only against the database
and compares historical row checksums; review_phase5_final_source.py reads saved
review payloads and re-solves them without overwriting results. Both use local .env
without printing it. review_phase5_live.py adds explicitly labelled hypothetical
review scenarios/jobs/results and one comparison; it is an opt-in acceptance run,
not a routine benchmark. It respects existing provider quotas and caches. Headless
exports exercise the actual frontend functions; they are not browser download tests.


## Phase 5 remaining-work completion (24 October 2026)

Fresh final tests: 198 backend (12 live DB), 70 frontend (14 files).
The comparison features are complete; real browser access remains disabled.
Use docs/PHASE5_BROWSER_ACCEPTANCE.md for manual sign-off; component/style/headless
export tests do not count as browser verification. No migration command is needed.

Commands actually executed in their respective backend/frontend folders:

```powershell
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests --basetemp=.cache/pytest-phase5-completion -q --junitxml=../docs/phase5-completion-backend.xml
npm.cmd test -- --reporter=json --outputFile=../docs/phase5-completion-frontend.json
npm.cmd run typecheck
npm.cmd run build
```

backend/verify_phase5_comparison_completion.py is opt-in: it adds one named comparison
from existing solved scenarios, reopens legacy snapshots and checks all historical row
fingerprints. It does not solve new routes, migrate, overwrite or reset database records.
Its baseline must be captured separately before use. Existing live pytest additions are
rollback-only; no synthetic test record is committed.


## Phase6 verification

Root reports: PHASE6_ACCEPTANCE.md / PHASE6_REVIEW.md. New source modules under
backend/app/sites and frontend/src/features/SiteSelection.tsx. No new runtime dependency
was needed; NumPy/Shapely/SQLAlchemy and existing routing stack were already installed.

Fresh final commands, respective backend/frontend directories:

```powershell
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests --basetemp=.cache/pytest-phase6-final -q --junitxml=../docs/phase6-backend.xml
npm.cmd test -- --reporter=json --outputFile=../docs/phase6-frontend.json
npm.cmd run typecheck
npm.cmd run build
```

The reviewed additive0003 SQL is docs/phase6-migration.sql. It was applied once using
app.db.migrate.migrate_safely, with advisory lock/transaction/full verification. Do not reset
or rerun destructive migrations. Future current databases are detected as already current.
verify_phase6_live.py is opt-in and adds three named site evaluations from existing OSM data,
using a bounded OSRM matrix; verify_phase6_gis.py performs read-only Phase4 API operations;
verify_phase6_integrity.py compares the pre-captured baseline and current schema/data.
Manual browser checklist: docs/PHASE6_BROWSER_ACCEPTANCE.md. Phase5 browser remains pending.


## Phase 7 verification and startup (Windows, no Docker)

Use the same backend virtual environment and React project. No new dependency installed.
The existing .env remains unchanged. Optional LLM fields are documented in .env.example;
no provider key is required or assumed. Keep keys backend-only and never use VITE_ secrets.

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
# Separate terminal, repository/frontend:
npm.cmd run dev
# Or production preview, after build:
npm.cmd run preview -- --host 127.0.0.1 --port 4173
```

Open http://127.0.0.1:4173/#geoai (or5173/#geoai). Vite GeoAI proxy and client
allow bounded long operations; cancellation is cooperative. Do not publish these local
analytics/optimization/GeoAI routes without actual authentication/shared quotas.

```powershell
# Backend, explicitly live PostGIS tests; temporary test rows are rolled back.
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp=.cache/pytest-phase7-release --junitxml=../docs/phase7-backend.xml
.\.venv\Scripts\python.exe -m pip check
# Frontend:
npm.cmd run typecheck
npm.cmd test -- --run --reporter=json --outputFile=../docs/phase7-frontend.json
npm.cmd run build
```

`backend/verify_phase7_live.py` calls the actual running HTTP API/OSRM and explicitly
confirms bounded in-memory test optimization and new GeoAI snapshot saving. It writes
new GeoAI audit/snapshot records only; it preserves all old Phase1–6 records.
Use it deliberately, not as a production monitor. Provider caches may be reused and
returned cached/retrieved_at metadata is retained. HTTP invocation freshness is not
a claim that every route was fetched anew upstream.
`verify_phase7_integrity.py` compares every original24-table row fingerprint, checks
SSL/PostGIS/migration, unchanged .env and frontend/backend runtime. No migration is
needed for browser checklist. Migration0004 SQL and committed verification evidence
are in docs/phase7-migration*. Database already upgraded; do not reset/stamp/reapply DDL.
