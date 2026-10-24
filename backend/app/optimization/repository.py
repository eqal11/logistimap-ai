"""Transactional logistics snapshots; legacy GIS/route/analysis tables are never modified."""
import copy,json
from datetime import datetime,timezone
from uuid import uuid4
from contextlib import nullcontext
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point,MultiLineString,shape
from app.db.session import get_engine
from app.models.entities import OptimizationScenario
from app.models.logistics import LogisticsDepot,LogisticsStop,LogisticsDemand,LogisticsVehicle,OptimizationJob,OptimizationSolution,VehicleAssignment,LogisticsComparison
from app.schemas.optimization import Scenario
from app.routing.service import feature_anchor
from app.optimization.solver import OptimizationError

def session(db=None):return nullcontext(db) if db is not None else Session(get_engine())
def save_scenario(payload:Scenario,db=None):
    s=payload.model_copy(deep=True)
    with session(db) as tx:
        for p in s.depots+s.stops:
            if p.feature_id:
                ref=feature_anchor(p.feature_id,tx)
                p.coordinates=tuple(ref["coordinates"]);p.source_id=ref["source_id"]
        identifier=str(uuid4());parameters=s.model_dump(mode="json")
        tx.add(OptimizationScenario(id=identifier,name=s.name,parameters={"phase":5,"scenario":parameters,"archived":False}))
        tx.flush();depots={};stops={}
        for p in s.depots:
            row=LogisticsDepot(scenario_id=identifier,logical_key=p.id,geometry=from_shape(Point(p.coordinates),srid=4326),parameters=p.model_dump(mode="json"))
            tx.add(row);tx.flush();depots[p.id]=row.id
        for v in s.vehicles:
            tx.add(LogisticsVehicle(scenario_id=identifier,logical_key=v.id,start_depot_id=depots[v.start_depot],end_depot_id=depots[v.end_depot],capacity=v.capacity,parameters=v.model_dump(mode="json")))
        for p in s.stops:
            row=LogisticsStop(scenario_id=identifier,logical_key=p.id,geometry=from_shape(Point(p.coordinates),srid=4326),parameters=p.model_dump(mode="json"))
            tx.add(row);tx.flush();stops[p.id]=row.id
        for p in s.stops:
            tx.add(LogisticsDemand(stop_id=stops[p.id],pickup_stop_id=stops.get(p.pickup_id),amount=p.demand,unit=s.capacity_unit,context=s.demand_context))
        if db is None:tx.commit()
        return {"id":identifier,"scenario":parameters,"status":"saved"}

def get_scenario(identifier,db=None,include_archived=False):
    with session(db) as tx:
        row=tx.get(OptimizationScenario,identifier)
        if row is None or row.parameters.get("phase")!=5:raise OptimizationError("Phase 5 scenario not found")
        if row.parameters.get("archived") and not include_archived:raise OptimizationError("Scenario is archived; restore before solving")
        return {"id":row.id,"name":row.name,"created_at":row.created_at.isoformat(),"archived":bool(row.parameters.get("archived")),
                "scenario":copy.deepcopy(row.parameters["scenario"])}

def list_scenarios(limit=25,offset=0,archived=False,db=None):
    with session(db) as tx:
        condition=[OptimizationScenario.parameters["phase"].as_integer()==5,
                   OptimizationScenario.parameters["archived"].as_boolean()==archived]
        count=tx.scalar(select(func.count()).select_from(OptimizationScenario).where(*condition))
        rows=tx.scalars(select(OptimizationScenario).where(*condition).order_by(OptimizationScenario.created_at.desc()).limit(limit).offset(offset)).all()
        items=[]
        for r in rows:
            latest=tx.scalar(select(OptimizationSolution).where(OptimizationSolution.scenario_id==r.id).order_by(OptimizationSolution.created_at.desc()).limit(1))
            items.append({"id":r.id,"name":r.name,"created_at":r.created_at.isoformat(),"archived":archived,
                          "objective":r.parameters["scenario"]["objective"],"stops":len(r.parameters["scenario"]["stops"]),
                          "summary":latest.result["summary"] if latest else None,"status":latest.result["status"] if latest else "not_solved"})
        return {"items":items,"total":count,"limit":limit,"offset":offset}

