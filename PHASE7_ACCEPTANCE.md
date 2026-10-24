# Phase 7 — GeoAI Copilot: penerimaan pembangunan

24 Oktober 2026. **Pembangunan bagi skop tempatan yang dihadkan siap; ujian automatik/API/DB lulus.
Penerimaan visual browser masih pending.** Phase5 dan Phase6 browser acceptance kekal pending.
Phase8 tidak dimulakan. Tiada deployment awam, Docker atau servis AI berbayar diaktifkan.

## Modul siap

- Ruang GeoAI dalam aplikasi React sedia ada: chat Melayu/Inggeris, contoh arahan, mode selector,
  explicit feature/scenario/MCDA context, sejarah memori, progress/cancel, result tables/cards/charts.
- MapLibre menggunakan geometri asal daripada alat: point/line/polygon/buffer/DBSCAN/MCDA/vehicle routes;
  legends, lapisan warna berasingan, show/hide, fit, linked map/table/chat selection dan gold highlights.
  Arahan “show only” menyembunyikan lapisan hasil terdahulu, tanpa memadam sejarah.
- 23 alat typed/allowlisted mengguna servis Phase1–6. Carian berbilang kategori melaporkan semua
  category counts, source coverage dan pagination; selected-feature radius menggunakan footprint
  geodesic sebenar, town radius menggunakan reference yang diketahui.
- Multi-intent search→road matrix→rank; multi-turn follow-up→filter→GeoJSON export.
- MCDA read/re-score/explain/sensitivity menggunakan raw-value snapshot asal; tidak menulis semula Phase6.
- Pengoptimuman senario tersimpan dan perbandingan fleet selepas preview/confirm. Pengiraan dalam
  memori; shipping demand/capacity/cost ialah andaian hypothetical/user-supplied, bukan fakta perniagaan.
- Simpan snapshot perbualan secara explicit dengan confirmation, history berhalaman dan reload
  ke session ID baharu. GeoJSON dan CSV mengekalkan identiti/geometri, metodologi dan atribusi.

## Status LLM sebenar

**Provider disabled; tiada credential LLM sah dikonfigurasi. Tiada live model call dibuat.**
Default ialah deterministic GIS command mode dengan grammar terhad; bukan full LLM intelligence.
Soalan kabur, tempat tidak dikenali, radius hilang atau parameter penghantaran tiada meminta penjelasan.

Adapter pilihan backend `openai_compatible` menggunakan function-tool Chat Completions contract,
HTTPS base URL/model/key melalui environment backend. Ia boleh digunakan oleh provider serasi,
namun bukan jaminan semua model/protokol disokong. Semua calls divalidasi; prose/reasoning model
langsung tidak diterima sebagai jawapan fakta. Penjelasan angka datang daripada output alat sahaja.
Satu planning request/turn, max1200 completion tokens, <=6 tool calls,25s default timeout,
100KB response cap dan30 provider requests/hour/process. Provider errors/missing key diuji;
kejayaan live LLM belum disahkan dan kekal sebagai batasan.

## Fresh tests — bukan rekod fasa lama

| Semakan | Hasil |
| --- | --- |
| Backend penuh | **288 passed;0 failed/errors/skipped**, 73.10s; termasuk **17 live PostGIS tests** |
| Frontend penuh | **89 passed;0 failed/pending**, 18 fail ujian |
| TypeScript | Lulus |
| Production build | Lulus; index509.80KB / MapLibre941.19KB chunk warning bukan kegagalan |
| pip check | No broken requirements |
| Map styles | Installed MapLibre style validator; highlight/top geometry dan visibility lulus dalam component tests |
| Live GeoAI HTTP | 23 langkah; tiada langkah gagal; clarification/pending-confirmation dibezakan daripada completed |
| Export sebenar | Frontend functions headless:3 geometri asal/3CSVrows/1visible layer; bukan browser download test |
| Browser | **0 ujian browser lulus**; local access disabled dalam Work settings |

Empat upstream Starlette/httpx/SWIG deprecation warnings kekal. Kegagalan awal parser MCDA,
stale future-module assertions dan TypeScript telah dibaiki sebelum keputusan akhir ini.

## Senario sebenar A–O

