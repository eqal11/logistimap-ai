# Phase 5 — Pelengkapan baki perbandingan dan peta

**24 Oktober 2026. Kedua-dua baki pembangunan telah dilaksanakan. Penerimaan visual browser masih belum disahkan. Phase 6 tidak dimulakan.**

## Hasil baharu

- Saved comparison history berhalaman, refresh, nama/masa, buka snapshot dan results yang jelas.
- Perbandingan baharu menyimpan exact solution IDs. Re-solving suatu scenario tidak menukar
  geometry comparison lama. Legacy snapshots dibaca tanpa diubah, menggunakan solution pada
  masa snapshot dan padanan metrics; jika tidak dapat disahkan, HTTP 409 tanpa penggantian.
- Peta memaparkan 2–4 solusi serentak: warna scenario A–D, dash vehicle, direction arrows,
  stop labels, selection/popup, ordered schedule, visibility scenario/vehicle dan fit controls.
- IDs dinamespace mengikut scenario + solution + vehicle; ID vehicle yang sama tidak bercampur.
  Pixel offsets membezakan ruas bertindih tetapi koordinat road geometry asal kekal.
- CSV comparison serta GeoJSON visible comparison mempunyai snapshot IDs, provenance,
  assumptions, standard car profile dan heavy_vehicle_verified=false.
- Matrix/final-road metrics dibezakan; unassigned stops dipaparkan supaya distance/cost
  lebih rendah dengan servis tidak penuh tidak dianggap peningkatan setara.
- Ralat geometry retrieval tidak memaparkan single-result geometry/matrix lama secara tersilap.
  Pertukaran tab membatalkan map-pick yang belum selesai.

## Keputusan baharu pada binaan akhir

| Semakan | Hasil |
| --- | --- |
| Backend penuh | **198 passed / 0 failed / 0 skipped**, termasuk **12 live PostGIS tests**, 65.04 s |
| Frontend penuh | **70 passed / 0 failed / 0 pending**, 14 fail |
| TypeScript / production build | Lulus / lulus |
| Installed MapLibre style specification | Expressions dash/offset dan selection diuji serta lulus validator |
| Live comparison API | Satu snapshot baharu, tiga solusi, lapan road geometries / 1,192 vertices; roundtrip tepat |
| Legacy comparison | Ketiga-tiga comparison sedia ada dibuka semula tanpa diubah |
| Export frontend sebenar, headless | 52 unique features: 8 MultiLineString + 44 Point; CSV tiga rows |
| Visibility/export | Sembunyi B → 33 features / 5 road routes; attribution dan geometry asal tepat |
| Data integrity | Semua row fingerprints asal pada **20 jadual** kekal; hanya satu comparison ditambah |
| Browser | **Tidak tersedia**: local browser use disabled in Work settings; tiada fresh browser pass |

Pembaikan dilakukan semasa ujian; final suites di atas lulus. Empat upstream deprecation
warnings dan warning MapLibre chunk 941.19 KB kekal, bukan test failures.
Ujian solver/routing 16 senario daripada review terdahulu ialah bukti sejarah;
pelengkapan ini menggunakan hasil OSRM tersimpan yang disahkan semula, **0 upstream routing calls**.
Tiada hasil lama dilabel semula sebagai ujian browser/routing baharu.

## API dan database

Endpoint baharu:
- GET /api/optimization/comparisons?limit=25&offset=0
- GET /api/optimization/comparisons/{id}
- GET /api/optimization/comparisons/{id}/solutions

POST /api/optimization/compare kekal dan kini menyimpan snapshot versi 2 dengan pinned solution IDs.
Pagination maksimum 100; sehingga empat solutions; 404 missing, 409 historical mismatch,
422 invalid parameters dan local Host/Origin guard. Frontend mengambil sepuluh history rows/page.
Tiada GET yang menulis semula legacy record.

Menggunakan jadual logistics_comparisons dan optimization_solutions sedia ada.
**Tiada migrasi dijalankan**; revision kekal 0002_logistics. SSL/PostGIS 3.3.7,
20 tables, tujuh geometry columns/GiST dan RLS disahkan.
5,234 OSM features, 5,300 category links, lapan saved routes, 14 analysis jobs/results,
27 scenarios, 25 solutions, 57 route assignments dan semua child rows asal tidak berubah.
Comparison count 3 → 4; tiada rekod diarchive/delete/reset. .env tidak diubah.

