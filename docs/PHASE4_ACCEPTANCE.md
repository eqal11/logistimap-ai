# Fasa 4 — Advanced GIS & Spatial Analytics

24 Oktober 2026, Windows x64. **Sedia untuk semakan tempatan. Fasa 5 tidak dimulakan.**
Tiada Docker, deployment awam atau servis berbayar diaktifkan.

## Modul yang dilaksanakan

1. **Spatial Analysis Toolbox** — buffer meter/km, intersection, clip, union,
   dissolve (semua atau kumpulan kategori), difference, spatial join
   (intersects/within/contains/nearest), aggregation by polygon dan nearest facility.
2. **Industrial Clusters** — DBSCAN epsilon/minimum points, representative points,
   noise, convex hull yang tidak degenerat, grid resolution, occupied-cell density,
   heatmap MapLibre, kategori, statistik dan jadual.
3. **Network Accessibility** — OSRM Table sebenar sehingga 5 origins × 5 destinations,
   distance/time matrix, unreachable pairs, fastest supplied destination,
   skor travel-time telus, titik rujukan dan pautan ke Phase 3 road planner.
4. **Industrial Accessibility** — perbandingan 1–6 kawasan, radius sama,
   industrial/land-use counts, density, mapped road segment counts serta proximity
   geography ke warehouse, port, airport dan logistics hub.
5. **Saved Analyses / Analytics & Reports** — senarai berhalaman, open, map layers,
   export, save/reload, delete dengan confirmation dan undo archive.
6. **Saved Route History** — lapan route Phase 3 boleh dibuka, dilapis dan
   dibandingkan (km/minit), dieksport, diarchive dengan confirmation dan dipulihkan.

Input boleh datang daripada query kategori PostGIS bbox/radius, sehingga 200 ID
dipilih serentak daripada preview, sketch point/line/polygon yang disiapkan,
atau analysis layer tersimpan. Input A dan B boleh berbeza.
Preview 100/page, query keseluruhan sehingga 2,000 objek tanpa silent truncation.
Borang mempunyai carian nama eksplisit, bbox, pusat/radius, kategori dan parameter.

Workspace memaparkan sehingga lima result layers dengan visibility, warna,
zoom, pemilihan feature, input context, statistik, source/method/parameter/time,
chart, jadual berhalaman 100, GeoJSON dan CSV. Layers bertahan semasa navigation,
tetapi browser reload membersihkan state memori; saved records kekal dalam DB.

## Senario A–J: keputusan sebenar

[phase4-scenarios.json](phase4-scenarios.json) mengandungi input, statistik,
result counts, sumber, ID tersimpan dan checks. Eksport:
[data/exports/analyses](../data/exports/analyses).

| Senario | Status | Hasil sebenar |
| --- | --- | --- |
| A: industrial dalam 10 km Tanjong Malim | Passed | 1 objek kategori industrial; buffer + match = 2 geometri |
| B: warehouse Shah Alam, buffer 5 km | Passed | 70 objek industrial berpadanan; 71 geometri hasil |
| C: clip industrial land-use kepada Klang boundary pengguna | Passed | 92 geometri sah; jumlah area output 34.176870 km² |
| D: nearest warehouse kepada Canpac | Passed | Jun Hong Trading; 537.625 m separation geografi |
| E: density Rawang vs Shah Alam, 5 km | Passed | 24 vs 270 objek industrial/land-use; 0.305608 vs 3.438092 objek/km² |
| F: network accessibility ke Port Klang | Passed | Canpac 54,478.8 m / 2,905.3 s; warehouse Pharmaniaga 20,530.2 m / 1,193.3 s |
| G: intersection dan export | Passed | 33 geometri sah; 9.683622 km² summed output area |
| H: save/reload Supabase | Passed | Geometri/statistik sama selepas reload; save idempotent |
| I: buka route Phase 3 | Passed | LineString sebenar dan jarak/masa asal dibaca semula |
| J: network isochrone | **Unsupported** | OSRM semasa tiada isochrone; HTTP 501; tiada polygon rekaan |

