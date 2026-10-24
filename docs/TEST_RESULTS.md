# Executed validation — Phase 4 (current)

2026-10-24, Windows x64; live Supabase/PostGIS, API8000, production preview4173.

| Check | Result |
| --- | --- |
| Backend pytest | 138 passed, 0 failed/skipped; 9 live DB tests |
| Frontend Vitest | 42 passed, 0 failed/skipped; 10 files |
| TypeScript | Passed |
| Vite production build | Passed |
| pip check | No broken requirements |
| Live scenarios A–I | 9 passed |
| Isochrone scenario J | Unsupported / HTTP501; not passed |
| Extra live GIS operations | 7 passed |
| Six regional query references | API + browser/export/save/reload passed |
| Existing OSM/Phase3 data | 5,234 real features + 8 exact route snapshots preserved |
| Save/reload/archive/restore | Live DB rollback tests passed |
| Real browser | Buffer/multisource/export/save/reload/routes/matrix/cluster/grid/heatmap/layers/select |
| Browser exports | 71 valid geometries, 70 CSV match rows, EPSG4326 |
| Empty/invalid/large/provider failure safeguards | Passed |
| API/proxy/DB/index/RLS/secret checks | phase4-database-verification.json + phase4-secret-scan.json |

Nonfatal warnings: Starlette/httpx test-client deprecation and large MapLibre
chunk. No cloud deployment or verified heavy-vehicle certification claimed.
Browser checks are manual real UI verification, not an automated E2E suite.

Reports: phase4-backend-tests.xml, phase4-frontend-tests.json,
phase4-scenarios.json, phase4-region-comparison.geojson,
phase4-database-verification.json, phase4-browser-checks.json,
phase4-secret-scan.json. Full methods/limitations: PHASE4_ACCEPTANCE.md.
Images: phase4-clusters.png, phase4-grid.png, phase4-heatmap.png, phase4-network.png.

---

# Historical validation — Phase 3

2026-10-24, Windows x64, local API/production preview + live Supabase.
Phase 4 not started. Historical results follow below.

| Check | Final result |
| --- | --- |
| Backend pytest | 111 passed, 0 failed/skipped (7 live DB) |
| Frontend Vitest | 31 passed, 0 failed/skipped, 7 files |
| TypeScript | Passed |
| Vite production build | Passed |
| Python pip check | No broken requirements |
| Real OSRM scenarios | 7/7 passed |
| Saved PostGIS routes | 8/8 valid LineString EPSG:4326, positive metrics/provenance |
| Existing OSM records | 5,234 unchanged, 0 synthetic/invalid |
| SSL/schema/index/RLS | Verified; existing migration 0001_foundation |
| API and preview health/ready/provider | 6/6 HTTP 200 |
| Real browser checks | Place/map/GIS/multi-stop/alternatives/export/save/basemap passed |
| Final browser console | No new errors/warnings after final-build reload |
| Secret scan | No matches outside .env; ignored/untracked |

Reports: phase3-backend-tests.xml, phase3-frontend-tests.json,
phase3-routing-scenarios.json, phase3-database-verification.json,
phase3-browser-checks.json, phase3-secret-scan.json.
Full scope/method/limitations: [Phase 3 acceptance](PHASE3_ACCEPTANCE.md).
Screenshots: phase3-preview.png, phase3-route-comparison.png,
phase3-multistop-map.png and phase3-multistop-summary.png.

Warnings: upstream Starlette/httpx test-client deprecation; large MapLibre chunk.
Standard-car planning references only; no heavy-vehicle or production certification.
No public hosting smoke test is claimed.

---

# Historical validation — Phase 1

2026-10-24, Windows x64. See PROGRESS.md for commands and fixes.

| Check | Final result |
| --- | --- |
| Backend pytest | 37 passed, 0 failed |
| Frontend Vitest | 13 passed, 0 failed |
| TypeScript + Vite production build | Passed |
| Python dependency consistency | No broken requirements |
| npm production dependency audit | 0 reported vulnerabilities |
| Offline Alembic SQL | Compiled; 12 tables, spatial indexes, RLS |
| Local API/frontend HTTP | 200 |
| DB connection diagnostic without credentials | Expected failure; not verified |
| Local compiled browser preview | Tiles, overlays and feature inspector verified |
| API outage/recovery browser check | Error displayed, retained data labeled, retry recovered |

Machine-readable reports: pytest-results.xml and vitest-results.json.
Contract snapshot: openapi.json. Compiled SQL: ../database/phase1-schema.sql.
Proof image: phase1-preview.png.

Nonfatal warnings: one upstream Starlette/HTTPX test-client deprecation;
MapLibre renderer exceeds Vite's default 500 kB chunk warning threshold.

These checks do not certify live PostGIS, cloud deployment, real industrial data,
geolocation permission, routing, optimization, GeoAI or production readiness.