Snapshot rujukan:
`2611752b-e82b-4130-a2e5-2e733dfa4d64`
“Phase 5 completion · pinned 2 / 3 / 4 vehicle comparison”.

## Keputusan acceptance dan batasan

**Baki fungsi perbandingan/peta: siap dan lulus automated/API/DB checks.
Penerimaan penuh Phase 5 masih menunggu manual browser sign-off.**
Checklist tepat: [PHASE5_BROWSER_ACCEPTANCE.md](docs/PHASE5_BROWSER_ACCEPTANCE.md).
Tiada screenshot lama dikemukakan sebagai bukti baharu.

Batasan kekal:
- Standard car routing sahaja; bukan truck-verified, tiada live traffic atau verified tolls.
- Maksimum empat solusi dan 300,000 visible vertices untuk comparison; output terlalu besar
  ditolak dengan ralat nyata, bukan dipotong senyap.
- Legacy geometry hanya dimuat apabila history dan metrics sepadan; 409 jika tidak dapat disahkan.
- Dialog cetak, visual narrow/dark views dan real browser downloads belum diuji semula.
- Satu bounded local worker; production authentication/durable queue/provider capacity kekal
  kerja deployment berasingan. Tiada public deployment atau Docker.

## Bukti baharu dan fail utama

- docs/phase5-completion-backend.xml
- docs/phase5-completion-frontend.json
- docs/phase5-completion-live.json dan phase5-completion-baseline.json
- docs/phase5-completion-comparison.json dan phase5-completion-solutions.json
- docs/phase5-completion-exports.json, routes.geojson, comparison.csv dan hidden-b.geojson
- docs/phase5-completion-secret-scan.json
- docs/PHASE5_BROWSER_ACCEPTANCE.md

Kod: backend/app/optimization/repository.py, app/api/optimization.py;
frontend/src/services/comparisons.ts, features/LogisticsComparison.tsx,
LogisticsOptimization.tsx, MapWorkspace.tsx dan styles/optimization.css.
Tests ditambah pada API/live DB, services/comparisons, LogisticsComparison dan MapWorkspace.
Full current API schema: docs/openapi.json.

---

# Rekod sebelum pelengkapan ini — sejarah, bukan status fungsi terkini

# LogistiMap AI — Penerimaan Phase 5: semakan baharu

**24 Oktober 2026 — BELUM DITERIMA SEPENUHNYA; Phase 6 belum sedia dimulakan.**

Kod, solver, API dan PostGIS lulus pengesahan baharu. Ujian visual/interaksi browser
masih **TERHALANG**: alat melaporkan “Local browser use is disabled in Work settings”.
Tiada screenshot atau test record lama dianggap hasil baharu.

Inventori setiap fungsi, status incomplete/unsupported/untested, pembaikan dan batasan:
[docs/PHASE5_REVIEW.md](docs/PHASE5_REVIEW.md).

## Keputusan ujian baharu selepas pembaikan

| Semakan | Hasil baharu |
| --- | --- |
| Backend penuh | **193 passed, 0 failed, 0 skipped**, termasuk 10 live PostGIS tests; 50.78 s |
| Frontend penuh | **60 passed, 0 failed, 0 pending**, 12 fail |
| TypeScript | Lulus |
| Production build | Lulus; MapLibre chunk 941.19 KB, warning bukan kegagalan |
| pip check | Tiada broken requirements |
| Live optimization | **16 senario lulus**, diikuti 16 re-solve dengan kod akhir |
| Comparison | 2/3/4 vehicle snapshots dibanding dan disimpan melalui API |
| Export headless | GeoJSON 3 road geometries/19 features; CSV 3 assignments, 16 schedules, 1 summary |
| No-solution export | CSV tetap 1 context row/10 unassigned; GeoJSON 0 geometry, tiada fake route |
| Browser baharu | **0 checks passed; terhalang**, bukan lulus |
| Phase 1–4 regression | Suites penuh + live search, buffer, saved route/analysis reload, health/ready lulus |

Empat pembaikan: malformed GeoJSON menjadi 422; independent node/service validation;
optional-service penalty meliputi depot arcs; empty-route CSV mengekalkan konteks.
Targeted regression tests gagal sebelum pembaikan dan lulus selepasnya.
Empat upstream deprecation warnings kekal tanpa test failure.

