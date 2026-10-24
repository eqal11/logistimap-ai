# Integrasi Supabase — selesai dan disahkan

Tarikh: 24 Oktober 2026 (Asia/Kuala_Lumpur).

Backend LogistiMap AI kini menggunakan Supabase PostgreSQL/PostGIS melalui
Session Pooler. Kata laluan dibaca daripada backend/.env sahaja dan tidak
dipaparkan dalam output, laporan atau kod frontend.

## Keputusan sebenar

| Pemeriksaan | Keputusan |
| --- | --- |
| Sambungan berpengguna | Berjaya |
| SSL | Aktif; sslmode=require dikekalkan |
| Versi PostGIS | 3.3.7 |
| Skema PostGIS | extensions |
| Fungsi spatial | ST_SRID, ST_Distance, ST_IsValid dan ST_Intersects lulus |
| Migrasi semasa | 0002_logistics (foundation + additive Phase 5) |
| Semakan migrasi berulang | already_current; tiada migrasi tambahan |
| Jadual aplikasi | 12 disahkan |
| Kolum geometri | 4 disahkan, semuanya EPSG:4326 |
| Indeks GiST | 4 disahkan aktif dan sah |
| RLS | Diaktifkan pada semua 12 jadual aplikasi |
| Kamus kategori | 9 kategori |
| Rekod kemudahan | 0; import data Fasa 2 belum dimulakan |
| Backend tanpa DB | 53 ujian lulus |
| Backend dengan Supabase sebenar | 4 ujian lulus |
| Frontend | 13 ujian dan pemeriksaan TypeScript lulus |

## Skema spatial

| Jadual | Kolum | Jenis | SRID |
| --- | --- | --- | --- |
| spatial_features | geometry | GEOMETRY | 4326 |
| study_areas | geometry | MULTIPOLYGON | 4326 |
| analysis_results | geometry | GEOMETRY | 4326 |
| routing_references | geometry | LINESTRING | 4326 |

Semakan juga mengesahkan nullable kolum, indeks carian, sejarah migrasi, kategori
dan RLS. Tiada Alembic stamp atau downgrade dijalankan. Migrasi asal disemak
sebelum digunakan dalam satu transaksi dengan advisory lock dan semakan nama
jadual bertindih. Jadual aplikasi lain tidak diubah.

Ujian live membandingkan unit jarak geodesik, menguji pembacaan repositori sebenar
dan menguji penggabungan pelbagai kategori menggunakan rekod sintetik sementara.
Transaksi dibatalkan melalui rollback dan ketiadaan rekod ujian disahkan selepas
ujian. Tiada rekod sintetik dimasukkan sebagai data sebenar.

## API dan aplikasi tempatan

Backend: http://127.0.0.1:8000
Frontend: http://127.0.0.1:4173/#explorer

Server tempatan telah dimulakan semasa penyerahan ini.

| Endpoint melalui frontend | Status |
| --- | --- |
| / | HTTP 200 |
| /health | HTTP 200; mode=postgis |
| /ready | HTTP 200; database_verified=true, ssl=true |
| /api/industrial/features | HTTP 200; mode=postgis, 0 rekod |

Pertanyaan turut menguji tiga kategori serentak. Tiada fallback fixture digunakan.
Peta asas masih boleh dipaparkan tetapi tiada titik kemudahan sebenar sehingga
data diimport dalam fasa yang dibenarkan kemudian.

## Konfigurasi dan kerahsiaan

- Pemacu sedia ada: psycopg 3.3.6, psycopg-binary 3.3.6, SQLAlchemy 2.0.55.
- SQLAlchemy menggunakan postgresql+psycopg.
- URL dibina dalam memori melalui URL.create; kata laluan tidak perlu dikodkan
  secara manual. DATABASE_URL penuh kekal disokong.
- DATA_MODE dalam backend/.env telah ditukar kepada postgis hanya selepas
  migrasi, semakan skema dan commit berjaya.
- Fail .env diabaikan Git dan tidak dijejaki.
- SQL echo dimatikan, parameter disembunyikan dan ralat diagnostik ditapis.
- Imbasan 84 fail kod/binaan/laporan tidak menemui rahsia di luar .env.
- Peranan login sedia ada dikekalkan; tiada polisi akses awam ditambah.
- sslmode=require memastikan enkripsi. Pengesahan identiti sijil verify-full
  tidak dituntut sebagai diuji; stor CA setempat sebelum ini tidak mempercayai
  rantaian sijil pelayan. Tiada semakan sijil dimatikan dalam ujian tersebut.

Rujukan teknikal:
[Supabase Session Pooler](https://supabase.com/docs/guides/database/connecting-to-postgres),
[SQLAlchemy URL.create](https://docs.sqlalchemy.org/en/20/core/engines.html#creating-urls-programmatically).

## Bukti yang disimpan

- database-verification.json — pengesahan skema sebenar tanpa credentials.
- database-live-tests.xml — empat ujian integrasi berjaya.
- database-offline-tests.xml — 53 ujian backend tanpa credentials.
- PROGRESS.md — rekod arahan, pembetulan dan hasil.

## Pembetulan semasa pengesahan

Percubaan sambungan pertama mengalami ralat operasi sementara; percubaan
seterusnya dan semua pemeriksaan berikutnya berjaya.

Fixture ujian live pada mulanya cuba membaca CORS_ORIGINS sebagai nilai list
daripada argumen konfigurasi mentah. Ia diperbetulkan supaya hanya medan
sambungan database dibaca oleh fixture. Keempat-empat ujian kemudian lulus.
Kod API tidak terjejas oleh masalah fixture tersebut.

Satu amaran deprecation Starlette/HTTPX sedia ada masih muncul dalam pytest,
tanpa kegagalan ujian.

Tiada Docker, deployment awam, akaun baharu atau perkhidmatan berbayar digunakan.
Fasa 2 tidak dimulakan.


## Kemas kini Phase 5
Skema semasa ialah 0002_logistics: 20 jadual, tujuh geometry columns/indeks GiST dan RLS pada semua jadual projek. Rekod pengesahan foundation asal di atas dikekalkan sebagai sejarah. Lihat ../PHASE5_ACCEPTANCE.md dan phase5-final-verification.json untuk bukti semasa dan checksum data lama.
