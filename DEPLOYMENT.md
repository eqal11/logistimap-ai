> Phases 2–4 discovery/routing/analytics are implemented locally. Render disables
> DISCOVERY_ENABLED, ROUTING_ENABLED and ANALYTICS_ENABLED. Do not expose these endpoints
> until authentication, shared quotas and provider policy arrangements are ready.
> Imported PostGIS data can still be queried. No public deployment has occurred.

# Deployment preparation (not deployed)

These files prepare eventual deployment. The existing user-configured Supabase
database is connected and verified; local Phases 1–4 are ready for review. No
GitHub remote, Render service, Netlify site or paid hosting was activated.

## 1. GitHub source control

A local Git repository is initialized at the monorepo root. Review source and
.gitignore before creating a repository or committing. Push only after choosing
your GitHub destination. Never add backend/.env, frontend/.env, virtualenv,
node_modules, generated test caches or secrets. No remote URL has been invented.

## 2. Supabase

Use a project you explicitly choose and authorize. Enable PostGIS; obtain the
actual database connection from the Connect panel. Choose direct connection
where networking permits, or the session pooler for an IPv4-only persistent
backend. Migrations need an appropriate migration-owner connection. Do not copy
the anonymous API key into DATABASE_URL. The implementation uses psycopg3,
SSL and public,extensions search_path.