## Senario jalan sebenar yang diuji semula

Semua lokasi ialah imported OSM candidate references; demand, capacity, RM1.50/km
dan RM10 per used vehicle ialah **andaian hipotesis**, bukan actual business shipments.
A/B/C menggunakan fresh upstream OSRM matrices yang diperoleh pada semakan ini:
121/81/49 cells, semuanya reachable. Variasi menggunakan semula cache matrix sebenar
daripada semakan ini. Dua-depot mendapat matrix sebenar baharu dengan susunan node berbeza.
Semua 16 payload kemudian diselesaikan semula dalam proses Python baharu menggunakan
kod akhir; hasil asal tersimpan tidak ditindih.

Jarak, driving time dan kos di bawah ialah **final road geometry**, bukan jumlah matrix.
Matrix metrics disimpan berasingan dalam evidence; perbezaan via-point bukan disembunyikan.

| Senario | Stop assigned | Vehicle used | Final km | Driving s | Kos andaian RM | Keputusan |
| --- | --- | --- | --- | --- | --- | --- |
| Shah Alam · 10 destinasi / 3 kenderaan | 10/10 | 3 | 19.8853 | 3178.8 | 59.83 | best_found; LULUS semakan |
| Rawang · 8 destinasi / 2 kenderaan | 8/8 | 2 | 37.3800 | 4055.7 | 76.07 | best_found; LULUS semakan |
| Port Klang · 6 warehouse / 3 tersedia | 6/6 | 2 | 68.2496 | 5354.5 | 122.38 | best_found; LULUS semakan |
| Fleet 2 | 8/10 | 2 | 13.4407 | 2397.4 | 40.16 | best_found; LULUS semakan |
| Fleet 3 | 10/10 | 3 | 19.8853 | 3178.8 | 59.83 | best_found; LULUS semakan |
| Fleet 4 | 10/10 | 3 | 19.8853 | 3178.8 | 59.83 | best_found; LULUS semakan |
| Capacity shortfall, optional | 1/10 | 1 | 1.4676 | 375.4 | 12.20 | best_found; LULUS semakan |
| Time windows 08:00–12:00 | 10/10 | 3 | 19.8853 | 3178.8 | 59.83 | best_found; LULUS semakan |
| Mandatory, kapasiti 2 vs demand 20 | 0/10 | 0 | Tiada laluan | — | — | no_solution_found; LULUS semakan |
| Pickup–delivery pair | 10/10 | 2 | 19.7301 | 3045.4 | 49.59 | best_found; LULUS semakan |
| Dua depot | 9/9 | 3 | 19.4842 | 2880.3 | 59.23 | best_found; LULUS semakan |
| TSP · satu vehicle, kapasiti 100 | 10/10 | 1 | 17.5152 | 2779.6 | 36.27 | best_found; LULUS semakan |
| Objektif time | 10/10 | 3 | 20.2435 | 3061.3 | 60.36 | best_found; LULUS semakan |
| Objektif cost | 10/10 | 3 | 19.8853 | 3178.8 | 59.83 | best_found; LULUS semakan |
| Objektif vehicle count | 10/10 | 3 | 19.8853 | 3178.8 | 59.83 | best_found; LULUS semakan |
| Objektif balance | 10/10 | 3 | 20.0422 | 3115.0 | 60.06 | best_found; LULUS semakan |

Semua hasil feasible live ialah **best_found**, tiada bukti optimum global.
Mandatory shortfall melaporkan **no_solution_found/search_failed** dan semua 10 stop
unassigned; aplikasi tidak mengaku solver membuktikan infeasible/optimal.
Demand 20 melebihi kapasiti 2 memang tidak boleh diservis sepenuhnya dalam model ini.
Fleet 2 lebih rendah jarak kerana dua stop tidak diservis; bukan perbandingan efisiensi demand penuh.

## Database, migrasi dan integriti

