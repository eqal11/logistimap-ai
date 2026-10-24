# Phase 6 — Warehouse Site Selection & MCDA acceptance

24 Oktober 2026. **Development/API/automated checks siap; visual browser sign-off pending.**
Phase 5 browser acceptance kekal pending. Phase 7 tidak dimulakan.

## Modul yang dilaksanakan

- Candidate management: mapped industrial/land-use/warehouse references, custom points/polygons,
  map clicks/drawing, validated GeoJSON/CSV import, duplicate/size/CRS checks dan source tracking.
- WLC; AHP principal eigenvector criterion weights, pairwise reciprocal judgments, CI/CR,
  normalized nonnegative weights, explicit cost/benefit directions dan hard CR guideline override.
- Min/max normalized candidate scores, tied ranks, criterion contributions, raw evidence,
  comparison charts/table dan one-weight-at-a-time sensitivity ± configured fraction.
- MapLibre score polygons/markers, rank labels, legend, selection, visibility, fit dan export.
  Candidate-based suitability sahaja; tiada continuous raster palsu.
- Actual Phase 4 buffer/intersection/spatial join/nearest/DBSCAN/grid integration, berasingan daripada score layers.
- Immutable PostGIS saved scenarios/candidates/criterion values/evaluations/AHP/weights/sensitivity,
  paginated history dan exact reload; GeoJSON dan attributed reproducible CSV.

## Data dan kriteria

Sumber sebenar: 5,234 imported OpenStreetMap objects, source IDs/ODbL provenance,
PostGIS geography calculations dan configured OSRM standard-car Table provider.
Enam town/search references diambil daripada Phase 2 geocoding evidence; bukan park boundaries.

Calculated GIS: nearest mapped major-road/other-warehouse/hub footprint separation (≤100km),
industrial object count/density pada anchor radius 100–25,000m, mapped park/industrial overlap,
dan polygon footprint area. Point area unknown, bukan sifar. Overlap bukan zoning approval.
Count/density pada radius sama berkait kuat; menggunakan kedua-duanya memberi extra emphasis
kepada concentration. Tiada economic-demand claim.

Network: road driving seconds to selected port/airport/network reference; actual asymmetric OSRM matrix.
No fallback speed/Euclidean travel times; no traffic/toll/truck guarantees. Anchors bukan verified entrances.

**Unavailable official datasets:** flood, infrastructure/utility availability, environmental restrictions,
land cost/availability dan statutory zoning. Kriteria ini hanya boleh menggunakan explicit unverified
user values dengan provenance/assumption note; tidak dilabel sebagai hasil GIS rasmi.

## Formula dan interpretasi

WLC score = 100 × Σ(weight × normalized value). Benefit=(x-min)/(max-min);
cost=(max-x)/(max-min); constant criterion=0.5. Normalization bergantung kepada set calon.
Missing policy default reject; optional global criterion exclusion/candidate exclusion dinyatakan,
weights kemudian renormalized; tiada zero fill atau imputation.
AHP supplies criterion weights, kemudian alternatif dinilai dengan WLC; bukan alternative-pairwise AHP.
Saaty RI n1–8; CI=(λmax-n)/(n-1), CR=CI/RI untuk n≥3, CR=0 bagi n≤2.
CR>0.10 ditolak kecuali explicit override; low CR bukan bukti prioriti perniagaan benar.
Sensitivity darab satu weight dengan 1±delta, renormalize semua weights dan rerank data yang sama.

## Fresh verification

| Semakan | Hasil baharu |
| --- | --- |
| Backend penuh | **230 passed, 0 failed, 0 skipped**, 14 live PostGIS tests; 66.66s |
| Frontend penuh | **79 passed, 0 failed, 0 pending**, 16 fail |
| TypeScript / production build | Lulus / lulus |
| pip check | Tiada broken requirements |
| MapLibre styles | Installed style-spec validator + point/polygon selection/hide tests lulus |
| GIS/WLC real cohort | 12 unique OSM candidates, dua setiap enam focus references; valid polygon geometry |
| Road matrix | **14 nodes / 196 pairs, zero unreachable**, one fresh upstream request, 2026-10-24 12:41:46 UTC |
| AHP | λmax=5, CI=0, **CR=0**; WLC/AHP equivalent weights produce same ranking within 1e-7 |
| Repeatability | Re-evaluation with same data/weights produces identical WLC ranking |
| Sensitivity | 12 perturbation runs GIS6; 10 runs road5; actual rank changes recorded |
| Persistence | Tiga evaluations saved, repeated save idempotent, full exact geometry/parameters/sensitivity reload |
| Phase 4 integration | Buffer/intersection/join/nearest/clusters/grid live API all passed |
| Exports | Actual frontend functions headless: 12 GeoJSON candidates, CSV12 rows, original geometry/definitions/provenance unchanged |
| Imports | Real HTTP CSV2 points/GeoJSON1 polygon passed; hypothetical/user-supplied labels retained |
| Browser | Unavailable; **0 browser checks passed**. Manual checklist provided |

Empat upstream Starlette/httpx/SWIG deprecation warnings dan MapLibre chunk 941.19 KB warning
kekal. Targeted temporary failures were fixed before final runs. Initial offline run skipped live DB
checks; ia bukan keputusan final di atas.

## Real ranking examples — descriptive assumptions only

