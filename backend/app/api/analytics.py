from uuid import UUID
from typing import Literal
from fastapi import APIRouter,HTTPException,Request,Query
from sqlalchemy.exc import SQLAlchemyError
from shapely.errors import GEOSException
from app.core.config import get_settings
from app.schemas.analytics import SpatialAnalysis,SaveAnalysis,ArchiveRequest,MatrixRequest
from app.schemas.analytics import RegionComparison
from app.services import analytics,accessibility
from app.gis.analytics import AnalysisError
from app.routing.providers import RoutingError

router=APIRouter(prefix="/api",tags=["phase4 analytics"])
def guard(request):
    s=get_settings()
    if (not s.analytics_enabled or request.client is None or request.client.host not in ("127.0.0.1","::1","testclient") or
        request.headers.get("host","").split(":")[0] not in ("127.0.0.1","localhost","testserver") or
        (request.headers.get("origin") and request.headers["origin"] not in s.cors_origins)):
        raise HTTPException(403,"Spatial analytics are restricted to the enabled local workspace.")
    if s.data_mode!="postgis":raise HTTPException(409,"Live PostGIS mode required; no synthetic fallback.")
def run(fn):
    try:return fn()
    except AnalysisError as e:raise HTTPException(422,str(e))
    except GEOSException:raise HTTPException(422,"Geometry operation could not complete safely; simplify or narrow inputs.")
    except RoutingError as e:raise HTTPException(e.status,str(e))
    except (SQLAlchemyError,OSError,RuntimeError):raise HTTPException(503,"Spatial database/provider/cache operation unavailable; no fabricated result.")
@router.post("/spatial/analyze")
def analyze(request:Request,payload:SpatialAnalysis):
    guard(request);return run(lambda:analytics.run_analysis(payload))
@router.post("/analysis/regions")
def regions(request:Request,payload:RegionComparison):
    guard(request);return run(lambda:accessibility.compare_regions(payload))
@router.post("/routing/matrix")
def matrix(request:Request,payload:MatrixRequest):
    guard(request)
    if not get_settings().routing_enabled:raise HTTPException(503,"Routing disabled")
    return run(lambda:accessibility.matrix(payload))
@router.get("/network/capabilities")
def capabilities():
    return {"matrix":True,"isochrone":False,"reason":"Current OSRM route/table provider has no isochrone endpoint. Imported OSM lines are not a validated directed routing graph with full access restrictions. No circular substitute generated."}
@router.post("/network/isochrone")
def isochrone(request:Request):
    guard(request);raise HTTPException(501,"Network isochrones unsupported by the current provider; no reachable-road polygon was generated.")
@router.post("/analysis/saved")
def save(request:Request,payload:SaveAnalysis):
    guard(request);return run(lambda:analytics.save_analysis(payload.calculation_id))
@router.get("/history/{kind}")
def history(request:Request,kind:Literal["analyses","routes"],limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0,le=10000)):
    guard(request);return run(lambda:analytics.history(kind,limit,offset))
@router.get("/history/{kind}/{id}")
def get_saved(request:Request,kind:Literal["analyses","routes"],id:UUID):
    guard(request);return run(lambda:analytics.get_saved(kind,str(id)))
@router.post("/history/{kind}/{id}/archive")
def archive(request:Request,kind:Literal["analyses","routes"],id:UUID,payload:ArchiveRequest):
    guard(request);return run(lambda:analytics.archive(kind,str(id)))

@router.post("/history/{kind}/{id}/restore")
def restore(request:Request,kind:Literal["analyses","routes"],id:UUID,payload:ArchiveRequest):
    guard(request);return run(lambda:analytics.restore(kind,str(id)))
