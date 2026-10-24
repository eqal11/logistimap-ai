# Phase 6 — Manual browser acceptance

**Belum dijalankan.** Alat browser melaporkan “Local browser use is disabled in Work settings”.
Tiada GPU/map/browser-download check ditandakan lulus. Phase 5 browser acceptance kekal pending.

Buka [preview terkini](http://127.0.0.1:4173/#sites), hard refresh, pilih Warehouse Site Selection.
Snapshot rujukan: **Phase 6 · six areas · road-accessibility WLC**
saved ID `af941dc3-18af-476d-9c03-63ff65513576`.
Ia menilai 12 mapped references, bukan tanah tersedia/kelulusan pembangunan.
Airport target ialah **Lapangan Terbang Sultan Abdul Aziz Shah (Subang)**, bukan KLIA.
Port target ialah **Port Klang town reference**, bukan terminal/gate.

Isi LULUS/GAGAL/N/A berserta browser/version, masa dan screenshot/fail sebenar.

| ID | Tindakan | Hasil wajib | Status |
| --- | --- | --- | --- |
| S01 | Buka #sites, hard refresh | Workspace sebenar terbuka; banner no official flood/zoning/land cost dan car not truck-verified kelihatan | Belum diuji |
| S02 | Saved evaluations → Open snapshot WLC di atas | 12 candidates, 5 criteria, weights 20/15/25/25/15%, raw values, ranking dan sensitivity dimuat tanpa query provider baharu | Belum diuji |
| S03 | Fit candidate sites | Semua 12 polygon footprints dan 12 representative markers masuk view; warna score dan rank label kelihatan, bukan raster surface | Belum diuji |
| S04 | Klik polygon/marker dan baris comparison | Candidate asal dipilih; border/marker menonjol; nama, contributions dan raw-evidence panel bertukar betul | Belum diuji |
| S05 | Toggle Show candidate layer off/on; switch basemap/theme | Layer hilang/pulih, tiada stale geometry/uncaught MapLibre error | Belum diuji |
| S06 | GeoJSON suitability / CSV suitability | 12 candidates/rows; polygon geometry tepat seperti docs/phase6-suitability.geojson; weights, definitions, provenance, warnings dan source IDs dipelihara | Belum diuji |
| S07 | Criteria & AHP: ubah satu weight; kembali Results/evaluate | Ranking lama tidak dilabel semasa input berubah; selepas evaluate, weights dinormalisasi dan scores/sensitivity dikira semula | Belum diuji |
| S08 | Tukar AHP, isi upper triangle atau equal judgments, Check AHP consistency | Reciprocal lower triangle auto; CR/λmax/weights nyata. Equal judgments CR≈0; inconsistent judgments ditolak kecuali explicit override | Belum diuji |
| S09 | Pilih Flood hazard | Official dataset unavailable, source user-supplied sahaja. Note tanpa numeric value tidak mencipta nilai sifar. Missing policy reject memberi ralat, bukan score palsu | Belum diuji |
| S10 | Tukar missing policy secara sengaja | Global excluded criteria/candidates dan renormalized weights jelas; tiada imputation. Point parcel area ialah unavailable | Belum diuji |
| S11 | New empty scenario; import data/phase6/hypothetical-reference-points.csv dan polygon.geojson melalui picker | Dua points/satu polygon valid, dilabel hypothetical/user-supplied; tiada OSM facility baharu dicipta | Belum diuji |
| S12 | Add point on map; draw polygon → Finish → Add drawn candidates | Koordinat/geometry mengikut klik/lakaran; calon hypothetical, bukan boundary/peraturan rasmi. Pick dibatalkan bila tab/request bertukar | Belum diuji |
| S13 | Study reference keenam-enam kawasan; Find mapped candidates; name/radius/map bounds dan paging | Imported categories serentak, explicit page limit; kosong bukan bukti tiada fasiliti sebenar. Duplicate mapped ID dan candidate ke-13 ditolak | Belum diuji |
| S14 | Prepare values, pilih polygon, jalankan buffer/intersection/join/nearest/clusters/grid | API sebenar, parameters 5km/eps1000/min3/grid1000 dinyatakan; layer GIS berasingan boleh toggle/export; empty/error dilaporkan nyata | Belum diuji |
| S15 | Evaluate → Save evaluation; refresh → buka semula | Scenario, values, weights, AHP, geometry, rank dan sensitivity sama; previous snapshots kekal | Belum diuji |
| S16 | Pilih target port/airport/network sendiri; evaluate | Target label/representative status jelas; actual OSRM seconds, no Euclidean travel time. Error/unreachable tidak menjadi score sifar secara senyap | Belum diuji |
| S17 | Uji input salah/import >1MB/max8criteria dan request failure | Ralat membantu; tidak kehilangan rekod DB; tiada fake/partial ranking tanpa missing-policy declaration | Belum diuji |
| S18 | Navigasi GIS Explorer, routing, spatial tools, optimization comparison history kemudian kembali | Phases 1–5 berfungsi; saved routes/analyses/scenarios/comparisons kekal; Phase 5 browser sign-off masih berasingan | Belum diuji |
| S19 | Narrow viewport, keyboard focus, light/dark dan Console | Map/config/table/charts usable; controls berlabel; tiada uncaught application/GPU error. Catat external tile/font warnings berasingan | Belum diuji |

Jangan reset database atau menjalankan migrasi untuk checklist ini.
Fail import contoh ialah optional hypothetical references derived from OSM geometry, never default data.
Score/rank ialah relatif kepada set calon dan andaian; ia bukan nasihat pelaburan atau statutory suitability.