| Senario | Hasil sebenar |
| --- | --- |
| A gudang Shah Alam10km | **Lulus:**21 mapped warehouses; semuanya dipulangkan |
| B industrial facilities Tanjong Malim10km | **Lulus:**1 objek category industrial; bukan census atau semua industrial parks |
| C Rawang5km berbilang kategori | **Lulus:**15 unique features; warehouse4,industrial10,logistics_hub1 |
| D Tanjong Malim→Port Klang | **Lulus:**2 actual road alternatives; route0 **99,007.3m /4,758s**, route1 99,421.1m/4,931.8s; valid LineStrings |
| E nearest warehouse | **Lulus:**Canpac reference→mapped nearest warehouse **537.6253m** footprint geography distance, bukan road distance |
| E proximity selected industrial feature1km | **Lulus:**2 gudang, ST_DWithin geography dari footprint asal, bukan centroid |
| F Shah Alam clusters5km | **Lulus:**270 mapped input objects;4 descriptive DBSCAN clusters,6 noise,264 clustered;274 output geometries termasuk footprints |
| G akses Rawang/Shah Alam→Port Klang | **Lulus:**Rawang54,916.9m/2,867.2s;Shah Alam18,008.7m/1,008.9s;2reachable pairs |
| H existing logistics scenario | **Preview→confirmed→lulus:**OR-Tools best_found,3vehicles,10/10stops,20demand assigned,0unassigned,18,676m matrix total |
| H fleet2 vs3 | **Lulus:**2vehicles capacity16/demand20→8assigned,2unassigned,15,804.4m;3vehicles capacity24→10assigned,0unassigned,18,676m. Less distance with unserved deliveries is not equivalent service improvement |
| I saved Phase6 MCDA | **Lulus:**12candidates;shah-alam-1 top94.0053916 under saved explicit weights |
| I explain | **Lulus:**stored candidate score/contribution arithmetic, no invented recommendation |
| J changed road_distance_m=0.4 | **Lulus:**renormalized roadweight1/3,2rank changes; top remains shah-alam-1. Saved raw inputs reused, not refreshed |
| K multi-intent + multi-turn | **Lulus:**4warehouses Shah Alam3km→actual road matrix→top3→show only3→GeoJSON3 original geometries |
| L invalid/ambiguous/unsupported | **Expected clarification/rejection**, not passed spatial analysis; no invented Atlantis/flood/isochrone |
| M missing LLM | **Expected unavailable/clarification**; deterministic mode remains usable; no live LLM success claim |
| N injection | **Expected rejection** before provider/tools; unsafe text replaced in memory transcript |
| O save/reload | **Lulus:**new GeoAI snapshot reload preserves full result/context; pending tokens never replayed |

Semua sumber: imported real OSM (ODbL), existing PostGIS operations dan OSRM-compatible provider.
HTTP verification baharu boleh menggunakan cache24h yang telah divalidasi; returned cached/retrieved_at
metadata dipelihara. Ia bukan dakwaan setiap request mengambil data baharu dari upstream.
Port Klang ialah town/search reference, bukan terminal/gate. Town origins bukan industrial entrances.
Airport criterion dalam saved MCDA ialah Subang reference, bukan KLIA. Routing ialah **car profile,
not truck verified**, fastest-path estimate bukan shortest-distance/traffic/toll guarantee.

## Keselamatan dan integriti DB

Migrasi **0004_geoai** disemak sebagai SQL offline:dua CREATE TABLE,dua RLS/revokePUBLIC,
tiada DROP/DELETE/old-table alteration. Applied transaction/advisory-lock verification:
**26tables/RLS,8geometry columns/GiST,SSL dan PostGIS3.3.7**.
Jadual baharu `geoai_sessions` menyimpan explicit conversation snapshots (bukan API keys/reasoning);
`geoai_confirmations` menyimpan action/digest/outcome metadata. Tiada perubahan jadual spatial lama.
Fingerprint semua **24 jadual asal** diperiksa semula dalam phase7-integrity.json; OSM5,234,
8routes,14analyses,27optimization scenarios,25solutions,4comparisons dan3site evaluations kekal.
.env dipelihara, diabaikan Git dan tidak dijejak; credential scan berasingan direkodkan.

Tiada arbitrary SQL/Python/shell/file/HTTP tool. Untrusted feature labels ialah data sahaja dan
render melalui React/textContent. Model menerima soalan/context IDs yang minimum, bukan attributes
penuh/DB secrets. Model-proposed places/IDs mesti datang daripada explicit question/context.
Confirmation tokens rawak, session-bound,5min,one-shot; scenario digest diperiksa semula.
Costly optimization dan snapshot writes memerlukan confirmation. API read-only secara default.

## Had dan kesiapan Phase8

- Grammar terhad kepada documented templates/six reference places atau exact imported UUID;
  radius perlu explicit. Tool form mendedahkan semua schema untuk parameter tepat.
- Tidak semua gabungan arbitrari NL disokong; meminta penjelasan adalah disengajakan.
- Search page<=200; map<=2000features/result; raw result<=4MB; last6results/20messages;
 32active sessions dengan24h idle expiry;12execution requests/minute/two sessions serentak.
- Warehouse road ranking perlu complete first search page<=23candidates; bukan ranking nasional.
- Solver<=12stops,10s/variant,3variants,6vehicles; best_found tidak dianggap proven optimal.
- Cancellation hanya antara alat/provider/solver stages; in-flight work boleh selesai dahulu.
- Saved snapshots<=100/4MB,7day retrieval expiry; audit<=1000. Physical expired rows memerlukan
  operator-reviewed cleanup; tidak dipadam senyap. In-memory context hilang apabila restart.
- Tiada production authentication/user isolation/distributed quotas/job queue. No production claim.
- Flood/zoning/land-cost/legal availability/raster/isochrones tidak direka atau didakwa tersedia.
- Full visual acceptance pending. Phase5/6 browser acceptance pending berasingan.

**Phase7 development-complete untuk bounded local review. Readiness Phase8 bersyarat kepada
manual visual sign-off dan credential/provider verification jika LLM ingin diaktifkan.
Phase8 tidak dimulakan.**

## Evidence

- docs/phase7-backend.xml; docs/phase7-frontend.json
- docs/phase7-live.json; phase7-a…o-result.json; phase7-h-confirmed-result.json; phase7-h-fleet-confirmed-result.json
- docs/phase7-frontend-export.geojson / .csv; phase7-exports.json
- docs/phase7-baseline.json; phase7-integrity.json; phase7-migration.sql; phase7-migration-verification.json
- docs/phase7-browser.json; docs/PHASE7_BROWSER_ACCEPTANCE.md; docs/openapi.json
- docs/PHASE7_REVIEW.md; docs/API.md; DEVELOPMENT.md; PROGRESS.md
