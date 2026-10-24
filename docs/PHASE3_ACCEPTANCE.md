# Fasa 3 — Freight Route Planner: sedia untuk semakan

24 Oktober 2026, Asia/Kuala_Lumpur. Skop Fasa 3 sahaja.
React/MapLibre dan FastAPI berjalan setempat; Supabase PostGIS digunakan.
Tiada Docker, deployment awam, akaun berbayar atau Fasa 4 dimulakan.

## Hasil yang berfungsi

- Adapter RoutingProvider dengan implementasi OSRM-compatible dan mod disabled.
  URL, profil OSRM, label provider dan polisi boleh dikonfigurasi backend.
- Carian tempat Malaysia secara submit, koordinat longitude,latitude atau klik peta.
  Kemudahan GIS sebenar boleh dipilih dalam planner atau melalui inspector.
- Origin, destination dan sehingga enam hentian perantaraan; susun semula,
  padam dan reverse. Susunan dikekalkan; ini bukan pengoptimuman hentian.
- LineString rangkaian jalan asal provider, jarak meter, masa saat, leg dan snap.
  Marker A/1/2/B, highlight route, alternatif, perbandingan dan fit map.
- Eksport route dipilih atau semua alternatif ke GeoJSON EPSG:4326, termasuk
  titik diminta/titik snap, metrik, masa retrieval, sumber dan batasan.
- Simpan hasil server yang disahkan ke routing_references dalam PostGIS.
  Geometri arbitrari daripada browser tidak diterima; simpanan berulang idempotent.
- Gudang terdekat menggunakan ST_Distance geography antara geometri sebenar.
  Ia **terdekat secara geografi**, bukan ranking jarak memandu. Laluan jalan
  dikira berasingan selepas gudang dipilih.
- Loading/cancel/error/empty states, stale-response guards, timeout dan cooldown.
  Tiada garis lurus atau data sintetik menggantikan kegagalan routing.

## Senario provider sebenar

Angka ialah hasil provider pada masa retrieval, bukan pengukuran perjalanan lori.
Butiran, koordinat sumber, snap, masa dan pemeriksaan setiap senario tersedia di
[phase3-routing-scenarios.json](phase3-routing-scenarios.json).

| Senario | km jalan | minit anggaran car | Vertex LineString | Alternatif tambahan |
| --- | ---: | ---: | ---: | ---: |
| Rujukan bandar Tanjong Malim → bandar Port Klang | 99.0073 | 79.30 | 1,111 | 1 |
| Rawang → Shah Alam | 39.0660 | 33.65 | 637 | 0 |
| Shah Alam → KLIA Terminal 1 Main Building | 49.2668 | 45.33 | 511 | 0 |
| Canpac Sdn. Bhd. → Jun Hong Trading | 0.8654 | 1.75 | 13 | 0 |
| Jun Hong Trading → bandar Port Klang | 54.7692 | 49.38 | 681 | 1 |
| Tanjong Malim → Rawang → Shah Alam → Port Klang | 110.2267 | 92.57 | 1,559 | 0 |
| Jun Hong Trading → objek pelabuhan OSM diimport | 56.0895 | 53.01 | 709 | 1 |

**7/7 lulus**: geometri sah, lebih dua vertex, metrik positif, jumlah leg betul,
panjang geodesik selaras dengan metrik provider, snap dalam had, profil car jujur,
save PostGIS, cache dan idempotency. 8 row route disimpan (7 senario primer +
1 alternatif dipilih melalui browser); semua geometry/metrik/provenance sah. Eksport setiap senario:
[data/exports/routes](../data/exports/routes).

Tanjong Malim ialah rujukan bandar daripada Nominatim, **bukan pintu atau
sempadan AHTV yang disahkan**. Port Klang town juga bukan terminal/pintu
pelabuhan. Ujian tambahan menggunakan feature pelabuhan sebenar secara berasingan.
KLIA menggunakan objek bangunan Terminal 1; ini tidak mengesahkan akses kargo.
Canpac dan Jun Hong menggunakan feature OSM yang telah diimport.
Jarak geografi Canpac–gudang terpilih ialah 537.625 m; laluan jalan 865.4 m.

## Quality gate dilaksanakan

- **111/111 backend lulus**, termasuk **7 ujian live Supabase**; tiada gagal/skipped.
  Ini termasuk 32 ujian routing, kontrak API, geometri/metrik/snap, kegagalan
  provider, kadar/cooldown, cache, local-only, save dan rollback DB.
- **31/31 frontend lulus** dalam 7 fail: planner, store, serialisasi/export,
  alternatif, error tanpa fallback, stale calculation/save/nearest responses,
  MapLibre route layers dan persistence sketch apabila bertukar modul.
- TypeScript `npm.cmd run typecheck`: lulus.
- Production `npm.cmd run build`: lulus. Amaran saiz chunk MapLibre masih ada.
- Backend masih mempunyai satu amaran deprecation Starlette/httpx upstream;
  ia tidak disembunyikan dan ujian lulus.
- Tiada dependency baru diperlukan. `pip check`: No broken requirements found.
  Pemeriksaan rahsia akhir tiada padanan di luar .env; fail ignored/untracked.
- Skema 0001_foundation digunakan tanpa migrasi baharu. Rekod OSM kekal 5,234;
  tiada feature sintetik ditambah. Jadual/geometry/index/RLS disahkan semula.

Bukti mesin: [backend JUnit](phase3-backend-tests.xml),
[frontend JSON](phase3-frontend-tests.json),
[verifikasi database](phase3-database-verification.json).

