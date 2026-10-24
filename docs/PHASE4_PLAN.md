# Fasa 4 — pelan pelaksanaan (sedang berjalan)

1. Audit kontrak/skema/ujian dan perlindungan rekod sedia ada.
2. Input analisis terhad: query PostGIS bbox/radius/kategori, ID berbilang,
   sketch GeoJSON EPSG:4326, atau hasil tersimpan; geometri disahkan.
3. Buffer, intersection/clip, union/dissolve/difference, spatial join/aggregation
   dan nearest geodesic; hasil/provenance/statistik/export yang sebenar.
4. DBSCAN dan grid density menggunakan CRS meter tempatan; parameter, noise,
   ringkasan kategori dan perbandingan kawasan; tiada dakwaan ekonomi/statistik.
5. OSRM Table matrix sebenar + comparison/road nearest/scoring telus.
   Isochrone ditanda unsupported kerana OSRM route/table tidak menyediakan
   isochrone dan line OSM diimport bukan graph berarah dengan restriction lengkap.
6. Workspace MapLibre berlapis + borang, selection, jadual, chart, GeoJSON/CSV.
7. Persist/reload/senarai/archive analysis dan sejarah route; delete confirmation
   melaksanakan soft delete boleh dipulihkan, tanpa destructive migration.
8. Ujian unit/API/CRS/DB/frontend/build, senario A–J, browser dan dokumentasi.
9. Semak 5,234 feature + route lama kekal, imbas rahsia, hentikan sebelum Fasa 5.

Tiada dependency/migrasi sistem baharu dirancang. Jadual analysis_jobs,
analysis_results dan routing_references sedia ada akan digunakan dengan metadata
archive. Operasi local-only, had input/output/masa, SQL parameterized, satu proses.
