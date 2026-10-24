# Phase 5 — Senarai semak penerimaan browser manual

Status: **BELUM DIJALANKAN**. Akses browser tempatan melaporkan
“Local browser use is disabled in Work settings”. Tiada browser check/screenshot
ditandakan lulus pada pelengkapan ini. Component tests, MapLibre style validation
dan headless export tests bukan pengganti pengesahan visual browser.

Sasaran binaan: production preview [LogistiMap AI](http://127.0.0.1:4173/#optimization).
Backend berjalan pada 127.0.0.1:8000. Hard refresh selepas membuka preview agar JS terkini dimuat.
Gunakan data sedia ada; tiada import, migrasi, reset atau re-solve diperlukan.

Perbandingan rujukan tersimpan:
**Phase 5 completion · pinned 2 / 3 / 4 vehicle comparison**
ID: `2611752b-e82b-4130-a2e5-2e733dfa4d64`.
Mengandungi tiga scenario hipotesis daripada lokasi OSM sebenar, lapan vehicle routes,
1,192 road vertices dan 44 stop/depot references. Bukan actual business deliveries.
Kos/demand adalah andaian ujian, bukan kadar pasaran atau spesifikasi truck sebenar.

Isi LULUS/GAGAL, browser/version, masa, screenshot atau nama fail muat turun untuk setiap baris.
Jangan mengisi LULUS hanya kerana butang boleh diklik.

| ID | Tindakan tepat | Hasil yang perlu dilihat | Status/bukti |
| --- | --- | --- | --- |
| B01 | Buka preview, hard refresh, buka navigation jika sidebar tersembunyi, pilih Logistics Optimization → Comparison | Tiada application error; banner OSRM car dan truck restrictions unverified dipaparkan | Belum diuji |
| B02 | Di Saved comparison history, klik Open comparison untuk nama rujukan di atas | Tajuk/masa snapshot dan jadual tiga scenario dimuat; legend A/B/C muncul; lapan road routes dipaparkan serentak | Belum diuji |
| B03 | Semak legend dan zoom pada ruas jalan bertindih | A teal, B ungu, C jingga; dash berbeza bagi vehicle, nombor stop berlabel A1/B1/C1 dan arah laluan kelihatan. Line offsets hanyalah display pixels, bukan koordinat baru | Belum diuji |
| B04 | Pastikan tool Select aktif. Klik satu laluan pada peta, kemudian gunakan Inspect B · Vehicle 1 pada legend | Popup mengenal pasti scenario/vehicle; ordered schedule bertukar kepada scenario B dan vehicle tersebut; selected route lebih tebal/terang. Untuk laluan bertindih, legend memilih route yang tepat | Belum diuji |
| B05 | Klik Fit visible solutions dan Fit selected route; pan/zoom selepas itu | Semua geometry yang visible masuk view; selected fit mengikuti geometry road route, tiada garisan depot-to-stop palsu | Belum diuji |
| B06 | Nyah tanda Show scenario B, kemudian muat turun GeoJSON visible comparison | Semua B hilang dari peta; fail mempunyai 33 features: 5 MultiLineString + 28 Point; tiada scenario B; metadata hidden_scenarios merekodkan B | Belum diuji |
| B07 | Tanda semula B. Nyah tanda satu Show A · Vehicle 1; klik Inspect A · Vehicle 1 | Hanya vehicle itu disembunyikan; Inspect memaparkannya semula dan memilihnya. Scenario lain kekal. Nyah tanda semua scenario → map kosong, bukan kembali kepada single solution lama | Belum diuji |
| B08 | Pulihkan semua scenario/routes visible. Klik GeoJSON visible comparison | Fail mempunyai 52 unique feature IDs: 8 MultiLineString + 44 Point; metadata comparison ID sama; scenario/solution IDs, original vehicle IDs, attribution, assumptions dan unassigned dipelihara | Belum diuji |
| B09 | Buka fail GeoJSON dengan text/GIS viewer dan banding dengan docs/phase5-completion-routes.geojson | Koordinat road geometry sama; EPSG:4326; profile car dan heavy_vehicle_verified=false. Display offsets tidak mengubah koordinat eksport | Belum diuji |
| B10 | Klik CSV comparison dan buka CSV | Tiga data rows; matrix metrics dan final_road_summary berasingan; A assigned 8/unassigned 2, B/C assigned 10/unassigned 0. Matrix km 12.4394/18.5191/18.5191; final km 13.4407/19.8853/19.8853 | Belum diuji |
| B11 | Hard refresh seluruh halaman, masuk Comparison, buka semula snapshot yang sama | History datang daripada Supabase; nama, pinned solution IDs, metrics dan geometry sama. Tidak bergantung kepada state memory sebelum refresh | Belum diuji |
| B12 | Buka satu legacy snapshot dalam history | Summary lama boleh dibaca; geometry direkonstruksi pada masa snapshot dengan warning legacy. Tidak menggantikan senyap dengan solve terkini. Jika exact history tiada, HTTP 409 dan mesej nyata; tiada route palsu | Belum diuji |
| B13 | Buka Create comparison from saved solutions; beri nama “Manual acceptance · hypothetical”; pilih dua solved snapshots; Save comparison 2/4 | Snapshot baharu tersimpan/terbuka; list history bertambah satu; tiada routing/solver job baharu. Unsolved choices disabled; maksimum empat; Next/Previous choices berfungsi | Belum diuji |
| B14 | Refresh comparisons; uji paging jika >10 snapshots | Record baharu kekal; paging tidak menggandakan record. Jika ≤10, Next comparisons disabled; tandakan paging besar N/A, bukan lulus secara palsu | Belum diuji |
| B15 | Buka Saved Scenarios → Open result untuk satu scenario; buka matrix cells; kembali ke Comparison tanpa snapshot/ketika geometry gagal | Single-result UI masih berfungsi. Comparison tidak menunjukkan matrix/schedule/geometry single-result yang tidak berkaitan. Ralat retrieval dipaparkan; stored summary kekal | Belum diuji |
| B16 | Uji Results GeoJSON/CSV lama, GIS Explorer feature selection, saved route dan saved analysis open | Fungsi Phase 1–4 dan single-solution Phase 5 tidak mengalami regresi; jangan archive/delete rekod untuk ujian ini | Belum diuji |
| B17 | Uji light/dark theme, basemap switching dan viewport sempit; scroll config panel | Legend, controls, comparison table dan map masih usable; overlay dipulihkan selepas style change; tiada page overflow yang menghalang penggunaan | Belum diuji |
| B18 | Periksa Console/Network semasa langkah di atas | Tiada uncaught React/MapLibre error. Rekod provider tile/font warnings berasingan; jangan menyembunyikan kegagalan overlay sebagai cosmetic warning | Belum diuji |

Nota B03: empat warna scenario A–D ialah teal `#087f80`, ungu `#7955c7`,
jingga `#ce721d` dan biru `#2876bf`. Snapshot rujukan menggunakan A–C sahaja.
Matriks dan laluan datang daripada stored OSRM standard-car solutions; tiada truck verification,
live traffic atau verified tolls. Lebih pendek dengan unassigned stops bukan servis yang setara.

Penerimaan visual penuh memerlukan bukti B01–B18 (atau N/A dengan sebab yang sah).
Tiada keperluan memadam rekod, menukar .env atau menjalankan migrasi.
Print dialog/laporan asal belum diperiksa semula; jika diperlukan, uji butang Print report
dalam Results dan semak preview sebelum menghantar apa-apa kepada printer.