def archive(identifier,value=True,db=None):
    with session(db) as tx:
        get_scenario(identifier,tx,True);row=tx.get(OptimizationScenario,identifier)
        row.parameters={**row.parameters,"archived":value,"archived_at":datetime.now(timezone.utc).isoformat() if value else None}
        if db is None:tx.commit()
        return {"id":identifier,"status":"archived" if value else "restored"}

def duplicate(identifier,db=None):
    source=get_scenario(identifier,db,True);s=Scenario.model_validate(source["scenario"]);s.name=(s.name+" · copy")[:160]
    return save_scenario(s,db)

def create_job(identifier,db=None):
    with session(db) as tx:
        get_scenario(identifier,tx)
        row=OptimizationJob(scenario_id=identifier,status="queued",metadata_json={"stage":"Queued","updated_at":datetime.now(timezone.utc).isoformat()})
        tx.add(row);tx.flush();key=row.id
        if db is None:tx.commit()
        return key

def update_job(key,status,stage,db=None):
    with session(db) as tx:
        row=tx.get(OptimizationJob,key)
        if row:
            row.status=status;row.metadata_json={**row.metadata_json,"stage":stage[:300],"updated_at":datetime.now(timezone.utc).isoformat()}
            if db is None:tx.commit()

def get_job(key,db=None):
    with session(db) as tx:
        row=tx.get(OptimizationJob,key)
        if not row:raise OptimizationError("Optimization job not found")
        return {"id":key,"scenario_id":row.scenario_id,"status":row.status,**row.metadata_json}

def persist_solution(scenario_id,job_id,result,db=None):
    if len(json.dumps(result).encode("utf-8"))>8_000_000:raise OptimizationError("Optimization result exceeds 8 MB; reduce scenario extent/size.")
    with session(db) as tx:
        row=OptimizationSolution(scenario_id=scenario_id,job_id=job_id,result=result);tx.add(row);tx.flush()
        fleet={v.logical_key:v.id for v in tx.scalars(select(LogisticsVehicle).where(LogisticsVehicle.scenario_id==scenario_id))}
        for r in result["routes"]:
            geom=r["geometry"];multiline=None
            if geom:
                g=shape(geom);multiline=MultiLineString([g]) if g.geom_type=="LineString" else g
                if not multiline.is_valid or multiline.is_empty:raise OptimizationError("Invalid route geometry cannot be saved")
            tx.add(VehicleAssignment(solution_id=row.id,vehicle_id=fleet[r["vehicle_id"]],
                geometry=from_shape(multiline,srid=4326) if multiline else None,summary={k:v for k,v in r.items() if k!="geometry"}))
        if db is None:tx.commit()
        return row.id

def results(identifier,db=None):
    with session(db) as tx:
        get_scenario(identifier,tx,True)
        row=tx.scalar(select(OptimizationSolution).where(OptimizationSolution.scenario_id==identifier).order_by(OptimizationSolution.created_at.desc()).limit(1))
        if not row:raise OptimizationError("No saved optimization solution yet")
        return {**row.result,"solution_id":row.id}

class ComparisonNotFound(OptimizationError):
    pass

class ComparisonUnavailable(OptimizationError):
    pass

def _comparison_record(identifier,tx):
    row=tx.get(LogisticsComparison,identifier)
    if row is None:raise ComparisonNotFound("Saved comparison not found")
    return row

def _comparison_view(row):
    return {**copy.deepcopy(row.result),"id":row.id,"name":row.name,"created_at":row.created_at.isoformat()}

def list_comparisons(limit=25,offset=0,db=None):
    with session(db) as tx:
        total=tx.scalar(select(func.count()).select_from(LogisticsComparison))
        records=tx.scalars(select(LogisticsComparison).order_by(LogisticsComparison.created_at.desc(),LogisticsComparison.id).limit(limit).offset(offset))
        return {"items":[{"id":r.id,"name":r.name,"created_at":r.created_at.isoformat(),
                          "scenario_count":len(r.result.get("rows",[])),"schema_version":r.result.get("schema_version",1)} for r in records],
                "total":total,"limit":limit,"offset":offset}

def get_comparison(identifier,db=None):
    with session(db) as tx:return _comparison_view(_comparison_record(identifier,tx))