- Supabase SSL/PostGIS **3.3.7** disahkan semula.
- Revision kekal **0002_logistics**; source migration diperiksa, **tiada migrasi dijalankan**.
- 20 project tables, 7 geometry columns EPSG:4326, 7 GiST indexes, RLS pada 20 tables.
- Foreign keys logistics diperiksa; 0 invalid/wrong-SRID vehicle route geometries.
- **5,234 OSM, 8 saved routes, 14 analysis_jobs dan 14 analysis_results** kekal.
- Semua row IDs/checksums daripada 10 scenario, 9 solution dan child records asal
  kekal tanpa hilang atau berubah. Tujuh saved Phase 4 analyses aktif boleh disenaraikan.
- Review menambah **17 scenario baru** (16 solved + 1 duplicate), 16 jobs/solutions
  dan 1 comparison; kini 27 scenario/25 solutions/3 comparisons. Tiada rekod lama dipadam.
- .env kekal ignored/untracked; semakan secret pada source/docs/dist tiada padanan.

## Perkara belum lengkap, tidak disokong dan belum diuji

1. Browser terkini: map geometry/warna/arah/popup/visibility, comparison dan downloads
   perlu pengesahan visual/interaksi baharu setelah akses browser diaktifkan.
2. Comparison snapshot tersimpan tetapi tiada list/reopen history API/UI.
   Alternative-solution map overlay belum dilaksanakan; carta/jadual perbandingan tersedia.
3. Printable report kod wujud; dialog dan output cetakan belum diuji semula.
4. 17–24 node batching diuji unit sahaja; tiada large public-server/load test.
   Live cancellation dan process-restart recovery tidak sengaja dicetuskan pada public routing.
5. OSRM standard car: tiada verified truck restrictions, traffic, tolls, driver breaks,
   split shipments, multi-commodity, depot reload atau production SLA.
6. Satu local worker, bounded solver 1–20s, cache 24h, 12 provider calls/minit.
   Refresh browser kehilangan active job ID dalam memory; saved snapshots/results kekal.
7. Final geometry yang gagal constraints ditanda tidak verified dan memerlukan replan;
   tiada automatic re-optimization berdasarkan final via-point timings.
8. Production auth/durable queue/provider capacity belum tersedia; local review sahaja.

Penerimaan penuh memerlukan baki browser checks dan keputusan scope untuk dua fungsi
comparison yang belum lengkap. **Phase 6 tidak dimulakan.**

## Bukti dan fail

- [Inventori/review lengkap](docs/PHASE5_REVIEW.md)
- [Hasil live baharu](docs/phase5-review-live.json)
- [16 re-solve kod akhir](docs/phase5-review-final-source.json)
- [PostGIS/integriti/API regression](docs/phase5-review-database.json)
- [Baseline semua row asal](docs/phase5-review-baseline.json)
- [Backend final XML](docs/phase5-review-backend-final.xml)
- [Frontend final JSON](docs/phase5-review-frontend-final.json)
- [Export verification](docs/phase5-review-exports.json)
- [Duplicate/archive/restore](docs/phase5-review-snapshots.json)
- [Browser blocked](docs/phase5-review-browser.json)
- [Secret scan](docs/phase5-review-secret-scan.json)

Sumber utama diubah: backend/app/optimization/imports.py, solver.py,
tests/test_optimization_review.py, tests/test_optimization_api.py,
frontend/src/services/optimization.ts dan optimization.test.ts.
Review scripts hanya menambah records berlabel review atau membaca DB; tiada migration/reset.

---

# Rekod pelaksanaan terdahulu — sejarah, bukan keputusan semakan baharu

# LogistiMap AI — Laporan Penerimaan Phase 5
Tarikh: 24 Oktober 2026. Status: **sedia untuk semakan Phase 5**. Phase 6 tidak dimulakan.

## Modul yang dilaksanakan
- Scenario Builder: 1–4 depot, 1–6 kenderaan, 1–20 stop, koordinat EPSG:4326 dan provenance OSM.
- Fleet: kapasiti integer dalam unit konsisten, availability, depot mula/akhir, waktu operasi, had jarak/kerja, kos MYR yang boleh disunting.
- Delivery: demand hipotesis atau input pengguna, priority, service duration, mandatory, hard service-start windows dan pasangan pickup–delivery.
- Pilihan GIS sebenar, carian nama tempat/koordinat, klik peta, import CSV/point GeoJSON dan guna semula point hasil analisis yang sudah dimuat.
- Results: assignment, ordered schedules, peak load/utilization, unassigned, solver status, matrix/final-road metrics, transparent costs dan warnings.
- Peta MapLibre: warna setiap kenderaan, arah, nombor stop, selection/popup, layer visibility, fit, basemap dan lakaran Phase 1–4.
- Saved Scenarios: save/reload/duplicate/archive/restore dengan confirmation. Snapshot asal dikekalkan.
- Comparison: 2–4 saved solved scenarios, carta/table dan snapshot perbandingan dalam PostGIS.
- GeoJSON laluan, CSV assignments/schedules/summary dan laporan cetak yang menyertakan andaian dan batasan.

