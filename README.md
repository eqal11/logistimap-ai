# LogistiMap AI

**Intelligent Industrial & Logistics Geospatial Intelligence**

A Docker-free React/TypeScript/MapLibre + FastAPI/PostGIS GIS for Malaysia.
**Phases 1–7 implemented for bounded local use. Phase7 adds a bilingual deterministic GIS Copilot and optional backend-only LLM tool planner. Fresh verification:288 backend /89 frontend passed. Phase5, Phase6 and Phase7 browser acceptance remain pending. Phase8 not started.**

## Working now

- GeoAI Copilot: Bahasa Melayu/English GIS commands,23 allowlisted tools, actual PostGIS/OSRM
  results, multi-intent/multi-turn map context, MCDA/OR-Tools integration, preview/confirm and
  saved conversations/exports. Default deterministic mode is not LLM intelligence; no LLM key
  configured or required. [Phase7 acceptance](PHASE7_ACCEPTANCE.md) ·
  [Review](docs/PHASE7_REVIEW.md) · [Pending browser checklist](docs/PHASE7_BROWSER_ACCEPTANCE.md).

- Warehouse Site Selection: mapped/hypothetical candidates, WLC/AHP/CR, real PostGIS/OSRM
  criteria, transparent sensitivity, thematic map, persistence/import/export.
  [Phase6 acceptance](PHASE6_ACCEPTANCE.md) · [Engineering review](PHASE6_REVIEW.md).

- OR-Tools logistics optimization with real OSRM matrices/geometries, capacity,
  pickup–delivery, hard windows, multi-depot fleet, saved scenarios, comparison
  and attributed exports. [Phase 5 acceptance](PHASE5_ACCEPTANCE.md).

- Advanced spatial toolbox: real buffer/intersection/clip/union/difference/
  dissolve/spatial joins/area aggregation/geographic nearest on bounded inputs.
- Industrial DBSCAN, density grids/heatmaps, regional concentration comparison.
- OSRM road travel matrices, supplied-candidate nearest and transparent time score.
- Layered analysis results, GeoJSON/attributed CSV, PostGIS save/reload/history,
  confirmed reversible deletion/undo and saved Phase 3 route comparison.
  [Phase 4 acceptance and actual scenario results](docs/PHASE4_ACCEPTANCE.md).


- Real road-network planner: place names, map clicks and imported GIS references;
  up to eight ordered stops, provider distance/time, alternatives, highlighted
  routes and markers, GeoJSON exports and optional PostGIS save.
- OSRM-compatible routing abstraction, validated geometry/metrics, bounded local
  cache/timeouts/quotas and explicit standard-car limitations.
  [Phase 3 acceptance and actual scenario results](docs/PHASE3_ACCEPTANCE.md).

- Real OpenStreetMap/Overpass discovery across eight overlapping categories:
  industrial facilities, industrial land use / parks, warehouses, logistics hubs,
  ports, airports, major roads and rail infrastructure.
- Explicit place-name lookup in Malaysia, radius or bounded-box discovery,
  category selection, background imports, persisted job history and coverage reports.
- Transactional imports into the existing Supabase PostGIS schema. Canonical OSM
  IDs deduplicate overlapping areas; newer source versions are protected.
- Actual PostGIS bbox intersection, geography distance queries, name search and
  category counts. No synthetic fallback in PostGIS mode.
- Map points, lines, polygons and multipolygons; selection, highlighting, layer
  order/visibility, complete active legends and source attributes.
- Map and query export load every result up to an explicit 10,000-object safety
  cap. The attribute table independently pages through 250 records at a time.
- Existing drawing, geodesic measurements, basemaps, coordinate fly-to, responsive
  layouts, themes and backend diagnostics remain available.

Initial import: **5,234 unique real OSM objects**, including a supplemental
airport query. Full per-area and per-category results, methods, tests and
limitations: [Phase 2 report](docs/PHASE2_ACCEPTANCE.md).
Database verification: [phase2-database-verification.json](docs/phase2-database-verification.json).
Progress: [PROGRESS.md](PROGRESS.md).

## Start on Windows

Dependencies are installed in this workspace. From this repository, use two
PowerShell terminals:

```powershell
# Terminal 1
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

```powershell
# Terminal 2
Set-Location frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173/ and http://127.0.0.1:8000/docs.
The existing production preview is at http://127.0.0.1:4173/.
Backend credentials stay in the ignored backend/.env; never copy them into chat
or VITE variables. No Docker, local PostgreSQL, routing engine or AI key is needed.