def comparison_solutions(identifier,db=None):
    with session(db) as tx:
        record=_comparison_record(identifier,tx);rows=record.result.get("rows",[])
        if not 2<=len(rows)<=4:raise ComparisonUnavailable("Saved comparison has no valid 2–4 solution references")
        items=[];warnings=[]
        for row in rows:
            key=row.get("solution_id")
            if key:
                solution=tx.get(OptimizationSolution,key)
            else:
                # Legacy snapshots did not pin an ID. Resolve the latest solution at creation time,
                # then require its stored metrics to match. Never silently use today's latest solve.
                solution=tx.scalar(select(OptimizationSolution).where(
                    OptimizationSolution.scenario_id==row["scenario_id"],
                    OptimizationSolution.created_at<=record.created_at).order_by(
                    OptimizationSolution.created_at.desc(),OptimizationSolution.id.desc()).limit(1))
                warnings.append("Legacy comparison: solution reconstructed at snapshot time and checked against saved metrics.")
            if (solution is None or solution.scenario_id!=row.get("scenario_id") or
                solution.result.get("status")!=row.get("status") or
                any(solution.result.get("summary",{}).get(k)!=row.get(k) for k in ("distance_m","travel_duration_s","estimated_cost","assigned_stops","unassigned_stops","vehicles_used"))):
                raise ComparisonUnavailable("Exact historical solution unavailable or metrics differ; no replacement geometry was substituted.")
            result={**copy.deepcopy(solution.result),"solution_id":solution.id}
            items.append({"scenario_id":solution.scenario_id,"solution_id":solution.id,"name":row["name"],"result":result})
        return {"comparison_id":record.id,"items":items,"warnings":list(dict.fromkeys(warnings)),
                "profile":"car","heavy_vehicle_verified":False}

def compare(ids,name="Scenario comparison",db=None):
    if not 2<=len(ids)<=4 or len(set(ids))!=len(ids):raise OptimizationError("Select 2–4 distinct saved scenarios")
    with session(db) as tx:
        rows=[];scenarios=[]
        for key in ids:
            s=get_scenario(key,tx,True);r=results(key,tx)
            rows.append({"scenario_id":key,"solution_id":r["solution_id"],"name":s["name"],"objective":r["objective"],"status":r["status"],
                         "solver_status":r["solver_status"],"proven_optimal":r["proven_optimal"],**r["summary"],
                         "final_road_summary":r.get("routed_summary"),"road_geometry_constraints_verified":r.get("road_geometry_constraints_verified",False),
                         "capacity_unit":s["scenario"]["capacity_unit"],"demand_context":s["scenario"]["demand_context"],
                         "provider":r["provider"],"profile":"car","heavy_vehicle_verified":False,
                         "matrix_id":r["matrix"]["id"],"scenario_assumptions":s["scenario"]})
            scenarios.append(s["scenario"])
        same_locations=all({(p["id"],tuple(p["coordinates"]),p["demand"]) for p in x["stops"]}=={(p["id"],tuple(p["coordinates"]),p["demand"]) for p in scenarios[0]["stops"]} for x in scenarios)
        result={"schema_version":2,"name":name,"rows":rows,"comparable_locations_and_demand":same_locations,
            "metric_basis":"Matrix metrics are solver objectives. Final road metrics are shown separately when road timing constraints were verified.",
            "warnings":["Different scenarios can change demand, windows, depots, costs and objectives. Inspect assumptions; comparison is descriptive, not a controlled causal estimate.",
                        "A shorter route with unassigned stops is not equivalent service. Standard car profile; not truck verified."]}
        record=LogisticsComparison(name=name,result=result);tx.add(record);tx.flush()
        view=_comparison_view(record)
        if db is None:tx.commit()
        return view

def recover_interrupted_jobs():
    from sqlalchemy import update
    with Session(get_engine()) as tx:
        rows=tx.scalars(select(OptimizationJob).where(OptimizationJob.status.in_(["queued","running"]))).all()
        for row in rows:
            row.status="interrupted"
            row.metadata_json={"stage":"Backend restarted before completion; solve the saved scenario again.","updated_at":datetime.now(timezone.utc).isoformat()}
        tx.commit()
        return len(rows)