See [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres)
and [PostGIS setup](https://supabase.com/docs/guides/database/extensions/postgis).

## 3. Migrations and reader privileges

Run from backend with the migration-owner DATABASE_URL in a protected environment:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe check_db.py
```

Migrations create 20 tables (12 foundation plus eight additive logistics tables), spatial indexes, category dictionary, RLS and
constraints. It does not ingest or seed facilities. Review database/reader-role.sql
before running once to create the optional NOLOGIN read group and read policies.
Provision the actual login separately, grant this group, and configure the backend
with that restricted login. Grant schema extensions usage when needed. A reader
can query but cannot migrate; use the migration owner only for deliberate schema
changes. Revoke existing anon/authenticated Supabase grants if your project's
default privileges grant access beyond these new policies.

PostGIS queries and migration were verified against the configured Supabase
instance on 2026-10-24; see docs/DATABASE_INTEGRATION.md.
Verify role permissions, index behavior and online migrations in staging before
treating this as a production database integration.

## 4. Render backend

render.yaml is a blueprint preparation file; using it may create billable resources.
Do not apply it until you approve the account, region and plan.

- Runtime: Python 3.12.10, root directory backend.
- Build: pip install -r requirements.lock.txt.
- Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log.
- Health path: /ready (database/migration checks); /health is process liveness.
- DATA_MODE=postgis, DATABASE_URL supplied as a protected secret.
- DATABASE_SSL_MODE=require, or verify-full with properly configured trust.
- CORS_ORIGINS must be a JSON array containing the exact HTTPS frontend origin.
- Auto deployment trigger is off in the preparation blueprint.
- Migrations are deliberately not run automatically at process startup.

NullPool is suitable when the upstream session pooler owns pooling. Test
connection concurrency against the chosen Supabase plan before scaling.
Transaction-pooler prepared-statement behavior is not configured/verified here.
See [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
and [blueprint specification](https://render.com/docs/blueprint-spec).

## 5. Netlify frontend

Use the monorepo's netlify.toml. Base directory frontend, build command
npm run build, publish directory dist, Node 24. Netlify installs npm dependencies
from package-lock.json before building.

Set VITE_API_URL to the backend's actual HTTPS origin and rebuild. The wildcard
SPA rewrite is included. Hash navigation also survives refresh. Security response
headers prevent MIME sniffing, restrict camera/microphone and limit geolocation
to the app origin. Do not place DATABASE_URL, database passwords, LLM keys or
Supabase service credentials into any VITE variable.

See [Netlify Vite guide](https://docs.netlify.com/build/frameworks/framework-setup-guides/vite/).

## 6. HTTPS and CORS

Use the hosting providers' HTTPS endpoints. Configure backend CORS after the
frontend's final hostname is known, then restart the backend. No wildcard
production origin is enabled. Preview deployments need individually approved
origins; do not permit arbitrary origins to access private data. Geolocation
needs a secure browser context. OpenFreeMap requests are separate HTTPS map
requests, with visible attribution.

## 7. Production boundaries

The local application supports feature queries, measurements, imports and saved
provider routes. Public-provider write/routing operations are loopback-only. It has no
authentication/authorization for application users and is not ready to serve
private datasets publicly. Add identity, dataset-level permissions, a gateway
body-size limit, shared throttling, monitoring, backup policy and capacity
testing during production readiness. The single-process guard is not a shared
production quota. Supabase RLS restricts its Data API but does not authenticate
callers of this FastAPI service.

A production routing provider must have a permitted usage plan; ordinary car
routing must not be described as verified truck routing. GeoAI secrets remain
backend-only and future tool calls must be allowlisted and validated.

## 8. Smoke tests after an authorized deployment

1. Backend /health: 200, expected version/mode, no secret values.
2. Backend /ready: 200 with PostGIS version and expected migration.
3. Frontend loads over HTTPS; the configured API origin is the deployed backend.
4. Empty DB gives an honest empty state; no synthetic fallback.
5. Imported controlled staging features preserve geometry, categories and lineage.
6. Query two or more categories and compare per-category counts.
7. Change extent, inspect point/line/polygon, toggle layers, export GeoJSON.
8. Measure known geometry: equatorial one-degree line is about 111.31949 km.
9. Verify exact-origin CORS and that no database secret is in the frontend assets.
10. Test provider failure, throttling and recovery; check structured backend logs.
11. Test /#settings refresh and mobile layout; check tile attribution.
12. Exercise online migration upgrade and backups in a separate staging DB.

## 9. Common failures

| Symptom | Check |
| --- | --- |
| Render /ready fails | Credentials, SSL, network access, PostGIS, migration revision, reader permissions |
| Tables appear empty | No data imported, RLS reader policies, study extent/category filters |
| Browser CORS error | Exact HTTPS origin, JSON CORS_ORIGINS, backend restart |
| Frontend calls localhost | Set VITE_API_URL at build time, rebuild/redeploy |
| Netlify 404 on navigation | Base/publish directories and SPA rewrite |
| Missing Python wheel | Python 3.12 x64 / compatible Linux host and runtime lock |
| Basemap unavailable | External HTTPS access; choose Minimal for feature-only display |
| High memory/latency | Geometry/query limits, SQL plans, connection limits, production gateway |
| SSL name/CA error | Use actual provider host and correct CA; do not turn off validation |
| Build chunk warning | MapLibre renderer is large; validate real loading budgets before production |

## 10. Delivery status

Local build/start, live Supabase migration/data verification and real bounded
OSM/routing provider tests have occurred. Public hosting, DNS, hosting TLS,
monitoring and deployment smoke tests have not occurred.

Keep ROUTING_ENABLED=false until authentication, role-scoped write permissions,
shared quotas, a production provider contract/capacity plan and privacy review
are complete. Public FOSSGIS demo use here is bounded interactive local research,
not production freight infrastructure. This adapter has no verified truck profile.
A reader-only DB role cannot save routes/import; use a separately reviewed writer
role with appropriate RLS/grants when enabling those operations. Local cache is
ephemeral on typical hosting; saved PostGIS results retain provenance.


## Phase 4 deployment guard

ANALYTICS_ENABLED=false is included in render.yaml. Before enabling anything
public, implement identity and permissions for read/write/history/archive/restore,
writer-role grants/RLS, shared quotas/cache, durable job processing as needed,
request/body/response size gateways and monitoring. Local Host/Origin checks are
not public authentication. Background worker resume and distributed cancellation
are not implemented. The current SQL geometry index is not a geography-expression
index; national-scale radius queries require query-plan review.

Phase 4 writes only existing analysis_jobs/analysis_results and uses JSONB
archived_at for reversible history deletion; there is no migration to deploy.
A reader-only DB login cannot save/archive/restore. No cloud deployment or
production performance claim is made. Real isochrones still require a compatible
provider/validated graph; ordinary car travel remains unverified for heavy vehicles.


## Phase 5 deployment guard
OPTIMIZATION_ENABLED=false is included in render.yaml. Phase 5 is verified locally,
not publicly deployed. Deploy migration 0002_logistics only after reviewing the additive
SQL and taking the normal database backup; it preserves foundation GIS/route/analysis rows.
Do not run a destructive downgrade. See ../PHASE5_ACCEPTANCE.md from docs, or
PHASE5_ACCEPTANCE.md at repository root, for actual migration checks and scope.

Production requires identity/authorization, role-scoped scenario writes, a durable shared
queue, shared rate limits/cache, cancellation/recovery across processes and a routing
provider provisioned for the intended workload. The local single-worker executor is
not a distributed service. Public demo OSRM is not certified truck routing. No paid
or public infrastructure was activated by this implementation.
