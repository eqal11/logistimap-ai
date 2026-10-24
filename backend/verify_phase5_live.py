"""Opt-in real OSM + OSRM acceptance scenarios. Demands/costs are explicitly hypothetical."""
import argparse,copy,json,time
from pathlib import Path
import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_engine
from app.core.config import PROJECT_ROOT
from app.db.verification import safe_error
from app.routing.service import feature_anchor
from app.services.osm import ssl_context
from app.optimization.solver import validate
from app.schemas.optimization import Scenario
from shapely.geometry import shape

OUT=PROJECT_ROOT/"docs"/"phase5-live-results.json"
def read():return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
def save(data):OUT.write_text(json.dumps(data,indent=2),encoding="utf-8")
def nearby(db,category,xy,limit,exclude=()):
    rows=db.execute(text("""
      SELECT f.id FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id
      WHERE NOT d.synthetic AND EXISTS(SELECT 1 FROM feature_categories c WHERE c.feature_id=f.id AND c.category_id=:category)
      AND ST_DWithin(f.geometry::geography,ST_SetSRID(ST_MakePoint(:x,:y),4326)::geography,25000)
      ORDER BY ST_Distance(f.geometry::geography,ST_SetSRID(ST_MakePoint(:x,:y),4326)::geography),f.id LIMIT 40
    """),{"category":category,"x":xy[0],"y":xy[1]}).scalars().all()
    return [feature_anchor(k,db) for k in rows if k not in exclude][:limit]
def location(p,key):return {"id":key,"name":p["label"],"coordinates":p["coordinates"],"feature_id":p["feature_id"],"source_id":p["source_id"]}
def base(letter,count=3):
    center={"A":[101.5185278,3.0739429],"B":[101.5773144,3.3197692],"C":[101.3966735,3.0027625]}[letter]
    with Session(get_engine()) as db:
        depot=nearby(db,"warehouse",center,1)[0]
        candidates=nearby(db,"warehouse" if letter=="C" else "industrial",center,6 if letter=="C" else 8 if letter=="B" else 10,(depot["feature_id"],))
    return {"name":"Phase 5 "+letter+" · "+{"A":"Shah Alam","B":"Rawang","C":"Port Klang"}[letter]+" · hypothetical demand",
        "notes":"Real imported OSM candidate locations; hypothetical demand 2 units/stop and assumed RM1.50/km + RM10/used vehicle. No actual business shipment/customer claimed.",
        "capacity_unit":"hypothetical units","demand_context":"hypothetical","depots":[location(depot,"depot")],
        "vehicles":[{"id":"vehicle-"+str(i+1),"name":"Vehicle "+str(i+1),"capacity":8,"start_depot":"depot","end_depot":"depot","cost_per_km":1.5,"fixed_cost":10} for i in range(count)],
        "stops":[{**location(p,"stop-"+str(i+1)),"demand":2,"service_s":120} for i,p in enumerate(candidates)],
        "objective":"distance","solver_seconds":3,"max_snap_m":2000,"allow_unassigned":True}
def call(client,method,path,body=None):
    response=client.request(method,"http://127.0.0.1:8000"+path,json=body)
    raw=response.json()
    if response.status_code>=400:raise RuntimeError("Local API rejected "+path+" · "+str(raw.get("error",{}).get("message","Request failed")))
    return raw
