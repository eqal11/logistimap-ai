from uuid import UUID
from fastapi import APIRouter,Request,Query,HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.api.analytics import guard
from app.core.config import get_settings
from app.sites.catalog import catalog
from app.sites.mcda import SiteError,ahp
from app.sites import service,repository
from app.sites.imports import import_candidates
from app.schemas.sites import SiteScenario,AHPRequest,SiteImport,SiteSave
router=APIRouter(prefix="/api/sites",tags=["phase6 site selection"])
def run(fn):
 try:return fn()
 except SiteError as e:raise HTTPException(422,str(e))
 except (SQLAlchemyError,OSError,RuntimeError):raise HTTPException(503,"Site evaluation database/provider unavailable; no substitute suitability scores.")
@router.get("/catalog")
def definitions():return {"criteria":catalog(),"limits":{"candidates":12,"criteria":8,"crs":"EPSG:4326","candidate_vertices":25000},"data_mode":get_settings().data_mode}
@router.post("/ahp")
def consistency(request:Request,payload:AHPRequest):
 guard(request);return run(lambda:ahp(payload.matrix))
@router.post("/prepare")
def prepare(request:Request,payload:SiteScenario):
 guard(request);return run(lambda:service.prepare(payload))
@router.post("/evaluate")
def evaluate(request:Request,payload:SiteScenario):
 guard(request);return run(lambda:service.evaluate(payload))
@router.post("/import")
def importing(request:Request,payload:SiteImport):
 guard(request);return run(lambda:import_candidates(payload))
@router.post("/saved")
def save(request:Request,payload:SiteSave):
 guard(request);return run(lambda:repository.save(payload.calculation_id))
@router.get("/saved")
def history(request:Request,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000)):
 guard(request);return run(lambda:repository.history(limit,offset))
@router.get("/saved/{id}")
def saved(request:Request,id:UUID):
 guard(request);return run(lambda:repository.get(str(id)))
