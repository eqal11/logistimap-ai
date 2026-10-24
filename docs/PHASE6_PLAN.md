# Phase 6 execution plan

1. Inspect/reuse existing GIS/routing/map architecture; capture fingerprints of all 20 existing tables. Done.
2. Implement bounded WLC/AHP/CR, missing-value policies and reproducible weight sensitivity; unit tests.
3. Derive real criteria with PostGIS and existing OSRM matrix service; validated CSV/GeoJSON candidates.
4. Add immutable site scenarios/candidates/evaluations/criterion values via additive 0003 migration. Review offline SQL before applying, verify indexes/RLS and historical fingerprints.
5. Build candidate/criteria/AHP/ranking/sensitivity/history workspace and thematic MapLibre overlays; integrate Phase 4 tools.
6. Run full regressions, real-data six-area comparisons, database save/reload, exports and browser checks where available; otherwise manual checklist.
7. Update acceptance/review/progress/API docs. Keep Phase 5 browser pending; stop before Phase 7.