Warehouse B ialah **Syarikat Farmaseutikal Pharmaniaga Logistics Sdn Bhd**,
OSM way/1495868943, ID 030efbe3-8d74-545d-90e0-15df09508265.
Buffer dibuat daripada polygon warehouse sebenar, jadi area 80.693685 km²
merangkumi footprint + buffer, bukan sekadar πr². Padanan menggunakan intersects.
Input warehouse boleh mengira dirinya apabila ia juga mempunyai kategori industrial.

Tambahan tujuh operasi atas data sebenar semuanya passed: DBSCAN, grid, dissolve,
union, difference (hasil kosong yang sah), spatial join dan polygon aggregation.
DBSCAN pada 85 objek Shah Alam, radius query 10 km, eps 1,000 m/minimum 3:
**6 cluster, 83 clustered, 2 noise**. Grid 1,000 m:
**30 occupied cells**, 85 representative points, 115 output features.
Hulls ialah descriptive convex hulls, bukan sempadan industri berkuasa.

## Enam kawasan awal

Perbandingan semua enam rujukan dilaksanakan secara berasingan:
[phase4-region-comparison.geojson](phase4-region-comparison.geojson).
Kategori industrial + industrial land-use/parks; radius 5 km; kiraan ID unik
daripada geometri yang intersects radius. Category memberships boleh bertindih.

| Rujukan query | Objek | Objek/km² |
| --- | ---: | ---: |
| Tanjong Malim | 7 | 0.089136 |
| Rawang | 24 | 0.305608 |
| Shah Alam | 270 | 3.438092 |
| Bukit Raja | 67 | 0.853156 |
| Klang | 46 | 0.585749 |
| Port Klang | 87 | 1.107830 |

Rujukan ialah hasil geocoder yang direkod penuh dalam output, **bukan gate atau
sempadan park disahkan**. Bukit Raja dipadankan kepada reference pada North Klang
Straits Bypass; pengguna boleh menggantikan pusat dengan koordinat tepat.
Tanjong Malim tidak dianggap sebagai pintu AHTV. Angka A berbeza daripada baris
Tanjong di atas kerana A menapis industrial sahaja dan radiusnya 10 km.
Tiada dakwaan aktiviti ekonomi atau inventori nasional lengkap dibuat.

## Metodologi spatial dan network

Query awal menggunakan parameterized SQLAlchemy/PostGIS ST_Intersects dan geography
ST_DWithin. Radius filtering menggunakan meter, bukan degree. DB nearest proximity
dalam region comparison menggunakan geography ST_Distance.

Overlay/joins/buffer/density menggunakan GEOS/Shapely dalam **WGS84 local azimuthal
equidistant CRS (meter)** yang dibina daripada extent input melalui PyProj.
Input dibatasi kepada 250 km dari pusat projection dalam study region Malaysia.
Output ditransformasi semula EPSG:4326 dan diperiksa valid/empty/complexity.
Area dan reported nearest separation menggunakan WGS84 Geod; ring holes
dinormalisasi sebelum pengiraan area. Nearest ranking menggunakan projected
footprint distance, dengan reported geodesic separation; bukan road distance.
Perbezaan projection kecil boleh mempengaruhi near-ties pada extent besar.

Intersection mengekalkan pasangan ID/sumber; clip menggunakan polygon-only mask
dan dissolve mask. Empty hasil dipulangkan sebagai FeatureCollection kosong.
Mixed GeometryCollections dipecahkan kepada geometry yang boleh dipaparkan.
Area statistik ialah **jumlah area geometri output**, boleh bertindih; bukan
semestinya unique coverage area. Union boleh digunakan untuk unique coverage.

DBSCAN menggunakan exact epsilon neighborhoods dalam CRS meter dengan spatial
hash; minimum points termasuk titik sendiri. Setiap geometri menyumbang satu
PointOnSurface/representative point. Noise = −1; border assignment deterministic
mengikut urutan input. Hull dihasilkan hanya jika polygon area >1 m².
Grid mengira representative points dalam sel meter; density dibahagi area
ellipsoidal sel. Hanya occupied cells dipaparkan; sel tidak dipotong kepada radius.
Heatmap ialah visual kernel concentration MapLibre yang berubah mengikut zoom,
bukan calibrated density raster atau significance test.

