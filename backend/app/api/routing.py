from uuid import UUID
from fastapi import APIRouter,HTTPException,Request
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import get_settings
from app.routing import service
from app.routing.providers import RoutingError,provider_info
from app.schemas.routing import RouteRequest,SaveRouteRequest

router=APIRouter(prefix="/api/routing",tags=["routing"])

def local_access(request,database=False):
    settings=get_settings()
    if (not settings.routing_enabled or request.client is None or
        request.client.host not in ("127.0.0.1","::1","testclient") or
        request.headers.get("host","").split(":")[0] not in ("127.0.0.1","localhost","testserver") or
        (request.headers.get("origin") and request.headers["origin"] not in settings.cors_origins)):
        raise HTTPException(403,"Routing is restricted to this enabled local workspace. Public use requires authentication, shared quotas and provider arrangements.")
    if database and settings.data_mode!="postgis": raise HTTPException(409,"PostGIS mode is required for imported facilities and route saving.")

def run(operation):
    try: return operation()
    except RoutingError as exc: raise HTTPException(exc.status,str(exc))
    except (SQLAlchemyError,OSError,RuntimeError):
        raise HTTPException(503,"Routing database/cache operation unavailable. No substitute route generated.")

@router.get("/provider")
def provider():
    return provider_info()

@router.post("/route")
def route(request:Request,payload:RouteRequest):
    local_access(request)
    return run(lambda:service.calculate(payload))

@router.get("/features/{feature_id}/anchor")
def anchor(request:Request,feature_id:UUID):
    local_access(request,database=True)
    return run(lambda:service.feature_anchor(str(feature_id)))

@router.get("/features/{feature_id}/nearest-warehouse")
def nearest(request:Request,feature_id:UUID):
    local_access(request,database=True)
    return run(lambda:service.nearest_warehouse(str(feature_id)))

@router.post("/saved")
def save(request:Request,payload:SaveRouteRequest):
    local_access(request,database=True)
    return run(lambda:service.save_calculation(payload))