## Algoritma dan ketepatan
Google OR-Tools **9.15.6755**, RoutingModel, parallel cheapest insertion diikuti guided local search.
Ini bukan nearest-neighbour yang dilabel optimal. Sokongan TSP, VRP/CVRP, multi-vehicle, multi-depot start/end,
pickup–delivery pada kenderaan yang sama dengan precedence, capacity, time windows, max duration/distance.
Dimensi load bertanda memastikan muatan tidak negatif, tidak melebihi kapasiti dan kosong semasa tiba di depot akhir.
Hasil diperiksa semula secara bebas untuk assignment partition, duplication, load, precedence, windows dan had perjalanan.

Objektif: matrix distance, driving time, supplied cost, jumlah kenderaan kemudian jarak,
atau jumlah jarak + 20 × laluan terpanjang. Optional-stop priority penalties mengutamakan weighted service
sebelum objektif travel. Mandatory stops tidak boleh digugurkan. Semua demand ujian adalah **hipotesis**.
Tiada pelanggan, kapasiti truck sebenar, harga bahan api atau tol direka.

Status successful/partial search dilaporkan sebagai **best_found**. Global optimality tidak dituntut.
Hanya kod OR-Tools ROUTING_OPTIMAL boleh menandakan optimal untuk model integer tersebut.
No solution, proven infeasible dan timeout dibezakan. Had 1–20 saat, default tiga saat.

OSRM Table menyediakan matrix jalan **asymmetric**, bukan Euclidean. Sel null adalah unreachable.
Fallback-speed cells ditolak. Distance matrix mengikuti fastest-time road path, tidak semestinya shortest-distance path.
Route/via-point geometry kadang-kadang berbeza daripada jumlah table kerana kesinambungan belokan.
Matrix objective/schedule dan final road distance/time/cost dilaporkan berasingan.
Final road windows/had disemak semula; geometri yang gagal diambil tidak diganti dengan garisan lurus.

## API baharu
Rujuk docs/API.md dan docs/openapi.json untuk schema lengkap.

| Endpoint | Fungsi |
| --- | --- |
| POST /api/optimization/scenarios | Validate dan simpan snapshot |
| GET /api/optimization/scenarios | Senarai berpaginasi |
| GET /api/optimization/scenarios/{id} | Muat semula parameter |
| POST /api/optimization/scenarios/{id}/duplicate | Salin snapshot |
| POST /api/optimization/scenarios/{id}/archive atau /restore | Recoverable, confirmed:true |
| POST /api/optimization/scenarios/{id}/solve | Queue satu bounded job, HTTP 202 |
| GET /api/optimization/jobs/{id} | Status/stage |
| POST /api/optimization/jobs/{id}/cancel | Cooperative cancellation |
| GET /api/optimization/scenarios/{id}/results | Muat hasil PostGIS |
| POST /api/optimization/matrix | Matrix sebenar berhad |
| POST /api/optimization/compare | Banding 2–4 solusi dan simpan snapshot |
| GET /api/optimization/vehicles?scenario_id={id} | Fleet snapshot |
| POST /api/optimization/import | Validated CSV/GeoJSON candidate stops |

Semua operasi memerlukan enabled local loopback workspace, Host/Origin dibenarkan dan live PostGIS.
POST body maksimum 1.5 MB; fail import maksimum 1 MB/20 records. Tiada arbitrary SQL/code/path execution.
Render template mengekalkan OPTIMIZATION_ENABLED=false sehingga production authentication/queue/provider disediakan.

## Perubahan database
Migrasi **0002_logistics** disemak sebagai offline SQL sebelum digunakan dalam transaksi dengan advisory lock.
Lapan jadual tambahan:
logistics_depots, logistics_vehicles, logistics_stops, logistics_demands,
optimization_jobs, optimization_solutions, vehicle_route_assignments, logistics_comparisons.