Network menggunakan [OSRM Table](https://project-osrm.org/docs/v26.4.0/http).
Metrik distance ialah jarak **laluan terpantas**, bukan jaminan shortest-distance.
Tiada fallback_speed digunakan; response fallback cells ditolak. Null pair kekal
unreachable. Nearest ialah terpantas antara calon dibekalkan sahaja.
Skor = 100 / (1 + minutes/reference), default reference 60 min; unreachable = 0.
Ini heuristic travel time, bukan MCDA/kelayakan pelaburan atau verified truck access.

Polisi [FOSSGIS](https://routing.openstreetmap.de/about.html) dan safeguard Phase 3
dikekalkan: satu request, ≥1.1 s spacing, 12 upstream/min, timeout, cooldown,
cache 24 jam. Matrix menyokong car sahaja dan tidak mencipta geometri jalan.
Gunakan Inspect pair in road planner untuk geometri Phase 3 sebenar.

## API baharu

| Method | Endpoint | Fungsi |
| --- | --- | --- |
| POST | /api/spatial/analyze | Allowlisted geometry operations, strict input/CRS/limits |
| POST | /api/analysis/regions | 1–6 comparable radius windows + geography proximity |
| POST | /api/routing/matrix | Real OSRM road distance/time, nearest and heuristic score |
| GET | /api/network/capabilities | Matrix/isochrone capability and explicit limitation |
| POST | /api/network/isochrone | 501 unsupported, no generated polygon |
| POST | /api/analysis/saved | Save validated server calculation ID |
| GET | /api/history/analyses or /routes | Metadata-only SQL pagination, 25/page default |
| GET | /api/history/{kind}/{uuid} | Reload full saved geometry/provenance |
| POST | /api/history/{kind}/{uuid}/archive | confirmed:true required, reversible soft delete |
| POST | /api/history/{kind}/{uuid}/restore | Restore archived record |

OpenAPI: [openapi.json](openapi.json). Contoh kontrak: [API.md](API.md).
Endpoint analisis/history/matrix memerlukan PostGIS, enabled local workspace,
loopback client, allowed Host dan Origin. Tiada SQL/Python/command execution API.
Jangan expose API ini sebagai public authenticated production service tanpa
kerja identity/grants/shared quota yang diperlukan.

## Database dan integriti

**Tiada migrasi/schema destructive atau schema baru.** analysis_jobs,
analysis_results dan routing_references sedia ada digunakan.
AnalysisResult menyimpan full result/provenance dalam JSONB dan spatially indexed
GeometryCollection EPSG:4326. Save UUID5 idempotent; save semula memulihkan analysis
yang diarchive. Delete menambah archived_at dalam metadata, bukan memadam row.
UI menawarkan confirmation/cancel dan Undo last deletion. Restore/save route
mengekalkan geometri asal. Jadual feature OSM tidak diubah oleh analisis.

Tujuh analisis sebenar disimpan untuk semakan (termasuk buffer, clip, matrix,
DBSCAN, grid dan perbandingan kawasan; dua run clip berlainan timestamp).
5,234 objek OSM kekal, 0 synthetic/invalid. Lapan route Phase 3 asal kekal
(ID dan geometri sepadan tepat dengan lapan snapshot Phase 3), tiada route asal
diarchive dalam ujian browser.
PostGIS 3.3.7 + SSL, revision 0001_foundation, 12 tables/RLS, 4 geometry/GiST
disahkan semula. Lihat [database verification](phase4-database-verification.json).
Live integration tests bagi save/archive/restore menggunakan rollback.

## Ujian dan bukti pelayar

- **138 backend passed**, termasuk **9 live Supabase tests**, 0 failed/skipped.
- **42 frontend passed**, 10 fail, 0 failed/skipped.
- TypeScript + production Vite build passed. pip check: tiada broken requirements.
- Point/line/polygon buffer, holes area, invalid input/CRS, empty overlays,
  join/aggregation/nearest, DBSCAN/noise, grid conservation, matrix null/error/
  fallback rejection/cache, local access dan archive confirmation diuji.
- Live DB save/reload/idempotency/archive/restore rollback dan route history passed.
- Runtime tambahan: empty query jujur, >2,000 road objects ditolak tanpa partial
  analysis, bowtie polygon 422, unsupported isochrone 501, API/proxy readiness passed.
- Regression Phase 1–3 lulus. Amaran sedia ada: Starlette/httpx deprecation dan
  chunk MapLibre >500 kB; bukan kegagalan build.

Reports: [backend JUnit](phase4-backend-tests.xml),
[frontend JSON](phase4-frontend-tests.json),
[secret scan](phase4-secret-scan.json).

Browser sebenar terhadap production preview 4173/API8000:
warehouse ID dipilih daripada query, buffer 5 km menghasilkan 70 matches;
save, reload selepas browser refresh, actual GeoJSON/CSV download dibaca semula;
Phase 3 history dibuka dan dua route dibandingkan, delete confirmation dibatalkan;
matrix Canpac→Port Klang 54.48 km/48.42 min disimpan; DBSCAN/grid/heatmap dipaparkan;
layer visibility dan pemilihan feature hasil berfungsi. Perbandingan enam kawasan
juga dijalankan/export/save/reload melalui UI; semua kolum proximity tersedia. Tiada console error/warning
baharu semasa semakan akhir. Ini manual UI verification, bukan dakwaan suite E2E.

- [Reloaded warehouse buffer](phase4-buffer.png)
- [Six-region comparison](phase4-regions.png)
- [Browser region export](phase4-browser-regions.geojson)
- [Cluster map](phase4-clusters.png)
- [Density grid](phase4-grid.png)
- [Heatmap](phase4-heatmap.png)
- [Network / saved route comparison](phase4-network.png)
- [Buffer GeoJSON download](phase4-browser-buffer.geojson)
- [CSV download: 70 rows](phase4-browser-buffer.csv)
- [Browser checks](phase4-browser-checks.json)

## Performance, coverage dan kerja selepas review

Query maksimum 2,000 objek/input, selected IDs 200, inline 200, output 4,000
geometri/200,000 vertices/8 MB, join 10,000 pairs, buffer ≤50 km. SQL statement
timeout 20 s; best-effort geometry/DBSCAN budget 20 s dengan had input. Satu
geoprocessing request serentak. Cache analysis/matrix 24 jam, sehingga 64 fail
setiap jenis; UI maksimum lima layers. Request browser boleh dibatalkan;
kerja server yang telah bermula boleh selesai dan dicache. Tiada durable worker
queue atau distributed cancellation/quota. Saved history hanya mengambil
metadata melalui SQL; full geometry dimuatkan apabila Open.

GiST geometry sedia ada digunakan untuk bbox; geography radius casts belum
mempunyai expression index khusus. Query-plan/capacity review diperlukan untuk
national-scale data. Pipeline terhad sengaja menolak input besar, bukannya
menghasilkan statistik daripada subset tersembunyi.

Coverage hanya dataset OSM yang telah diimport, tertumpu koridor yang disahkan
Phase 2; bukan seluruh Malaysia. Objek OSM berlainan boleh mewakili kemudahan sama.
Kategori bertindih. Kategori port boleh merangkumi harbour/marina seperti Royal Yacht Club; ia tidak membuktikan freight/cargo capability. Unknown gates/status/capacity/land legality kekal unknown.
Grid, hull dan buffer ialah hasil matematik, bukan industrial boundary atau
network service area. Isochrone kekal unsupported.

Sebelum Phase 5: semak hasil ini, sahkan origin/gates sebenar bagi kajian operasi,
pilih provider production/verified truck profile jika perlu, identity/writer
roles/shared quotas/monitoring/capacity. OR-Tools VRP/MCDA/GeoAI tidak dibina
dalam fasa ini. **Berhenti selepas Fasa 4.**