Cohort dipilih sebagai dua mapped candidates terdekat dalam 5km setiap town reference,
bukan kajian semua tanah/fasiliti di kawasan itu. Tiada available parcel, owner, price atau permit direka.
Road-model weights: road proximity20%, warehouse proximity15%, industrial count25%,
selected Port Klang reference25%, selected airport15%.
Port target ialah **Port Klang town**, NOT terminal/gate.
Airport target ialah **Lapangan Terbang Sultan Abdul Aziz Shah (Subang), relation/16811593**, NOT KLIA/cargo gate.
Semua input priorities adalah andaian keputusan untuk ujian, bukan recommendation investment.

| Calon teratas setiap reference area | Rank daripada12 | Score/100 | Port town min | Subang airport min | Sensitivity rank |
| --- | --- | --- | --- | --- | --- |
| AHTV / Tanjong Malim · Depoh MARA Liner Tanjung Malim | 11 | 16.606 | 77.76 | 61.42 | 11–11 |
| Rawang · Unnamed OSM industrial_park (way/1494483669) | 9 | 55.565 | 49.17 | 32.83 | 9–9 |
| Shah Alam · Unnamed OSM industrial (way/911253375) | 1 | 94.005 | 17.85 | 19.18 | 1–2 |
| Bukit Raja · Unnamed OSM industrial_park (way/1120991654) | 6 | 73.650 | 14.99 | 26.09 | 6–7 |
| Klang · Unnamed OSM industrial_park (way/954409087) | 4 | 75.223 | 9.96 | 24.57 | 4–4 |
| Port Klang · Unnamed OSM industrial_park (way/1465120894) | 3 | 84.374 | 3.93 | 33.45 | 3–3 |

Shah Alam top score94.005 dan UMW93.918 bertukar rank1–2 pada sesetengah weight perturbations;
perbezaan kecil ini tidak membuktikan superiority tapak dalam dunia sebenar.
Data penuh/source IDs/criterion values ada dalam docs/phase6-*-result.json.

## Database dan integriti

Migrasi **0003_site_selection** additive disemak sebagai offline SQL, kemudian digunakan dalam
transaksi/advisory lock. Empat jadual baharu: site_scenarios, site_candidates, site_evaluations,
site_criterion_values. Existing candidate_sites foundation dikekalkan kerana satu feature unik
foundation tidak menyokong repeated scenarios/hypothetical geometry.
Definitions, raw inputs, AHP matrices dan weights disimpan dalam scenario JSONB;
resolved geometry/provenance dalam candidate rows; raw values/provenance dalam normalized rows;
rankings/ranges/sensitivity/provider snapshots dalam immutable evaluation JSONB.

Verified SSL/PostGIS3.3.7; **24 tables, 8 geometry columns/GiST, RLS24**, all geometry SRID4326.
Tiga saved scenarios/evaluations, 36 candidate rows, 192 criterion-value rows; zero invalid/wrong-SRID.
Fingerprints semua **20 jadual asal** sama: 5,234 OSM, 5,300 category links, 8 saved routes,
14 analysis jobs/results, 27 optimization scenarios, 25 solutions dan 4 comparisons kekal.
.env unchanged/ignored/untracked. Tiada reset, drop, old-row overwrite atau destructive downgrade.
Initial migration preflight detected a geometry_columns type-inference issue and rolled back;
type constraint was corrected before the successful committed upgrade. No partial schema was retained.

## API

GET /api/sites/catalog; POST /api/sites/ahp, /prepare, /evaluate, /import, /saved;
GET /api/sites/saved?limit=&offset=; GET /api/sites/saved/{id}.
Strict schemas, local Host/Origin guard, no fixture fallback for analysis, 1.5MB POST cap,
1MB imports, 12 candidates/8 criteria/25,000 combined vertices and 20s spatial statement timeout.
Evaluation cache24h/32 entries/4MB output cap. Routing reuses existing 24h bounded cache/quota.

## Acceptance, limits dan Phase 7

**Core Phase 6 implemented and passes automated/API/DB verification. Full visual acceptance
remains pending manual browser sign-off.** [Checklist S01–S19](docs/PHASE6_BROWSER_ACCEPTANCE.md).
Phase 5 browser acceptance remains pending separately. Phase 7 is not started.

Limits: observed-data relative MCDA, no official hazard/cost/zoning/land availability validation,
no raster engine, no verified truck routes, hypothetical reference geometry labels, maximum12/8,
no production authentication/distributed GIS job queue. Stored scores are snapshots, not live revaluations.
Browser interaction/GPU/font/layout/download behaviour has not been observed on this build.

## Evidence

- docs/phase6-backend.xml; docs/phase6-frontend.json
- docs/phase6-live.json; phase6-gis-result.json; phase6-road-wlc-result.json; phase6-road-ahp-result.json
- docs/phase6-gis-integration.json; phase6-imports.json; phase6-exports.json
- docs/phase6-baseline.json; phase6-integrity.json; phase6-migration.sql; phase6-migration-verification.json
- docs/phase6-suitability.geojson / phase6-suitability.csv
- docs/phase6-secret-scan.json; docs/openapi.json
- PHASE6_REVIEW.md; docs/PHASE6_BROWSER_ACCEPTANCE.md

No Docker, paid service, public deployment or Phase 7 work.
