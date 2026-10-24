# Phase 5 — Status selepas pelengkapan baki

24 Oktober 2026. **Saved comparison history dan simultaneous optimization overlays sudah siap.**
Ujian akhir baharu: 198 backend (12 live PostGIS), 70 frontend/14 files; TypeScript,
production build dan installed MapLibre style validation lulus.

| Baki yang ditutup | Bukti baharu |
| --- | --- |
| Persistent history/retrieval | Tiga legacy snapshots dibuka; snapshot baharu roundtrip sama; GET pagination/404/409/422/403 diuji |
| Immutable solution references | New snapshots pin solution IDs; rollback live test membuktikan later solve tidak menukar snapshot |
| Multiple solutions serentak | Tiga solutions / lapan road geometries / 1,192 vertices daripada stored OSRM results |
| Route differentiation | Scenario colours A–D, vehicle dashes, pixel offsets, arrows/labels, namespaced IDs; installed MapLibre spec validator lulus |
| Selection/visibility | Component/map tests memilih scenario+vehicle yang betul; hide scenario/route dan inspect-unhide lulus |
| Geometry integrity/export | 52 IDs unik, 8 road MultiLineStrings/44 points; actual frontend export geometry tepat seperti DB; CSV3 rows |
| Error recovery | Failed historical geometry retrieval mengosongkan overlay, tidak menunjukkan single-result lama; snapshot summary kekal |
| Data preservation | Fingerprint 20 jadual asal kekal; hanya satu comparison ditambah, tiada migrasi |

**Browser acceptance belum disahkan.** Akses browser dimatikan dalam Work settings.
[Checklist manual B01–B18](PHASE5_BROWSER_ACCEPTANCE.md) ialah pengganti arahan penerimaan
yang diminta pengguna apabila browser unavailable, bukan keputusan lulus.
Tiada screenshot lama digunakan semula.

Tiada upstream routing calls baharu dalam pelengkapan ini. Hasil 16 live solver scenarios
daripada review sebelum ini kekal sebagai bukti sejarah. Backend suite baharu menguji solver
dan regressions; live completion API/DB checks mengesahkan exact saved OSRM geometries semula.

Batasan: car profile bukan truck-verified; 2–4 solusi dan maksimum 300,000 visible vertices;
legacy mismatches → 409; print/visual GPU/browser downloads masih belum diuji baharu.
Production authentication/durable queue dan routing production capacity kekal belum tersedia.
**Development scope Phase 5 lengkap; full acceptance pending manual browser sign-off. Phase 6 tidak dimulakan.**

Bukti: phase5-completion-backend.xml, phase5-completion-frontend.json,
phase5-completion-live.json, phase5-completion-exports.json dan
phase5-completion-secret-scan.json. Laporan penuh terkini: ../PHASE5_ACCEPTANCE.md.

---

# Inventori dan keputusan sebelum pelengkapan — sejarah

Status “belum lengkap” bagi dua fungsi comparison dalam inventori lama di bawah telah
digantikan oleh keputusan terkini di atas. Kiraan 193/60 dan 16 live solver scenarios
di bawah ialah rekod review terdahulu, bukan ujian yang baru dijalankan pada pelengkapan ini.

# Semakan penerimaan baharu Phase 5 — 24 Oktober 2026

Semakan ini membaca kod sebenar, README.md, PROGRESS.md, docs/PHASE4_ACCEPTANCE.md dan PHASE5_ACCEPTANCE.md.
Ia tidak membina semula Phase 5. Bukti `phase5-review-*` ialah hasil semakan baharu;
fail `phase5-live-results.json`, screenshot dan keputusan lama kekal sebagai sejarah sahaja.

## Keputusan penerimaan

**Belum diterima sepenuhnya.** Ujian automatik, API, solver jalan sebenar dan PostGIS
lulus; pengesahan visual/interaksi browser baharu disekat kerana akses browser tempatan
dimatikan dalam tetapan Work. Tiada screenshot lama digunakan sebagai bukti baharu.
Phase 6 tidak dimulakan. Fungsi perbandingan snapshot yang belum lengkap diterangkan di bawah.

## Pembaikan yang dibuat

1. GeoJSON array/null, feature null dan geometry tidak sah kini memberi ralat terkawal
   HTTP 422, menggantikan AttributeError/500. Pemeriksaan bentuk objek dibuat sebelum akses medan.
2. Validator bebas solver mengesahkan identiti node dan tempoh servis yang tepat,
   serta menolak depot perantaraan yang tidak dijangka.
3. Penalti optional-stop mengira had kos semua arc termasuk depot. Sebelum pembaikan,
   ujian kos tinggi yang sah dalam had input menggugurkan stop yang boleh diservis;
   ujian regresi menghasilkan kegagalan sebenar sebelum pembaikan dan lulus selepasnya.
4. CSV assignments/schedules tanpa laluan kini masih mengandungi status solver,
   unassigned deliveries, attribution dan andaian senario.

Tiada skema, .env, OSM, laluan/analisis asal atau senario lama diubah oleh pembaikan ini.