## Pengesahan pelayar sebenar

Dalam in-app browser terhadap production preview 4173 dan API 8000:

- Carian nama Tanjong Malim/Port Klang, dua alternatif, pemilihan route 2.
- Paparan line rangkaian jalan dan marker, fit map.
- GeoJSON route 2 benar-benar dimuat turun dan dibaca semula: 99,421.1 m,
  4,931.8 s, 1,379 vertex; geometri, CRS dan provenance kekal.
  Salinan: [eksport pelayar](phase3-browser-route-export.geojson).
  [Eksport semua alternatif](phase3-browser-route-comparison.geojson) mengandungi
  2 LineString + 4 requested/snapped points; diperiksa selepas download.
- Save selected route ke PostGIS; row disemak pada database.
- Klik peta menggantikan origin dan membatalkan hasil lama.
- Imported GIS: Canpac dipilih, helper memilih Jun Hong Trading,
  kemudian hasil jalan 0.87 km / 2 min dipaparkan.
- Dua hentian tambahan Rawang/Shah Alam: empat waypoint, tiga leg,
  110.23 km / 1 h 33 min. Tiada alternatif rekaan.
- MapLibre worker rasmi dan fungsi Phase 1/2 dikekalkan. Font marker diselaraskan
  kepada Noto Sans Regular yang dibekalkan basemap.
- API/proxy health, ready dan provider: 6/6 HTTP 200. Tiada console warning/error
  baharu selepas reload binaan akhir. Basemap Minimal→Light mengekalkan route.
- Bukti visual akhir: [phase3-preview.png](phase3-preview.png),
  [perbandingan/simpanan](phase3-route-comparison.png),
  [peta empat hentian](phase3-multistop-map.png),
  [ringkasan empat hentian](phase3-multistop-summary.png).
  Semakan terstruktur: [phase3-browser-checks.json](phase3-browser-checks.json).
  Semakan pelayar ialah manual berasaskan UI sebenar, bukan dakwaan suite E2E automatik.

## Safeguard dan had yang masih wujud

Provider default [FOSSGIS](https://routing.openstreetmap.de/about.html),
[protokol OSRM](https://project-osrm.org/docs/v26.4.0/http/).
Atribusi OSRM/FOSSGIS/© OpenStreetMap contributors dan pautan Fix the map
ditunjukkan. HTTPS dan OS trusted CA digunakan.

- **Profil standard car sahaja.** Tiada pengesahan lori, height/weight/hazmat,
  live traffic, loading, customs, break atau legal road access.
- Geometri footprint/PointOnSurface dan geocoder bukan pintu masuk disahkan;
  semak snap. Provider boleh memilih jalan yang tidak sesuai untuk operasi lori.
- Alternatif bergantung pada provider; dua-point sahaja diminta. Multi-stop
  mengekalkan urutan, tanpa alternatif atau pengoptimuman.
- Public demo tiada SLA/kapasiti production. Minimum 1.1 s antara request,
  maksimum 12 upstream/minit, satu request serentak, cache 24 jam/128 fail.
  HTTP timeout 20 s/connect 8 s, respons maksimum 8 MiB; tiada retry automatik.
  429/503/504 mencetuskan cooldown sekurang-kurangnya 60 s.
- Maksimum 8 titik, snap 25–2,000 m, chain geodesik 3,000 km, 50,000 vertex/route.
- Cache/locks/quota setempat dan satu proses. Endpoint routing terhad loopback,
  Host/Origin dibenarkan. Render template mematikan discovery dan routing.
- Pelan dalam browser bertahan semasa bertukar modul, tetapi reload membersihkan
  state memori. Eksport atau save sebelum reload; UI sejarah/load saved routes
  belum dibina. Saved rows/provenance kekal dalam Supabase.
- Production masih memerlukan autentikasi, peranan DB sesuai, shared quotas,
  provider berlesen/berkapasiti dan operational monitoring.
- OSM coverage bukan inventori lengkap. Tiada kapasiti gudang, gate AHTV,
  status operasi atau sempadan berkuasa direka.

## Fail dan arahan

Backend: app/schemas/routing.py, app/routing/providers.py, app/routing/service.py,
app/api/routing.py, settings/main, tests/test_routing.py, live DB tests,
verify_phase3.py. Frontend: FreightRoutePlanner, routing service/types/store,
MapWorkspace, Inspector, navigation/App, workspace sketch store, routing.css
dan regression tests. Config: Vite routing proxy, backend/.env.example,
render.yaml. Dokumentasi API/architecture/development/deployment/progress dikemas kini.

```powershell
# Dari backend
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
.\.venv\Scripts\python.exe -m pytest -q --tb=no --basetemp=.cache/pytest-phase3-final --junitxml=../docs/phase3-backend-tests.xml
# API mesti berjalan sebelum senario live; melakukan request terhad + save:
.\.venv\Scripts\python.exe verify_phase3.py
# Dari frontend
npm.cmd test -- --reporter=dot --reporter=json --outputFile=../docs/phase3-frontend-tests.json
npm.cmd run typecheck
npm.cmd run build
```

Kesilapan yang ditemui dan dibaiki: cast WKB→geography dalam nearest warehouse
diganti scalar geometry subquery PostGIS; font marker yang tiada di basemap
diganti font sebenar; scroll map picking diperbetul; balasan async lama tidak
lagi mengubah hasil/pilihan semasa; sketch siap kekal apabila map bertukar modul.
Tiada kegagalan ujian akhir. **Fasa 3 sedia untuk semakan tempatan. Fasa 4 ditangguhkan.**
