Current database integration update: live Supabase/PostGIS has now been verified.
See [DATABASE_INTEGRATION.md](DATABASE_INTEGRATION.md). The original Phase 1
acceptance record below predates that integration.

# Phase 1 acceptance scope

| Capability | Implementation and verification |
| --- | --- |
| Frontend + backend | Actual local HTTP servers exercised; build and tests executed |
| Map | MapLibre/OSM basemap, vector overlays, pan/zoom, scale, coordinates |
| Point/line/polygon | Synthetic fixtures of all three; rendered by real sources/layers |
| Selection | Stable-ID map hit test, highlight, safe DOM popup, table inspector |
| Layers | Toggle and reorder; overlapping category visibility preserved |
| Search | Backend name, multiple categories, bbox/radius, configured study names, coordinates |
| Drawing/measurement | User sketches validated and measured by backend, exportable |
| Attributes/exports | API provenance, nulls as Unknown, page/selection/sketch downloads |
| Dashboard/insights | Counts from query data; overlapping memberships explained |
| Data quality | Persistent synthetic banner and per-record synthetic flags |
| Database | Models, SSL connection, migration and SQL generation; **no live DB verification** |
| Errors/loading | Query states, retry, provider failure, no silent fixture fallback |
| Documentation | Windows startup, configuration, API/OpenAPI, architecture, deployment prep |
| Tests | Pytest backend suite, frontend component/contract/map regression tests |
| Later modules | Explicit unavailable state; no fabricated results |

The Phase 1 deliverable is complete in limited fixture mode. The conditional
PostGIS integration gate remains open until actual credentials are provided.

Not verified in Phase 1: real OSM industrial discovery, online migrations,
live PostGIS queries, actual browser geolocation permission, real routing,
network service areas, buffer/overlay processing, advanced analytics,
optimization, MCDA, uploads, LLM calls, public deployment, authentication or
production capacity. These must not be described as delivered capabilities.