## Inventori lengkap fungsi Phase 5

Status **dilaksanakan/diuji** menyatakan lapisan bukti (unit, live API/DB atau headless export).
Ia tidak menyatakan browser baharu lulus.

| Keperluan | Status dan bukti sebenar |
| --- | --- |
| Google OR-Tools 9.15.6755 | Dilaksanakan; RoutingModel, parallel cheapest insertion + guided local search; unit + solver live |
| TSP, VRP, CVRP | Dilaksanakan; ujian unit dan senario jalan sebenar |
| Banyak kenderaan | Dilaksanakan; Shah Alam tiga, Rawang dua, perbandingan dua/tiga/empat |
| Banyak depot | Dilaksanakan sebagai depot mula/akhir setiap kenderaan; unit + dua depot live; tiada reload/inventory |
| Pickup–delivery | Dilaksanakan, kapasiti bertanda, same vehicle + precedence; unit + live |
| Kapasiti | Dilaksanakan; integer satu unit; unit + live shortfall |
| Delivery/vehicle/depot time windows | Dilaksanakan sebagai hard service-start windows, saat dalam satu hari; unit + live 08:00–12:00 |
| Tempoh servis dan waiting | Dilaksanakan; independent service/arrival/load validation; unit dan live |
| Max route distance dan working duration | Dilaksanakan; unit had jarak/tempoh dan final-road revalidation; bukan peraturan truck |
| Optional priority/mandatory stops | Dilaksanakan; weighted priority, explicit unassigned; unit + live optional dan mandatory shortfall |
| Solver status | best_found, optimal hanya kod 7, no_solution_found, proven infeasible, timeout berasingan; tiada dakwaan global optimum untuk hasil live |
| Semua lima objektif | Dilaksanakan: distance, time, supplied cost, count-first vehicles, distance + 20 × longest route; unit dan live |
| Pembina senario/depot | Dilaksanakan: nama/koordinat/operating windows/notes, maksimum empat depot; API/DB diuji, interaksi browser baharu belum disahkan |
| Fleet configuration | Dilaksanakan: ID/type/enable/capacity/start/end/cost/max limits; snapshot setiap senario, bukan shared fleet master |
| Delivery editor | Dilaksanakan: nama/koordinat/demand/service/priority/window/mandatory/pair; frontend tests + backend validation |
| Road matrix | OSRM Table distances metres/durations seconds sebenar; asymmetric, no fallback_speed; fresh upstream A/B/C |
| Matrix batching | ≤16 nodes satu call; 17–24 nodes bounded blocks sehingga sembilan calls; batching diuji synthetic unit, tidak diuji besar di public server |
| Cache | 24 jam/64 entri, provider/profile/coordinates/snap-specific; unit + reuse matrix yang diambil dalam semakan ini |
| Timeout/quota/missing routes | Guard 1.1 saat, 12/minit, bounded timeout dan explicit errors/null arcs; provider failures diuji secara suntikan unit, tiada gangguan public server disengajakan |
| Assignment/schedule validation | Dilaksanakan: unik, partition, mandatory, precedence, kapasiti, time, depot, distances; unit + live |
| Final road geometry | OSRM Route sebenar, MultiLineString chunks; valid geometry, vertices, endpoint/metric validation; live + export |
| Matrix vs final road metrics | Dilaporkan berasingan; final via-point timings/limits/cost diperiksa, tiada garisan lurus gantian |
| Auto-repair final geometry constraint mismatch | Belum dilaksanakan; warning jelas, final-road verification false; pengguna perlu replan; unit failure-path lulus |
| Depot/delivery markers, nombor stop, warna/arah | Kod MapLibre dilaksanakan; map/component tests lulus; pengesahan visual browser baharu terhalang |
| Route selection/popup/fit/visibility | Kod dilaksanakan dan component/map tests; browser baharu belum disahkan |
| Alternative optimization solution map overlay | Belum dilaksanakan; scenario comparison hanya carta/jadual, satu solution aktif pada map |
| Fleet summary/utilization | Dilaksanakan daripada demand dan kapasiti input serta load sebenar; unit + live |
| Explicit MYR operating/fixed/fuel/driver costs | Dilaksanakan dan diuji; tiada harga sebenar direka; model integer-rounded, hasil tidak dituntut optimal |
| Verified toll costs | Tidak disokong; tiada dataset tol yang disahkan |
| Cost/delivery/km/vehicle/scenario | Dilaksanakan daripada andaian input; unit + live + exports |
| Scenario comparison | Dilaksanakan 2–4 saved solutions, status/distance/time/cost/vehicles/assignment, carta + jadual dan SQL snapshot; live comparison diuji |
| Reopen comparison snapshot history | Belum lengkap: jadual menyimpan snapshot tetapi tiada GET/list/UI untuk membuka semula comparison tersimpan |
| GIS warehouse/industrial/hub references | Dilaksanakan; backend mengambil representative point sebenar dan source ID daripada PostGIS; live |
| Place search/manual coordinates/map click | Kod dilaksanakan; regresi komponen; belum diuji semula dalam browser pada semakan ini |
| Reuse saved analyses | Terhad kepada point yang sudah dimuat dalam workspace; polygon bukan entrance/gate dan tidak ditukar secara senyap |
| CSV/GeoJSON destination import | Dilaksanakan: 1–20 WGS84 2D points, demand integer, schema/size checks; unit/API termasuk input rosak |
| Save/reload scenarios/results | Dilaksanakan immutable snapshot + normalized child rows/geometry; live setiap senario + rollback integration |
| Duplicate/archive/restore | Dilaksanakan, confirmed:true dan soft archive; live DB rollback tests serta fresh API check pada salinan baharu |
| Logistics DB entities | Lapan jadual tambahan, foundation optimization_scenarios; migration source reviewed, DB actual constraints/geometry/RLS verified |
| Jobs/progress | Satu bounded local worker, persisted stage polling; live API solve |
| Cancel | Cooperative antara stages, solver/in-flight request tidak boleh dihentikan serta-merta; kod disemak, tidak diuji live dengan membatalkan public request |
| Restart/refresh recovery | Backend menandakan unfinished jobs interrupted; tiada distributed queue; browser refresh kehilangan active job ID dalam memory, saved result boleh dibuka semula |
| GeoJSON route export | Fungsi frontend sebenar dijalankan headlessly dengan hasil live; geometry sama tepat dengan hasil PostGIS; browser download belum diuji semula |
| CSV assignments/schedules/summary | Fungsi frontend sebenar + CSV parser + attribution/assumptions diuji; empty-route CSV regression lulus |
| Printable report | Kod report/print stylesheet wujud; dialog/hasil cetakan baharu belum diuji |
| Responsive/light-dark/accessibility | Kod sedia ada dan component tests; visual/browser baharu belum disahkan |
| Security/local guards | Strict schemas, local Host/Origin, body/import/solver limits, backend-only secrets; tests + ignored/untracked .env check |
| Production auth/authorization | Belum disediakan; optimization dihadkan kepada local workspace dan Render default disabled |
| Truck restrictions/live traffic/driver breaks/split loads/multi-commodity | Tidak disokong; UI/result warnings menerangkannya |
| Isochrones Phase 4 | Tidak disokong oleh provider semasa; HTTP 501 diuji semula, bukan lulus sebagai fungsi tersedia |
| Phases 1–4 regression | Full suites + live multikategori PostGIS, saved routes/analysis reload, real buffer dan health/ready; browser regression baharu terhalang |

