from uuid import UUID
from fastapi import APIRouter,Request,HTTPException,Query
from sqlalchemy.exc import SQLAlchemyError
from app.api.analytics import guard
from app.core.config import get_settings
from app.schemas.optimization import Scenario,Comparison,Confirm,ImportLocations
from app.optimization import repository as repo,jobs
from app.optimization.matrix import road_matrix
from app.optimization.imports import import_locations
from app.optimization.solver import OptimizationError
from app.routing.providers import RoutingError

router=APIRouter(prefix="/api/optimization",tags=["phase5 logistics"])
def checked(request):
    guard(request)
    if not get_settings().optimization_enabled:raise HTTPException(403,"Optimization disabled in this workspace.")
def run(fn):
    try:return fn()
    except repo.ComparisonNotFound as e:raise HTTPException(404,str(e))
    except repo.ComparisonUnavailable as e:raise HTTPException(409,str(e))
    except OptimizationError as e:raise HTTPException(422,str(e))
    except RoutingError as e:raise HTTPException(e.status,str(e))
    except (SQLAlchemyError,OSError,RuntimeError):raise HTTPException(503,"Logistics database/provider operation unavailable; no substitute result.")
@router.post("/scenarios",status_code=201)
def create(request:Request,payload:Scenario):
    checked(request);return run(lambda:repo.save_scenario(payload))
@router.get("/scenarios")
def listing(request:Request,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),archived:bool=False):
    checked(request);return run(lambda:repo.list_scenarios(limit,offset,archived))
@router.get("/scenarios/{id}")
def get(request:Request,id:UUID):
    checked(request);return run(lambda:repo.get_scenario(str(id),include_archived=True))
@router.post("/scenarios/{id}/duplicate",status_code=201)
def duplicate(request:Request,id:UUID):
    checked(request);return run(lambda:repo.duplicate(str(id)))
@router.post("/scenarios/{id}/archive")
def archive(request:Request,id:UUID,payload:Confirm):
    checked(request);return run(lambda:repo.archive(str(id)))
@router.post("/scenarios/{id}/restore")
def restore(request:Request,id:UUID,payload:Confirm):
    checked(request);return run(lambda:repo.archive(str(id),False))
@router.post("/scenarios/{id}/solve",status_code=202)
def solve(request:Request,id:UUID):
    checked(request)
    if not get_settings().routing_enabled:raise HTTPException(503,"Road routing disabled")
    return run(lambda:jobs.start(str(id)))
@router.get("/scenarios/{id}/results")
def results(request:Request,id:UUID):
    checked(request);return run(lambda:repo.results(str(id)))
@router.get("/jobs/{id}")
def job(request:Request,id:UUID):
    checked(request);return run(lambda:repo.get_job(str(id)))
@router.post("/jobs/{id}/cancel")
def cancel(request:Request,id:UUID,payload:Confirm):
    checked(request);return run(lambda:jobs.cancel(str(id)))
@router.post("/matrix")
def matrix(request:Request,payload:Scenario):
    checked(request)
    if not get_settings().routing_enabled:raise HTTPException(503,"Road routing disabled")
    return run(lambda:road_matrix([{"coordinates":list(p.coordinates),"label":p.name} for p in payload.depots+payload.stops],payload.max_snap_m))
@router.post("/compare")
def compare(request:Request,payload:Comparison):
    checked(request)
    try:ids=[str(UUID(x)) for x in payload.ids]
    except ValueError:raise HTTPException(422,"Comparison requires saved scenario UUIDs")
    return run(lambda:repo.compare(ids,payload.name))
@router.post("/import")
def importing(request:Request,payload:ImportLocations):
    checked(request);return run(lambda:import_locations(payload))
@router.get("/vehicles")
def vehicles(request:Request,scenario_id:UUID):
    checked(request);return run(lambda:{"scenario_id":str(scenario_id),"vehicles":repo.get_scenario(str(scenario_id),include_archived=True)["scenario"]["vehicles"]})


@router.get("/comparisons")
def comparisons(request:Request,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000)):
    checked(request);return run(lambda:repo.list_comparisons(limit,offset))

@router.get("/comparisons/{id}")
def saved_comparison(request:Request,id:UUID):
    checked(request);return run(lambda:repo.get_comparison(str(id)))

@router.get("/comparisons/{id}/solutions")
def saved_comparison_solutions(request:Request,id:UUID):
    checked(request);return run(lambda:repo.comparison_solutions(str(id)))
