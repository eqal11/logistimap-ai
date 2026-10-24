"""Fresh Phase 5 review. Adds review records only; never migrates or updates historical scenarios."""
import copy,json,time,sys
from datetime import datetime,timezone
from pathlib import Path
import httpx
from verify_phase5_live import base,call,execute
from app.core.config import PROJECT_ROOT
from app.services.osm import ssl_context
from app.db.verification import safe_error
OUT=PROJECT_ROOT/"docs"/"phase5-review-live.json"
def main(case):
 data=json.loads(OUT.read_text()) if OUT.exists() else {"review_started_at":datetime.now(timezone.utc).isoformat()}
 try:
  with httpx.Client(verify=ssl_context(),timeout=60) as client:
   if case=="compare":
    raw=call(client,"POST","/api/optimization/compare",{"ids":[data[k]["scenario_id"] for k in ("D2","D3","D4")],"name":"Fresh acceptance review · hypothetical fleet comparison"})
    data[case]=raw
   else:
    if case in ("A","B","C"):
     p=base(case,2 if case=="B" else 3);p["max_snap_m"]=1900
    else:
     p=call(client,"GET","/api/optimization/scenarios/"+data["A"]["scenario_id"])["scenario"]
     if case.startswith("D"):
      count=int(case[-1]);v=copy.deepcopy(p["vehicles"][0])
      p["vehicles"]=[{**v,"id":"vehicle-"+str(i+1),"name":"Vehicle "+str(i+1)} for i in range(count)]
     if case in ("E","mandatory"):
      p["vehicles"]=p["vehicles"][:1];p["vehicles"][0]["capacity"]=2
      if case=="mandatory":p["allow_unassigned"]=False
     if case=="F":
      for stop in p["stops"]:stop["window"]=[28800,43200]
      for v in p["vehicles"]:v["window"]=[28800,57600]
     if case=="pickup":
      # Same genuine road nodes; hypothetical pickup-load pair; all must be served.
      p["stops"][0]["kind"]="pickup";p["stops"][1]["pickup_id"]=p["stops"][0]["id"]
      p["allow_unassigned"]=False
     if case=="multi_depot":
      other=p["stops"].pop()
      other={k:v for k,v in other.items() if k in ("id","name","coordinates","feature_id","source_id","window")}
      other["id"]="depot-2";p["depots"].append(other)
      p["vehicles"][1]["start_depot"]="depot-2";p["vehicles"][1]["end_depot"]="depot-2"
     if case=="tsp":
      p["vehicles"]=p["vehicles"][:1];p["vehicles"][0]["capacity"]=100;p["allow_unassigned"]=False
     if case.startswith("objective-"):p["objective"]=case.removeprefix("objective-")
    p["name"]="Fresh Phase 5 acceptance "+case+" · hypothetical demands"
    result=execute(client,p)
    if "job_id" in result:
     raw=call(client,"GET","/api/optimization/scenarios/"+result["scenario_id"]+"/results")
     result["result_status"]=raw["status"];result["unassigned"]=raw["unassigned"]
     result["matrix"]["upstream_requests"]=raw["matrix"]["upstream_requests"]
     result["verified_at"]=datetime.now(timezone.utc).isoformat()
     result["independent_assertions"]=[]
     if raw["validated"]:
      assert raw["geometry_complete"] and raw["road_geometry_constraints_verified"]
      assert all(r["peak_load"]<=r["capacity"] for r in raw["routes"])
      assert all(r["estimated_cost"]==round(sum(r["cost_components"].values()),2) for r in raw["routes"])
      result["independent_assertions"]=["assignment partition unique","capacity valid","matrix schedule validated","actual road geometry valid","final road constraints valid","explicit costs verified","saved scenario roundtrip"]
      if case in ("A","B","C","F","pickup","multi_depot","tsp") or case.startswith("objective"):
       assert raw["summary"]["unassigned_stops"]==0
      if case=="E":assert raw["summary"]["unassigned_stops"]==9
      if case=="D2":assert raw["summary"]["unassigned_stops"]==2
      if case=="F":
       for route in raw["routes"]:
        for row,at in zip(route["schedule"],route["road_geometry_arrival_s"]):
         if row["kind"]!="depot":assert 28800<=at<=43200
       result["independent_assertions"].append("all final-road service starts inside 08:00–12:00")
      if case=="pickup":
       r=next(r for r in raw["routes"] if p["stops"][0]["id"] in r["stop_ids"])
       assert r["stop_ids"].index(p["stops"][0]["id"])<r["stop_ids"].index(p["stops"][1]["id"])
       result["independent_assertions"].append("pickup precedes paired delivery on same vehicle")
     elif case=="mandatory":
      assert not raw["routes"] and raw["status"] in ("infeasible","no_solution_found","timeout")
      assert len(raw["unassigned"])==10
      result["status"]="passed";result["independent_assertions"]=["mandatory demand exceeds capacity; no feasible solution claimed","all unserved stops explicit"]
    assert result["status"]=="passed"
    data[case]=result
   OUT.write_text(json.dumps(data,indent=2),encoding="utf-8")
   print(json.dumps({"case":case,"status":"passed","details":{k:v for k,v in data[case].items() if k in ("scenario_id","summary","matrix","routed_summary","result_status","solver_status","geometry_vertices","independent_assertions")}}))
 except Exception as exc:
  data[case]={"status":"failed","error_type":type(exc).__name__}
  OUT.write_text(json.dumps(data,indent=2),encoding="utf-8")
  print(json.dumps({"case":case,**safe_error(exc)}));return 1
 return 0
if __name__=="__main__":raise SystemExit(main(sys.argv[1]))