## Ujian baharu

- Backend final: **193 passed, 0 failed, 0 skipped**, termasuk sepuluh live PostGIS tests; 50.78 saat.
- Frontend final: **60 passed, 0 failed, 0 pending**, 12 fail.
- TypeScript `npm.cmd run typecheck`: lulus.
- Production `npm.cmd run build`: lulus.
- `pip check`: tiada dependency rosak.
- Warnings: empat deprecation Starlette/httpx/OR-Tools SWIG; MapLibre JS chunk 941.19 KB.
- Initial full rerun sebelum pembaikan: 183 backend/58 frontend. Ia bukan keputusan final.
- Targeted tests semasa debug benar-benar gagal sebelum pembaikan; kegagalan itu telah dibaiki.
- Tiada ujian beban public routing, 24-node live matrix atau deployment production dilakukan.

Bukti: `phase5-review-backend-final.xml`, `phase5-review-frontend-final.json`,
`phase5-review-live.json`, `phase5-review-database.json` dan `phase5-review-exports.json`.
Hasil nombor senario dan checksum akhir diringkaskan dalam PHASE5_ACCEPTANCE.md.

## Sumber dan batasan data

Lokasi daripada OSM yang telah diimport ialah candidate reference/footprint point, bukan verified gate,
pelanggan atau penghantaran perniagaan. Semua shipment demand, RM1.50/km dan fixed RM10
dalam ujian live adalah andaian hipotesis. Standard-car OSRM bukan verified truck routing;
tiada toll, live traffic atau jaminan operational access. Coverage 5,234 objek bukan seluruh Malaysia.

Rujukan primer: [OR-Tools routing options](https://developers.google.com/optimization/routing/routing_options),
[OSRM HTTP API](https://project-osrm.org/docs/v26.4.0/http),
[polisi routing FOSSGIS](https://routing.openstreetmap.de/about.html).
Public provider digunakan secara ringan, serial, berhad dan dengan caching.

## Baki penerimaan sebelum Phase 6

Aktifkan akses browser tempatan dan jalankan semula map, selection, visibility, save/open,
comparison dan download GeoJSON/CSV pada binaan terkini. Uji print jika penerimaan cetakan diperlukan.
Tentukan scope untuk comparison snapshot history dan alternative-solution map overlay;
kedua-duanya tidak boleh dianggap siap hanya kerana comparison carta/jadual tersedia.
Semua rekod lama mesti dikekalkan. Ini semakan Phase 5 sahaja, bukan kebenaran memulakan Phase 6.
