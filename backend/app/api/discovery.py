from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import get_settings
from app.schemas.discovery import DiscoveryRequest, STUDY_TARGETS
from app.services import discovery
from app.services.osm import ProviderError, geocode

router=APIRouter(prefix="/api",tags=["discovery"])

def local_access(request, *, database=False):
    settings=get_settings()
    host=request.headers.get("host","").split(":")[0]
    origin=request.headers.get("origin")
    if (not settings.discovery_enabled or request.client is None or
        request.client.host not in ("127.0.0.1","::1","testclient") or
        host not in ("127.0.0.1","localhost","testserver") or
        (origin and origin not in settings.cors_origins)):
        raise HTTPException(403,"Discovery is restricted to this local workspace. Public deployment requires authentication and a shared provider quota.")
    if database and settings.data_mode!="postgis":
        raise HTTPException(409,"Live discovery requires configured PostGIS mode; synthetic data will not be substituted.")

@router.get("/discovery/study-areas")
def study_areas():
    return {"areas":STUDY_TARGETS,"note":"Names are search targets, not verified polygons."}

@router.get("/locations/search")
def locations(request:Request,q:str=Query(min_length=2,max_length=200)):
    local_access(request)
    try: return geocode(q)
    except ProviderError as exc: raise HTTPException(502,str(exc))

@router.post("/discovery/jobs",status_code=202)
def start(request:Request,payload:DiscoveryRequest,background:BackgroundTasks):
    local_access(request,database=True)
    try:
        job_id=discovery.create_job(payload)
    except ProviderError as exc: raise HTTPException(409,str(exc))
    except (SQLAlchemyError,RuntimeError,OSError):
        raise HTTPException(503,"Database unavailable; import was not started.")
    background.add_task(discovery.run_job,job_id,payload)
    return {"id":job_id,"status":"queued"}

@router.get("/discovery/jobs")
def jobs(request:Request):
    local_access(request,database=True)
    try: return {"jobs":discovery.recent_jobs()}
    except (SQLAlchemyError,RuntimeError,OSError): raise HTTPException(503,"Database job history unavailable.")

@router.get("/discovery/jobs/{job_id}")
def job(request:Request,job_id:str):
    local_access(request,database=True)
    if len(job_id)!=36: raise HTTPException(404,"Job not found.")
    try: result=discovery.job_record(job_id)
    except (SQLAlchemyError,RuntimeError,OSError): raise HTTPException(503,"Database job history unavailable.")
    if result is None: raise HTTPException(404,"Job not found.")
    return result
