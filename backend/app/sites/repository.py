import json,time
from contextlib import nullcontext
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from app.db.session import get_engine
from app.models.sites import SiteScenario,SiteCandidate,SiteEvaluation,SiteCriterionValue
from app.sites.service import cache_path
from app.sites.mcda import SiteError
def save(key,db=None):
 path=cache_path(key)
 if not path.exists() or time.time()-path.stat().st_mtime>86400:raise SiteError("Evaluation cache expired; evaluate again before saving")
 result=json.loads(path.read_text(encoding="utf-8"))
 if result.get("calculation_id")!=key or result.get("operation")!="site_suitability":raise SiteError("Invalid evaluation cache")
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  previous=tx.scalar(select(SiteEvaluation).where(SiteEvaluation.calculation_id==key))
  if previous:return {"id":previous.id,"scenario_id":previous.scenario_id,"status":"already_saved"}
  scenario=SiteScenario(name=result["title"],parameters=result["scenario"]);tx.add(scenario);tx.flush()
  row=SiteEvaluation(scenario_id=scenario.id,calculation_id=key,result=result);tx.add(row);tx.flush()
  for c in result["candidates"]:
   candidate=SiteCandidate(scenario_id=scenario.id,feature_id=c["feature_id"],logical_key=c["id"],geometry=from_shape(shape(c["geometry"]),srid=4326),provenance=c["provenance"])
   tx.add(candidate);tx.flush()
   for criterion,cell in result["values"][c["id"]].items():
    tx.add(SiteCriterionValue(evaluation_id=row.id,candidate_id=candidate.id,criterion_id=criterion,value=cell["value"],provenance=cell))
  identifier=row.id;scenario_id=scenario.id
  if db is None:
   try:tx.commit()
   except IntegrityError:
    tx.rollback();previous=tx.scalar(select(SiteEvaluation).where(SiteEvaluation.calculation_id==key))
    if not previous:raise
    return {"id":previous.id,"scenario_id":previous.scenario_id,"status":"already_saved"}
  return {"id":identifier,"scenario_id":scenario_id,"status":"saved"}
def history(limit=25,offset=0,db=None):
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  count=tx.scalar(select(func.count()).select_from(SiteEvaluation))
  rows=tx.execute(select(SiteEvaluation.id,SiteEvaluation.created_at,SiteEvaluation.result["title"].as_string().label("name"),SiteEvaluation.result["scenario"]["method"].as_string().label("method"))
     .order_by(SiteEvaluation.created_at.desc(),SiteEvaluation.id).limit(limit).offset(offset)).mappings().all()
  return {"items":[{**r,"created_at":r["created_at"].isoformat()} for r in rows],"total":count,"limit":limit,"offset":offset}
def get(identifier,db=None):
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  row=tx.get(SiteEvaluation,identifier)
  if row is None:raise SiteError("Saved site evaluation not found")
  return {**row.result,"saved_id":row.id,"scenario_id":row.scenario_id}