optimization_scenarios foundation digunakan untuk snapshot. Foundation vehicles/shipments tidak diubah;
jadual tambahan menyokong koordinat pengguna yang tiada spatial_feature FK.
Tiga geometry columns baharu: dua POINT dan satu MULTILINESTRING, semua SRID 4326 + GiST.
Keseluruhan projek kini **20 jadual, tujuh geometry columns/indeks GiST, RLS pada semua 20 jadual**.
Tiada destructive migration. Downgrade Phase 5 disekat untuk melindungi rekod.

Checksum awal/akhir mengesahkan rekod lama kekal: **5,234 OSM features, lapan saved routes,
14 analysis_jobs dan 14 analysis_results rows** (tujuh saved Phase 4 analyses aktif).
Bukti: docs/phase5-database-baseline.json dan docs/phase5-database-verification.json.
Tiada credential dimasukkan ke browser atau laporan.

## Senario sebenar dan keputusan
Sumber lokasi ialah OSM yang sudah diimport; titik footprint adalah representative reference,
bukan verified gate. Demand dua unit/stop, kapasiti lapan unit/kenderaan, RM1.50/km + RM10/kenderaan
ialah **andaian ujian hipotesis**, bukan kadar pasaran atau penghantaran perniagaan sebenar.

| Senario | Keputusan yang diperiksa | Status |
| --- | --- | --- |
| A Shah Alam | Warehouse + 10 industri, 3 kenderaan; 121 matrix cells; 10/10 assigned, 18.5191 km / 2,671.4 s matrix, RM57.77; 3 geometri sebenar | LULUS |
| B Rawang | Warehouse + 8 industri, 2 kenderaan; 81 cells; 8/8 assigned, 36.2563 km / 3,749.5 s matrix, RM74.39; 2 geometri | LULUS |
| C Port Klang | Depot warehouse + 6 warehouse candidates; 49 cells; 6/6 assigned, 2 daripada 3 kenderaan digunakan, 68.1261 km / 5,270.3 s matrix, RM122.19 | LULUS |
| D fleet 2 | Kapasiti 16 untuk demand 20; 8/10 stops assigned; 12.4394 km / 2,006.9 s, RM38.66; 2 stops/4 units unassigned | LULUS |
| D fleet 3 | 10/10 assigned; 18.5191 km / 2,671.4 s, RM57.77; 3 digunakan | LULUS |
| D fleet 4 | 10/10 assigned; best solution menggunakan 3 daripada 4, matrix metrics sama dengan D3 | LULUS |
| E capacity shortfall | Satu vehicle capacity 2 vs demand 20; 1 stop assigned, 9 stops/18 units unassigned | LULUS |
| F hard windows | Semua 10 stop service-start 08:00–12:00, vehicle 08:00–16:00; matrix dan final road checks sah | LULUS |
| G persistence | Parameter dan hasil setiap senario di atas dimuat semula daripada PostGIS; geometry valid dan unik | LULUS |
| H route export | GeoJSON browser: satu road MultiLineString, 241 vertices, empat point references; sama tepat dengan provider geometry tersimpan; tiga CSV sah | LULUS |

F final road result: **19.8853 km, 3,178.8 s driving, RM59.83**; matrix masih
18.5191 km / 2,671.4 s. Tiada hasil global optimum dibuktikan.
D2 lebih rendah jarak/kos kerana dua stop tidak diservis; ia bukan bukti lebih efisien untuk demand penuh.
Sumber ID/koordinat, job/scenario IDs, vertex counts dan metadata ada dalam docs/phase5-live-results.json.

