# Fasa 2 — laporan penerimaan sebenar

24 Oktober 2026 · LogistiMap AI · Windows · Docker tidak digunakan.

**Status: siap untuk semakan pembangunan setempat. Fasa 3 belum dimulakan.**
Ini bukan pengesahan bahawa semua kemudahan industri Malaysia telah dipetakan,
atau bahawa operasi import sudah sesuai didedahkan kepada umum.

## Pelaksanaan

Pelan yang dilaksanakan: semak skema/kod sedia ada → adapter sumber awam dan
polisi → normalisasi geometri/kategori → import transaksi dan deduplikasi →
borang serta paparan peta → ekstraksi sebenar → ujian DB/API/pelayar → laporan.

- Integrasi Overpass sebenar, satu pertanyaan gabungan untuk semua kategori.
- Carian nama Malaysia melalui Nominatim; pilihan padanan pengguna, radius atau bbox.
- Lapan kategori dengan keahlian bertindih dan kiraan sifar/kegagalan yang jelas.
- Import ke datasets, spatial_features, feature_categories, analysis_jobs dan
  analysis_results yang telah wujud. Tiada migrasi baharu diperlukan.
- ID OSM jenis/id dan UUID stabil; refresh tidak menggandakan rekod dan versi
  lama dalam cache tidak menggantikan versi sumber yang lebih baharu.
- Point, LineString, Polygon dan MultiPolygon. Relasi multipolygon dengan
  outer/inner disambung daripada geometri sumber; data tidak lengkap ditolak,
  dikira dan dilaporkan. Tiada sempadan atau centroid rekaan.
- Pertanyaan sebenar PostGIS ST_Intersects dan geography ST_DWithin.
- Peta/eksport memuatkan semua halaman sehingga had keselamatan jelas 10,000 objek.
  Jadual atribut kekal 250 rekod setiap halaman. Lapisan boleh ditukar,
  disusun, dipilih dan dieksport; legenda merangkumi semua kategori aktif.
- Provenans, lesen, versi/masa OSM, masa import dan pautan objek dikekalkan.
- Import berjalan di latar; status/laporan disimpan. Kegagalan DB rollback
  transaksi; kegagalan sumber tidak digantikan dengan data sintetik.
- Cache, satu import pada satu masa, had keluasan/saiz/objek, cooldown dan
  kawalan akses setempat melindungi operasi mahal.

## Liputan yang benar-benar diimport

Enam pertanyaan awal menggunakan **radius 5 km** daripada rujukan lokasi OSM
yang diperoleh melalui geocoder, bukan koordinat rekaan.

| Rujukan kawasan | Objek sah dipulangkan | Rekod baharu | Rekod dikemas kini |
| --- | ---: | ---: | ---: |
| AHTV / Tanjong Malim — rujukan pekan | 234 | 234 | 0 |
| Rawang | 550 | 550 | 0 |
| Shah Alam | 2,099 | 2,099 | 0 |
| Bukit Raja — rujukan Bandar Bukit Raja | 1,228 | 1,179 | 49 |
| Klang — rujukan Bandaraya Klang | 1,577 | 677 | 900 |
| Port Klang — rujukan Pelabuhan Klang | 793 | 494 | 299 |

Kawasan bertindih: jumlah baris jadual ini bukan jumlah unik.
Enam import awal menghasilkan **5,233 objek unik**.
Satu import tambahan **kategori airport sahaja, radius 10 km Shah Alam**,
dijalankan melalui borang pelayar dan menambah satu poligon sebenar:
Lapangan Terbang Sultan Abdul Aziz Shah, OSM relation/16811593.

**Jumlah akhir: 5,234 objek OSM unik.**
Tujuh job selesai, sifar job gagal, sifar geometri ditolak dalam ekstraksi ini.

| Keahlian kategori akhir | Kiraan objek |
| --- | ---: |
| Industrial facilities / tag industrial | 194 |
| Industrial land use / parks | 345 |
| Warehouse | 36 |
| Logistics hub | 2 |
| Port | 3 |
| Airport | 1 |
| Major road | 4,505 |
| Rail infrastructure | 214 |