def execute(client,payload):
    saved=call(client,"POST","/api/optimization/scenarios",payload)
    job=call(client,"POST","/api/optimization/scenarios/"+saved["id"]+"/solve")
    started=time.monotonic()
    while time.monotonic()-started<300:
        state=call(client,"GET","/api/optimization/jobs/"+job["job_id"])
        if state["status"] in ("failed","cancelled"):return {"scenario_id":saved["id"],"status":"failed","stage":state["stage"]}
        if state["status"]=="completed":break
        time.sleep(3)
    else:return {"scenario_id":saved["id"],"status":"timeout"}
    result=call(client,"GET","/api/optimization/scenarios/"+saved["id"]+"/results")
    scenario=Scenario.model_validate(result["scenario"])
    # Reopen persisted scenario and results, compare exact JSON values.
    reloaded=call(client,"GET","/api/optimization/scenarios/"+saved["id"])
    assert reloaded["scenario"]==result["scenario"]
    for route in result["routes"]:
        assert route["peak_load"]<=route["capacity"]
        if route["geometry"]:
            geom=shape(route["geometry"]);assert geom.is_valid and not geom.is_empty
            assert sum(len(line.coords) for line in geom.geoms)>len(route["schedule"])
    all_ids=[key for r in result["routes"] for key in r["stop_ids"]]
    assert len(all_ids)==len(set(all_ids))
    assert set(all_ids)|{p["id"] for p in result["unassigned"]}=={p.id for p in scenario.stops}
    return {"scenario_id":saved["id"],"job_id":job["job_id"],"status":"passed" if result["validated"] else result["status"],
        "solver_status":result["solver_status"],"proven_optimal":result["proven_optimal"],
        "summary":result["summary"],"matrix":{"nodes":result["matrix"]["nodes"],"pairs":result["matrix"]["pairs"],
        "unreachable_pairs":result["matrix"]["unreachable_pairs"],"cached":result["matrix"]["cached"],"retrieved_at":result["matrix"]["retrieved_at"]},
        "geometry_complete":result["geometry_complete"],"road_geometry_constraints_verified":result.get("road_geometry_constraints_verified"),"routed_summary":result.get("routed_summary"),"geometry_vertices":[sum(len(line) for line in r["geometry"]["coordinates"]) if r["geometry"] else 0 for r in result["routes"]],
        "geometry_errors":[r.get("geometry_error") for r in result["routes"] if not r["geometry"]],
        "persistence_roundtrip":True,"scenario_assumptions":{"demand_context":scenario.demand_context,"capacity_unit":scenario.capacity_unit,"vehicles":[v.model_dump(mode="json") for v in scenario.vehicles],"delivery_windows":[{"id":p.id,"window":list(p.window)} for p in scenario.stops]},"locations":[{"name":p.name,"source_id":p.source_id,"feature_id":p.feature_id,"coordinates":list(p.coordinates)} for p in scenario.depots+scenario.stops],
        "road_routes":[{k:r[k] for k in ("vehicle_name","distance_m","travel_duration_s","working_duration_s","peak_load","capacity","stop_ids","estimated_cost","geometry_status")} for r in result["routes"]]}
def main():
    parser=argparse.ArgumentParser();parser.add_argument("case",choices=["A","B","C","D2","D3","D4","E","F","compare"]);args=parser.parse_args()
    try:
        data=read()
        with httpx.Client(verify=ssl_context(),timeout=60) as client:
            if args.case=="compare":
                ids=[data[k]["scenario_id"] for k in ("D2","D3","D4")]
                result=call(client,"POST","/api/optimization/compare",{"ids":ids,"name":"Phase 5 D · hypothetical 2 / 3 / 4 vehicle comparison"})
                data["D_comparison"]=result;save(data);print(json.dumps(result));return 0
            if args.case in ("A","B","C"):payload=base(args.case,2 if args.case=="B" else 3)
            else:
                if "A" not in data:raise RuntimeError("Run A first")
                payload=call(client,"GET","/api/optimization/scenarios/"+data["A"]["scenario_id"])["scenario"]
                payload["name"]="Phase 5 "+args.case+" · hypothetical demand"
                if args.case.startswith("D"):
                    n=int(args.case[-1]);template=copy.deepcopy(payload["vehicles"][0])
                    payload["vehicles"]=[{**template,"id":"vehicle-"+str(i+1),"name":"Vehicle "+str(i+1)} for i in range(n)]
                elif args.case=="E":
                    payload["vehicles"]=payload["vehicles"][:1];payload["vehicles"][0]["capacity"]=2
                elif args.case=="F":
                    for p in payload["stops"]:p["window"]=[28800,43200]
                    for v in payload["vehicles"]:v["window"]=[28800,57600]
            result=execute(client,payload);data[args.case]=result;save(data)
            print(json.dumps({"case":args.case,**{k:v for k,v in result.items() if k not in ("locations","road_routes")}}))
            return 0 if result["status"]=="passed" else 1
    except Exception as e:
        # No arbitrary exception string/traceback may reveal connection details.
        print(json.dumps(safe_error(e)));return 1
if __name__=="__main__":raise SystemExit(main())
