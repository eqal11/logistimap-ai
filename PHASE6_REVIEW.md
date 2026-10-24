# Phase 6 — Engineering and acceptance review

24 Oktober 2026. Development scope implemented; automated/API/PostGIS checks pass.
**Browser verification unavailable. Phase 5 browser acceptance stays pending. Phase 7 not started.**

## Requirement coverage

| Requirement | Implementation and evidence |
| --- | --- |
| Existing facilities / mapped industrial land use | Existing Phase2 GeoJSON API, multi-category/radius/bbox/name/pagination; server re-resolves feature UUID and original geometry/category/source |
| User points/polygons | Map clicks, existing Phase1 drawing → Finish → Add drawn candidates, CSV/GeoJSON import; hypothetical/reported-existing labels, not verified sites |
| WLC | Nonnegative normalized weights, observed min/max, explicit benefit/cost; known-answer tests |
| AHP | Reciprocal 1/9–9 pairwise editor, principal eigenvector, λmax/CI/RI/CR, inconsistent override; consistent/inconsistent/invalid unit tests |
| Missing data | Reject default; explicit global criterion or candidate exclusion, disclosed renormalization, no imputation |
| Criteria availability | GIS/network/user distinctions; official hazard/cost/environment/infrastructure/zoning unavailable unless user supplies unverified numeric values and note |
| Geometry and CRS | Point/Polygon/MultiPolygon only, EPSG4326 validation, Malaysia extent/complexity bounds; geodesic area and PostGIS geography distances |
| Real road data | Existing OSRM Table provider abstraction/cache/quotas;14×14 actual matrix, no unreachable pairs or fallback speeds |
| GIS integration | Actual Phase4 buffer/intersection/spatial join/nearest/DBSCAN/grid calls; six live API cases passed |
| Candidate thematic map | Score fill/circle colours, rank labels, selection via original candidate ID, markers on PostGIS anchors, visibility/fit; installed MapLibre spec tested |
| Contributions/comparison | Original values/source/method/unit, normalized values, weights, contributions and ranked tables; chart per selected candidate |
| Sensitivity | One weight ×1±delta then renormalize; exact reranking runs and min/max rank/score charts; deterministic tests and real changes |
| Save/reload | Immutable scenarios/evaluations, normalized candidate and criterion-value child rows, repeated save, paginated history, exact roundtrip |
| Export | GeoJSON preserves original geometry plus evaluation metadata; CSV includes values, definitions, directions, ranges, weights/AHP/missing policy/provenance/sensitivity |
| Phase1–5 preservation | Full regression suites, runtime histories/queries and all original20-table row fingerprints unchanged |
| Browser QA | Not passed/observed; manual S01–S19 checklist delivered |

AHP here derives criterion weights, followed by numeric WLC alternative scoring. It does not elicit
pairwise judgments between every pair of alternative sites. CR is a consistency guideline,
not proof that preferences or underlying source data are correct.

## Dataset interpretation

OSM/source footprints are community-mapped industrial/warehouse references, never availability,
ownership, vacancy, price or regulatory permission. Named study areas are search references only;
AHTV has no fabricated park boundary. The12-candidate cohort is a purposive sample around six
reference points, not an exhaustive study. Industrial count/density describe imported objects,
not actual economic output or forecast demand. Count and density at a fixed radius correlate;
users must avoid unintentional double weighting.

Road criterion validation selected **Port Klang town** and **Subang Airport**, not verified cargo/port gates.
OSRM driving time is seconds on standard-car fastest paths, not truck time/traffic/tolls.
The full provider matrix/snaps and retrieval metadata remain in the saved evaluation JSON.
Nearest road/warehouse/hub is geography footprint separation ≤100km, not network access.
GIS preview tools use fixed5km, ε1000m/min3 and grid1000m; MCDA radius is separately configurable.

Official flood, environment, utilities, land cost and zoning datasets are not configured.
User-supplied values are unverified, note-required and retain source/status. Point parcel area
is unavailable; polygon area describes the mapped footprint, not a surveyed cadastral parcel.

## Fresh quality gates

- **230 backend passed**,0 failed/skipped;14 live PostGIS,66.66s.
- **79 frontend passed**,0 failed/pending;16 files.
- TypeScript/production build/pip check passed. MapLibre style expressions validated.
- Real cohort:12 candidates/6 areas; one fresh OSRM request,196 pairs; WLC repeatability
  and equivalent AHP ranking parity passed, CR0.
- Three DB snapshots saved/reloaded; geometry/ranking/parameters/sensitivity exact.
- GeoJSON12 candidate geometries unchanged; CSV12 rows; display-only anchors create24 map features.
- Source-specific criterion units, normalized contributions and sensitivity runs remain reproducible.
- CSV2 point/GeoJSON1 polygon HTTP imports passed without DB writes.
- Live Phase4 API: buffer1,intersection1,join2,nearest1,clusters83,grid103 output features.
  These counts include the actual algorithm output structure; not all are cluster counts.
- Browser tool explicitly disabled; **0 real browser checks passed**. No old screenshot reused.

## Errors found and fixed

- PostGIS geometry_columns inferred a generic candidate geometry as POINT from the initial
  GeometryType IN check. The migration transaction rolled back, then the explicit type
  allow-list check was rewritten with array_position. The committed column is GEOMETRY4326,
  accepting point/polygon/multipart as intended; GiST/RLS verified.
- A stale test expected Phase6 to remain unavailable; it now tests the still-unavailable Phase7 module.
- TypeScript test nullability/import issues were fixed before final build.
- Pending map picks are cancelled on requests/tab changes; criterion removal prunes hidden
  user values; editing inputs invalidates old scores; no note-only zero-value insertion.

## Database and operational limits

Revision0003 additive: site_scenarios,site_candidates,site_evaluations,site_criterion_values.
24 tables/RLS,8 geometry/GiST; original20 tables unchanged, .env unchanged.
No destructive migration, reset, data replacement, public deployment, Docker or paid service.
The application binds to local loopback and reuses existing analytics guards.

Bounded12 candidates,8 criteria,25,000 combined vertices,1MB import,1.5MB POST,4MB result,
20s spatial statement timeout; cache24h/32 evaluations. Saved snapshots do not auto-refresh
when OSM/provider data later changes. Actual road table size≤15 nodes for these limits.
Production auth/durable background processing/provider capacity is outside this local delivery.

Remaining verification: actual browser/GPU/font/layout/download and keyboard/narrow/theme interactions
must be checked with docs/PHASE6_BROWSER_ACCEPTANCE.md. No continuous raster pipeline, authoritative
land feasibility, split legal parcel evaluation, flood modelling or verified truck analysis is advertised.
**Phase6 code ready for review; full visual acceptance pending. Phase7 readiness is conditional on sign-off.**

## Files and evidence

Backend: app/schemas/sites.py; app/sites/{catalog,mcda,service,imports,repository}.py;
app/models/sites.py; app/api/sites.py; alembic/versions/0003_site_selection.py;
safe migration/schema/body-limit integration; tests/test_sites.py and live tests.

Frontend: features/SiteSelection.tsx; services/sites.ts; site-areas.json from prior geocoding evidence;
MapWorkspace site layers; App/Sidebar/CSS; site unit/component/map tests.

See PHASE6_ACCEPTANCE.md, docs/phase6-*.json/XML/SQL/GeoJSON/CSV,
docs/openapi.json, docs/PHASE6_BROWSER_ACCEPTANCE.md and PROGRESS.md.
Method reference: [Saaty2008 publisher record](https://www.inderscience.com/info/inarticle.php?artid=17590).