Fresh checkout and tests: [DEVELOPMENT.md](DEVELOPMENT.md).
API: [docs/API.md](docs/API.md). Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Future hosting: [DEPLOYMENT.md](DEPLOYMENT.md).

## Data meaning and provider limits

**© OpenStreetMap contributors, ODbL 1.0.**
[License and attribution](https://www.openstreetmap.org/copyright).
Basemap data and ingested feature records are separate.

Counts are OSM objects, not verified facility totals. Industrial land-use shapes
are not authoritative industrial park boundaries, zoning or developability.
Airport mapping does not establish cargo capability. Road/rail source lines are
not computed routes. Unknown capacity, rent and available space remain unknown.
Distinct OSM ways and relations can overlap; spatial overlap alone is not grounds
to delete a source object. OSM deletions are not automatically reconciled.

Discovery is restricted to the local workspace. One import at a time, bounded
areas, resource/response limits, 24-hour Overpass caching and cooldowns protect
public providers. Place search uses explicit submits, no autocomplete, a
7-day cache and at most one request per 1.1 seconds.
Read the [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/)
and [Overpass resource guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html).
Public deployment needs authentication, shared quotas and a suitable provider;
the Render template disables discovery, routing, analytics and optimization. Nothing has been publicly deployed.

Network isochrones, site selection, GeoAI and general spatial-file ingestion
(Shapefile/GeoPackage) remain unavailable. Phase 5 supports validated logistics
CSV and point GeoJSON imports. Fixture mode is retained only
as explicitly synthetic Phase 1 test functionality; it is never used for live discovery.

## Road route planning

Open [Freight Route Planner](http://127.0.0.1:4173/#routing). Choose the exact
place match, a coordinate reference, map point or real Imported GIS feature for
each stop. Calculate, inspect snaps/legs, select an alternative, export or save
to PostGIS. Inspector buttons also set a selected feature as origin/destination.

Default provider: [FOSSGIS OSRM public demo](https://routing.openstreetmap.de/about.html),
standard car only; no verified truck restrictions or live traffic. Local-only,
24-hour cache, minimum 1.1 s spacing, at most 12 upstream requests/minute.
Results are planning references; town/representative points are not verified
facility gates. Saved LineStrings and provenance use routing_references; the
browser plan is memory-only across modules and resets on reload.

Latest checks: **138 backend (9 live DB), 42 frontend**, TypeScript and production
build passed; **A–I spatial scenarios and seven extra operations passed**.
Network isochrone scenario J is unsupported, not passed. Details and limitations are
in the Phase 3 report. No production deployment is claimed.


## Advanced GIS workspace

Open [Spatial Analysis Toolbox](http://127.0.0.1:4173/#toolbox),
[Industrial Clusters](http://127.0.0.1:4173/#clusters),
[Network Accessibility](http://127.0.0.1:4173/#accessibility),
[Industrial Accessibility](http://127.0.0.1:4173/#industrial-accessibility),
[Saved Analyses](http://127.0.0.1:4173/#saved-analyses) or
[Saved Route History](http://127.0.0.1:4173/#route-history).

Apply bounded category queries, select multiple preview IDs, choose a completed
map sketch, or reuse a saved analysis layer. Run, inspect inputs/method/warnings,
hide/zoom/select result layers, export or save. Reload persisted results from
history. Delete asks for confirmation and archives without erasing geometry;
Undo restores the last archive. No schema migration was required.

Local metric projection is limited to 250 km from its center. Queries over 2,000
objects fail clearly. Grid/hulls/buffers are mathematical references, not verified
boundaries or network service areas. OSM counts are mapped objects, not economic
activity or a physical-facility census. Network matrices use car travel on the
fastest routes; distance is not necessarily shortest-distance. Isochrones remain
unsupported because no compatible provider/validated graph is configured.


### Phase 5 — logistics optimization
The existing workspace now includes a bounded OR-Tools scenario builder, fleet/delivery
constraints, real OSRM matrices/vehicle geometries, saved scenarios, comparison and exports.
Use Logistics Optimization in navigation. Demands default to hypothetical; car routing
does not verify truck restrictions. See [Phase 5 acceptance](PHASE5_ACCEPTANCE.md),
[development workflow](DEVELOPMENT.md) and [API contracts](docs/API.md).