## Ujian dan bukti browser
- Backend: **183 passed**, termasuk sepuluh live PostGIS tests; tiada failed/skipped dalam final opted-in run.
- Frontend: **58 passed**, 12 files; TypeScript dan production build berjaya.
- pip check: tiada broken requirements.
- Nonfatal warnings: upstream Starlette/httpx dan OR-Tools SWIG deprecations; MapLibre chunk sekitar 941 KB.
- Browser: pemilihan warehouse GIS sebenar, edit kapasiti/kos, import dua CSV candidates, tambah/remove point peta, save/solve, reload hasil, map layer visibility, fit geometry, comparison 2/3/4 vehicles dan duplicate/archive/restore berkonfirmasi lulus.
- Browser solve tambahan: satu depot Pharmaniaga, dua OSM industrial candidates, demand hipotesis empat unit; kedua-dua stop assigned. Matrix 11.4955 km / 953.9 s / RM27.24; final road 11.9011 km / 1,105.9 s / RM27.85. Had final road disahkan.
- Muat turun: GeoJSON geometry sah dan sama tepat dengan PostGIS; CSV assignments satu baris, schedules empat baris, summary satu baris; semuanya mempunyai attribution dan demand_context.
- Console browser: tiada application error. Basemap gelap pihak ketiga mengeluarkan satu amaran cosmetic missing sprite wood-pattern; road overlays, nombor stop dan arah kekal berfungsi. Light/dark theme dan basemap switching diperiksa; paparan dipulihkan ke light.
- Laporan cetak disediakan melalui print stylesheet dan butang browser. Dialog printer fizikal tidak dijalankan.

Bukti ujian: docs/phase5-backend-tests.xml, docs/phase5-frontend-tests.json.
Bukti browser: docs/phase5-browser-checks.json, docs/phase5-optimization-map.png, docs/phase5-optimization-dark.png, docs/phase5-comparison.png dan docs/phase5-browser-routes.geojson/CSV. Semakan akhir: docs/phase5-final-verification.json dan docs/phase5-secret-scan.json.

## Batasan dan kerja sebelum Phase 6
- OSRM car sahaja; tidak verified heavy vehicle, height/weight/axle/hazmat restrictions.
- Tiada traffic langsung, tol, jam operasi sebenar, legal gate access, driver breaks atau inventory depot.
- Public demo light use, tiada SLA. Satu upstream call pada satu masa, 1.1 s spacing, 12/minute.
  Provider timeout/cooldown/size limits boleh menghalang solve atau final geometry; errors nyata.
- Input POST 1.5 MB, import 1 MB dan persisted solution 8 MB; fit geometry diuji dengan 150,000 vertices tanpa argument overflow.
- Matrix cache 24 jam/64 entri. ≤16 nodes satu request; 17–24 nodes sehingga sembilan blocks.
  Public quota boleh mengehadkan scenario besar. Tiada ujian beban public server.
- Satu local worker/job sahaja, cooperative cancel, proses restart menandakan interrupted. Tiada distributed queue.
- Kapasiti satu unit integer; tiada split shipments, multi-commodity dimensions, legal truck routing, reload trips,
  route-specific toll estimate atau live order feed. Empty vehicles tidak direposition antara depot.
- Reuse analysis secara terus terhad kepada point results yang telah dimuat. Polygon bukan verified entrance.
- Coverage ialah imported mapped candidates; tidak membuktikan semua warehouse/facility wujud telah dipetakan.
- Production rollout memerlukan authentication/authorization, durable jobs, backend role sesuai,
  dan provider routing dengan kapasiti/polisi penggunaan production.
- Phase 6 belum dimulakan. Tiada public deployment/paid service diaktifkan.


## Fail utama dan arahan yang dilaksanakan
Backend: app/schemas/optimization.py, app/optimization/{solver,matrix,jobs,repository,imports}.py,
app/models/logistics.py, app/api/optimization.py, app/core/body_limit.py,
alembic/versions/0002_logistics.py dan sambungan main/config/migration verification.
Frontend: features/LogisticsOptimization.tsx, LogisticsForms.tsx, LogisticsLocationPicker.tsx,
MapWorkspace.tsx, services/optimization.ts, store/optimization.ts, styles/optimization.css,
App.tsx dan Sidebar.tsx. Dependency range/runtime/dev locks dikemas kini.

Arahan sebenar: project venv pip install ortools>=9.15,<10; pip check;
Alembic offline SQL; verify_phase5_db.py (migrasi selamat);
verify_phase5_live.py A/B/C/D2/D3/D4/E/F/compare; pytest termasuk live Supabase;
npm.cmd test, npm.cmd run typecheck dan npm.cmd run build.
Final full pytest: 183 passed / 0 failed / 0 skipped; frontend: 58 passed / 0 failed.
Tiada public deployment atau Phase 6 dilaksanakan.