Keahlian kategori bertindih. Angka ini ialah objek OSM, **bukan bancian bilangan
kilang, gudang beroperasi atau jalan fizikal yang berasingan**.
Road/rail kebanyakannya segmen geometri; beberapa segmen boleh mewakili jalan
yang sama. Way dan relation berlainan boleh bertindih dan dikekalkan bersama
provenansnya. Rawang dan Shah Alam masing-masing mempunyai satu objek logistics_hub;
Tanjong Malim memulangkan sifar warehouse dalam pertanyaan awal.

Geometri akhir: **20 Point, 4,696 LineString, 514 Polygon, 4 MultiPolygon**.
Semua EPSG:4326. Semakan DB: sifar geometri tidak sah, sifar ID sumber berganda,
sifar rekod sintetik. SSL, PostGIS 3.3.7, migrasi 0001_foundation, 12 jadual,
4 kolum geometri, 4 GiST dan 12 tetapan RLS kekal disahkan.

Bukti mesin:

- [Liputan terperinci, koordinat rujukan, masa snapshot dan kategori sifar](phase2-coverage.json)
- [Pengesahan pangkalan data dan HTTP](phase2-database-verification.json)
- [Eksport semua 5,234 objek sebenar](../data/exports/phase2-osm-malaysia.geojson)
- [Eksport lapangan terbang melalui pelayar](phase2-browser-airport-export.geojson)

## Ujian dan pengesahan

- **77/77 ujian backend lulus:** 72 tanpa DB, 5 langsung Supabase.
- Ujian langsung menggunakan transaksi rollback; tiada rekod ujian sintetik kekal.
- Ujian baharu: semua kategori dalam QL, scope terhad, polygon/line/point,
  multipolygon dengan lubang, geometri rosak/tidak lengkap, deduplikasi,
  cache, timeout separa, HTTP 429/cooldown, had 12,000 objek, akses setempat,
  kegagalan geocoder, import berulang dan perlindungan versi.
- **18/18 ujian frontend lulus:** API, pemuatan halaman lengkap, borang penemuan,
  semua lapan kategori, kegagalan/validasi, lapisan/jadual, peta dan navigasi.
- TypeScript dan binaan Vite production lulus; pip check bersih.
- **9/9 semakan penerimaan HTTP/DB lulus**, termasuk empat kategori serentak,
  radius pelabuhan, keputusan kosong tanpa fallback, eksport penuh sah dan
  semua job selesai. health/ready serta API sebenar memberikan HTTP 200.
- Pelayar: peta sebenar 5,000 objek dalam bbox Klang Valley; carian empat kategori
  memaparkan **221/221 objek**. Menyembunyikan kategori lain meninggalkan
  **36 objek warehouse**. Import airport menghasilkan status selesai dan
  satu poligon dengan atribut/ID asal; pemilihan jadual menyorot poligon.
  Halaman jadual 251–500 juga disahkan sementara peta kekal 5,000 objek.
- Muat turun GeoJSON melalui butang aplikasi berjaya. Fail dibaca semula:
  Polygon sah, EPSG:4326, source_id relation/16811593, synthetic=false.
- Eksport pelayar penuh 5,000 objek bbox Klang Valley juga dibaca semula:
  semua ID unik, geometri sah, bukan sintetik, lesen kekal, EPSG:4326 dan
  empat jenis geometri. [Bukti eksport pelayar](phase2-browser-export-checks.json).
- Proxy Vite diuji semula selepas pembaikan socket: lima halaman berturut-turut,
  1,000 objek setiap halaman, HTTP 200 sekitar 2.8–3.1 saat.
  [Bukti proxy](phase2-proxy-checks.json).
- Imbasan 106 fail: tiada kata laluan di luar .env; .env ignored/untracked.
  [Bukti imbasan](phase2-secret-scan.json).
- Paparan pada saiz pelayar sedia ada berfungsi. Kebenaran geolokasi peribadi
  tidak diminta/digunakan dalam ujian ini.

Laporan ujian: [backend XML](phase2-backend-tests.xml),
[frontend JSON](phase2-frontend-tests.json).

Arahan utama yang telah dijalankan, dari folder berkaitan:

