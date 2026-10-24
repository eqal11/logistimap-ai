import json
from contextlib import asynccontextmanager
import logging
import time
from collections import deque
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.body_limit import OptimizationBodyLimit
from app.db.session import check_database
from app.gis.measure import measure
from app.schemas.spatial import Category, FeatureCollection, MeasurementRequest, SearchParams
from app.services.features import search
from app.api.discovery import router as discovery_router
from app.api.routing import router as routing_router
from app.api.analytics import router as analytics_router
from app.api.optimization import router as optimization_router
from app.api.sites import router as sites_router
from app.api.geoai import router as geoai_router

settings = get_settings()
logger = logging.getLogger("logistimap")
logging.basicConfig(level=logging.INFO, format="%(message)s")
@asynccontextmanager
async def lifespan(application):
    if settings.data_mode=="postgis" and settings.optimization_enabled:
        from app.optimization.repository import recover_interrupted_jobs
        try:
            count=recover_interrupted_jobs()
            if count:logger.info(json.dumps({"event":"optimization_jobs_interrupted","count":count}))
        except Exception:logger.warning(json.dumps({"event":"optimization_job_recovery_unavailable"}))
    yield

app = FastAPI(lifespan=lifespan,title="LogistiMap AI", version="0.7.0", description="Industrial GIS with bounded OSM discovery, PostGIS ingestion and provider-computed road routing with source provenance.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(discovery_router)
app.include_router(routing_router)
app.include_router(analytics_router)
app.include_router(optimization_router)
app.include_router(sites_router)
app.include_router(geoai_router)
app.add_middleware(OptimizationBodyLimit)
requests_by_ip: dict[str, deque] = {}
rate_lock = Lock()


@app.middleware("http")
async def request_context(request: Request, call_next):
    started = time.monotonic()
    request_id = str(uuid4())
    ip = request.client.host if request.client else "unknown"
    with rate_lock:
        # Bounded single-process guard, no trust in user-supplied forwarding headers.
        expired = [key for key, values in requests_by_ip.items() if not values or values[-1] < started - 60]
        for key in expired:
            requests_by_ip.pop(key, None)
        if ip not in requests_by_ip and len(requests_by_ip) >= 10000:
            return JSONResponse(status_code=503, content={"error": {"code": "capacity", "message": "Request guard at capacity."}})
        bucket = requests_by_ip.setdefault(ip, deque())
        while bucket and bucket[0] < started - 60:
            bucket.popleft()
        if len(bucket) >= settings.request_limit_per_minute:
            return JSONResponse(status_code=429, content={"error": {"code": "rate_limited", "message": "Retry after one minute."}}, headers={"Retry-After": "60"})
        bucket.append(started)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    logger.info(json.dumps({"event": "http_request", "request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code, "elapsed_ms": round((time.monotonic() - started) * 1000)}))
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": str(exc.status_code), "message": exc.detail}})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_input", "message": "Request validation failed", "details": [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]}})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "version": "0.7.0", "mode": settings.data_mode,
            "database_configured": settings.database_configured,
            "limitations": ["Phase 1 only", "Synthetic records only"] if settings.data_mode == "fixture" else ["Imported data coverage only"]}


@app.get("/ready", tags=["system"])
def ready():
    if settings.data_mode == "fixture":
        return {"status": "limited", "mode": "fixture", "database_verified": False}
    try:
        return {"status": "ready", "mode": "postgis", **check_database()}
    except Exception:
        raise HTTPException(503, "PostGIS unavailable or schema not migrated. Run the backend connection diagnostic; no fixture fallback.")


@app.get("/api/capabilities", tags=["system"])
def capabilities():
    return {"phase": 7, "available": ["geojson_query", "bbox_filter", "radius_filter", "feature_selection", "geodesic_measurement", "osm_discovery", "place_search", "postgis_ingestion", "import_history", "road_routing", "route_alternatives", "route_export", "saved_routes", "spatial_toolbox", "dbscan", "density_grid", "network_matrix", "analysis_history", "route_history", "logistics_optimization", "scenario_persistence", "optimization_imports", "warehouse_site_selection", "mcda_wlc", "ahp", "sensitivity", "geoai_copilot", "deterministic_gis_commands", "validated_tool_calling"],
            "unavailable": {
                            "isochrones": "Unsupported by configured OSRM provider",
                            "uploads": "Later data ingestion phase"}}


@app.get("/api/industrial/features", response_model=FeatureCollection, tags=["features"])
def features(
    categories: list[Category] = Query(default=[]),
    q: str = Query(default="", max_length=200),
    bbox: str | None = Query(default=None, max_length=160, description="west,south,east,north; EPSG:4326"),
    center: str | None = Query(default=None, max_length=80, description="longitude,latitude; use with radius_km"),
    radius_km: float | None = Query(default=None, gt=0, le=200),
    limit: int = Query(default=250, ge=1, le=1000),
    offset: int = Query(default=0, ge=0, le=100000),
):
    try:
        params = SearchParams(categories=categories, q=q, bbox=tuple(map(float, bbox.split(","))) if bbox else None,
                              center=tuple(map(float, center.split(","))) if center else None,
                              radius_km=radius_km, limit=limit, offset=offset)
    except (ValidationError, ValueError):
        raise HTTPException(422, "Invalid search bounds, coordinates, or radius. Supply EPSG:4326 values; center and radius_km must be paired.")
    try:
        return search(params)
    except (SQLAlchemyError, RuntimeError, OSError, ValidationError):
        logger.error(json.dumps({"event": "feature_provider_failed", "mode": settings.data_mode}))
        raise HTTPException(503, "Feature provider unavailable. Check backend configuration and migrations; no fixture fallback.")


@app.post("/api/spatial/measure", tags=["spatial"])
def spatial_measure(payload: MeasurementRequest):
    return {"data": measure(payload.geometry.model_dump())}

