"""One bounded background worker; persisted job stages and cooperative cancellation."""
import copy,threading,math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from app.optimization import repository as repo
from app.optimization.matrix import road_matrix
from app.optimization.solver import solve,OptimizationError,cost_components
from app.schemas.optimization import Scenario
from app.schemas.routing import RouteRequest
from app.routing.service import calculate
from app.routing.providers import RoutingError,provider_info,LIMITATIONS

executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix="logistics")
lock=threading.Lock()
active=None
cancelled=set()

def start(identifier):
    global active
    with lock:
        if active is not None:raise RoutingError("One optimization job is already active. Wait or cancel it.",429)
        key=repo.create_job(identifier);active=key
        executor.submit(worker,key,identifier)
    return {"job_id":key,"status":"queued"}

def cancel(key):
    with lock:
        if active!=key:raise OptimizationError("Job is no longer active")
        cancelled.add(key)
    return {"id":key,"status":"cancellation_requested","message":"Cancellation checked between provider calls and after bounded solver execution; an in-flight request/search cannot be interrupted."}

def checkpoint(key,stage):
    with lock:
        if key in cancelled:raise InterruptedError()
    repo.update_job(key,"running",stage)

def calculate_solution(s:Scenario,progress=lambda x:None):
    points=[{"coordinates":list(p.coordinates),"label":p.name} for p in s.depots+s.stops]
    matrix=road_matrix(points,s.max_snap_m,progress=progress)
    progress("OR-Tools solving · bounded "+str(s.solver_seconds)+" seconds")
    result=solve(s,matrix)
    progress("Validating solution and retrieving road geometry")
    warnings=list(LIMITATIONS)+[
        "GIS locations are candidate references, not verified customers, gates or legal truck access.",
        "Demands: "+s.demand_context+". Capacity is a single integer unit: "+s.capacity_unit+".",
        "Matrix distances follow fastest OSRM paths, not necessarily shortest-distance paths; no live traffic.",
        "Time windows apply to service start; service completion and depot return must fit the vehicle working limit.",
        "Optional-stop priorities weight a lexicographic service penalty before the selected travel objective.",
        "Operating cost excludes tolls. Fuel/driver costs are added only from supplied values; avoid counting them twice in cost/km.",
        "Empty vehicles are not repositioned between different start/end depots. Vehicle minimization is a weighted count-first objective; balance minimizes total metres + 20 × longest route.",
        "Solver schedules use upward-rounded whole seconds/metres; final road geometry may differ at via-points because of OSRM turn continuity."
    ]
    for r in result["routes"]:
        progress("Road geometry · "+r["vehicle_name"])
        indices=r["node_indices"];chunks=[]
        # At most 8 via-points per ordinary Phase 3 request; overlapping boundary retains real road geometry.
        try:
            for begin in range(0,len(indices)-1,7):
                subset=indices[begin:begin+8]
                cleaned=[]
                for node in subset:
                    p=points[node]
                    if not cleaned or cleaned[-1]["coordinates"]!=p["coordinates"]:cleaned.append(p)
                if len(cleaned)<2:continue
                route=calculate(RouteRequest(points=cleaned,alternatives=False,max_snap_m=s.max_snap_m))
                chunks.append(route["routes"][0])
            if not chunks:raise RoutingError("No non-zero road route geometry available",422)
            r["geometry"]={"type":"MultiLineString","coordinates":[c["geometry"]["coordinates"] for c in chunks]}
            r["geometry_status"]="available"
            r["geometry_distance_m"]=sum(c["distance_m"] for c in chunks)
            r["geometry_duration_s"]=sum(c["duration_s"] for c in chunks)
            r["geometry_matrix_difference_m"]=r["geometry_distance_m"]-r["distance_m"]
            legs=[leg for chunk in chunks for leg in chunk["legs"]]
            vehicle=next(v for v in s.vehicles if v.id==r["vehicle_id"])
            by_id={p.id:p for p in s.depots+s.stops}
            at=r["schedule"][0]["arrival_s"];valid=len(legs)==len(r["schedule"])-1
            actual_schedule=[at]
            if valid:
                for leg,previous,point in zip(legs,r["schedule"],r["schedule"][1:]):
                    at=max(by_id[point["id"]].window[0],at+(previous["departure_s"]-previous["arrival_s"])+math.ceil(leg["duration_s"]))
                    actual_schedule.append(at)
                    if at>min(by_id[point["id"]].window[1],vehicle.window[1]):valid=False
                valid=valid and at-actual_schedule[0]<=vehicle.max_duration_s and math.ceil(r["geometry_distance_m"])<=vehicle.max_distance_m
            r["road_geometry_constraints_verified"]=valid
            r["geometry_working_duration_s"]=at-actual_schedule[0] if valid else None
            r["geometry_cost_components"]=cost_components(vehicle,r["geometry_distance_m"],at-actual_schedule[0]) if valid else None
            r["geometry_estimated_cost"]=round(sum(r["geometry_cost_components"].values()),2) if valid else None
            r["road_geometry_arrival_s"]=actual_schedule if valid else None
            if not valid:warnings.append(r["vehicle_name"]+": final via-point road timings do not satisfy the matrix schedule/limits or include duplicate references. Replan before dispatch; matrix solution remains separately labelled.")

            if abs(r["geometry_matrix_difference_m"])>max(100,r["distance_m"]*.05):
                warnings.append(r["vehicle_name"]+": final via-point route differs by more than 5%/100 m from matrix sum. Scheduling/cost uses the validated matrix; inspect before dispatch.")
        except RoutingError as e:
            r["geometry"]=None;r["geometry_status"]="unavailable";r["geometry_error"]=str(e)
            warnings.append(r["vehicle_name"]+": road geometry unavailable; no straight-line route displayed.")
    checked=bool(result["routes"]) and all(r.get("road_geometry_constraints_verified",False) for r in result["routes"])
    result["routed_summary"]={"distance_m":sum(r["geometry_distance_m"] for r in result["routes"]),
        "travel_duration_s":sum(r["geometry_duration_s"] for r in result["routes"]),
        "working_duration_s":sum(r["geometry_working_duration_s"] for r in result["routes"]),
        "estimated_cost":round(sum(r["geometry_estimated_cost"] for r in result["routes"]),2)} if checked else None
    info=provider_info()
    return {**result,"scenario":s.model_dump(mode="json"),"matrix":matrix,"warnings":warnings,
        "provider":info["provider"],"profile":"car","heavy_vehicle_verified":False,"attribution":info["attribution"],
        "policy_url":info["policy_url"],"fix_map_url":info["fix_map_url"],"executed_at":datetime.now(timezone.utc).isoformat(),
        "crs":"EPSG:4326","geometry_complete":bool(result["routes"]) and all(r["geometry_status"]=="available" for r in result["routes"]),
        "road_geometry_constraints_verified":bool(result["routes"]) and all(r.get("road_geometry_constraints_verified",False) for r in result["routes"])}

def worker(key,identifier):
    global active
    try:
        checkpoint(key,"Loading saved scenario")
        s=Scenario.model_validate(repo.get_scenario(identifier)["scenario"])
        result=calculate_solution(s,lambda stage:checkpoint(key,stage))
        checkpoint(key,"Saving validated solution")
        repo.persist_solution(identifier,key,result)
        repo.update_job(key,"completed","Solution saved · "+result["status"])
    except InterruptedError:repo.update_job(key,"cancelled","Cancelled between bounded processing stages")
    except (RoutingError,OptimizationError) as e:repo.update_job(key,"failed",str(e))
    except Exception:
        # Never persist raw database/provider exceptions or credentials.
        try:repo.update_job(key,"failed","Optimization processing unavailable; inspect safe local diagnostics. No fabricated result.")
        except Exception:pass
    finally:
        with lock:
            cancelled.discard(key);active=None