```powershell
# backend
./.venv/Scripts/python.exe -m pytest -q --basetemp=.cache/pytest
$env:RUN_SUPABASE_INTEGRATION_TESTS='1'
./.venv/Scripts/python.exe -m pytest -q --tb=no --basetemp=.cache/pytest-final2 --junitxml=../docs/phase2-backend-tests.xml
./.venv/Scripts/python.exe -X utf8 import_study_areas.py --initial-six
./.venv/Scripts/python.exe -X utf8 verify_phase2.py
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log

# frontend
npm.cmd test -- --reporter=default --reporter=json --outputFile=../docs/phase2-frontend-tests.json
npm.cmd run build
```

Kesalahan yang ditemui dan dibaiki: arahan awal ujian dari folder yang salah,
folder sementara Windows tidak boleh ditulis (diganti .cache setempat),
import TypeScript fungsi eksport yang salah, penukaran tuple geometri kepada
array GeoJSON, refresh peta berbilang halaman dan metadata lesen setiap ciri.
Reset socket proxy Vite→Uvicorn juga ditemui semasa hasil besar. Proxy kini
menggunakan upstream keepAlive=false dan timeout terhad; lima halaman serta
paparan penuh 5,000 objek disahkan semula. Ujian frontend/build diulang dan lulus.
Semua quality gate akhir di atas lulus. Amaran sedia ada yang tidak menyekat:
deprecation HTTPX/Starlette test client dan saiz bundle MapLibre ~941 kB.

## Had dan tindakan selepas semakan

- Liputan ini enam kawasan terhad, bukan seluruh Malaysia atau semua POI.
  OSM tidak lengkap; sifar hasil bukan bukti kemudahan tidak wujud.
- Semasa enam carian 5 km awal, semua kategori airport memulangkan sifar.
  Poligon airport hanya datang daripada carian tambahan 10 km yang dinyatakan.
- AHTV ialah sasaran carian menggunakan pekan Tanjong Malim. Tiada sempadan
  rasmi AHTV atau taman industri dicipta/disahkan.
- Poligon landuse=industrial bukan pengesahan nama taman, pemilikan, zon,
  kebenaran pembangunan, kapasiti, harga sewa atau status operasi.
- Major roads hanya motorway/trunk/primary/secondary dan links. Tiada routing,
  sekatan lori, masa perjalanan, isochrone atau pengoptimuman dihasilkan.
- Airport tidak bermaksud kemudahan kargo disahkan. Hub mungkin kurang ditag.
- OSM penghapusan objek belum diselaraskan; refresh mengemas kini objek
  dipulangkan, tanpa memadam rekod secara automatik.
- Had 10 km / bbox 400 km² / 12,000 objek / respons 25 MB adalah disengajakan.
  Pertanyaan melebihi had perlu dikecilkan. Peta/eksport dihadkan 10,000;
  jadual boleh menghalaman rekod selebihnya.
- Job/cache/kunci pembekal direka untuk satu proses setempat. Job tidak disambung
  semula selepas restart; laporan menandakan job terputus. Tiada queue teragih.
- Radius menggunakan geography cast; belum ada indeks ekspresi geography
  tambahan. Ujian prestasi setakat dataset ~5,000 objek, bukan skala nasional.
- Import/geocoder tidak didedahkan kepada umum. Render mematikannya; auth,
  shared quota dan penyedia produksi perlu sebelum akses awam.
- Tiada akaun/servis berbayar, deployment awam atau Docker digunakan.
  Rahsia kekal dalam backend/.env yang diabaikan Git.

## Fail utama

Backend: app/services/osm.py, app/services/discovery.py,
app/api/discovery.py, app/schemas/discovery.py, config/main/features/spatial
yang dikemas kini; import_study_areas.py, verify_phase2.py dan ujian.

Frontend: DiscoveryPanel, adapter discovery, pemuatan map/export lengkap,
App, Inspector, Sidebar, legenda, jenis data, CSS dan ujian.

Dokumentasi: README, DEVELOPMENT, DEPLOYMENT, API, ARCHITECTURE, OpenAPI,
PROGRESS serta bukti liputan/ujian/eksport. Semak Fasa 2 sebelum sebarang Fasa 3.

Sumber rasmi:
[OSM/ODbL](https://www.openstreetmap.org/copyright),
[polisi Nominatim](https://operations.osmfoundation.org/policies/nominatim/),
[had sumber Overpass](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html),
[Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL).
