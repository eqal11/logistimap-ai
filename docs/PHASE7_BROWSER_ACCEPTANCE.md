# Phase 7 — Manual browser acceptance

**Belum dijalankan.** Alat browser memberi “Local browser use is disabled in Work settings”.
Tiada browser/GPU/screenshot/download check ditandakan lulus. Phase5/6 kekal pending.
Buka http://127.0.0.1:4173/#geoai selepas hard refresh (backend8000 berjalan).
API/headless evidence bukan pengganti semakan ini. Jangan reset DB atau jalankan migration.

| ID | Tindakan dan hasil dijangka | Status |
| --- | --- | --- |
| G01 | GeoAI navigation; deterministic/no-credentials label; empty conversation, usable responsive map | Belum diuji |
| G02 | “Cari semua warehouse dalam radius10 km dari Shah Alam.” dengan jarak antara radius dan10;21records, attribution/counts, linked list/table/map | Belum diuji |
| G03 | Rawang5km search warehouse+industrial+logistics hubs;15unique features,4/10/1counts; no category silently omitted | Belum diuji |
| G04 | Klik result row/list/map; golden highlight dan attributes sepadan; Use as input→buffer5km dan nearest warehouse berfungsi | Belum diuji |
| G05 | Route Tanjong Malim→Port Klang; LineString jalan sebenar, metrics dan2alternatives mengikut API; car/not truck label | Belum diuji |
| G06 | DBSCAN Shah Alam5km; actual clusters/noise counts; polygon/point map rendering; legend/toggle/fit/basemap switch | Belum diuji |
| G07 | Multi-intent example Shah Alam3km→Port Klang;4warehouse road metrics;gold outline top3; follow-up “Show only those three on the map.”→hanya3visible; all prior history retained | Belum diuji |
| G08 | “Export them to GeoJSON.” dan Download CSV; fail dimuat turun,3original features/rows,EPSG4326/provenance/car metadata; compare docs/phase7-frontend-export.* | Belum diuji |
| G09 | Pilih saved logistics scenario; Optimize→preview dahulu, tiada solve sehingga Confirm; reject/expiry/replay tidak execute | Belum diuji |
| G10 | Confirm saved scenario solve;3routes/10stops for tested sample, real road geometry, capacity/unassigned/solver status; fleet2vs3 shows2unassigned vs0 | Belum diuji |
| G11 | Pilih saved Phase6 WLC; rank/explain; road_distance_m=0.4→renormalized1/3,2rank changes; saved scenario remains unchanged | Belum diuji |
| G12 | Preview save conversation→Confirm→Saved conversations→Open; history/results/context same, new session ID, no reusable pending token | Belum diuji |
| G13 | Typed tool form strict schema; invalidJSON/extra SQL/tool name/unavailable location rejected. Tool form permits exact parameter control | Belum diuji |
| G14 | LLM mode without key gives explicit unavailable/clarification; no fake model answer; deterministic mode still works | Belum diuji |
| G15 | Unsupported flood/isochrone/ambiguous radius/injection; no layer fabricated. Cancel mid-operation reports cooperative limitation. Provider/network failure gives error/partial status | Belum diuji |
| G16 | Pagination on a large explicit query, Load next page; returned+total+offset visible, no completeness claim; layer controls remain responsive | Belum diuji |
| G17 | Clear map/New conversation; no stale highlights/context; clear scenario selector requires new selection before optimization | Belum diuji |
| G18 | Narrow screen, keyboard focus, dark/light, console; labels/controls/map/table usable; external tile/font issues recorded separately | Belum diuji |
| G19 | Navigate Phases1–6; Explorer, saved routes/analyses, optimization comparison, MCDA snapshots still load. Prior browser pending flags remain pending | Belum diuji |

Use prompts with spaces as shown in the in-app examples. Snapshot counts/timings are measured
from imported data, not census/customer/gate validation. Don't use hypothetical demands for dispatch.
Record date/browser/version/screenshots only after actually performing these checks.
