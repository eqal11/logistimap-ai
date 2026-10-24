"""Phase 5 completion checks: inserts one named comparison only; preserves all historical rows."""
import json,datetime
from pathlib import Path
from collections import Counter
from uuid import uuid4
import httpx
from sqlalchemy import text
from shapely.geometry import shape
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.core.config import PROJECT_ROOT
from app.services.osm import ssl_context
def main():
 try:
  docs=PROJECT_ROOT/"docs";old=json.loads((docs/"phase5-review-live.json").read_text(encoding="utf-8"))
  report={"verified_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"new_routing_calls":0,"migration_applied":False}
  with httpx.Client(verify=ssl_context(),timeout=60) as c:
   base="http://127.0.0.1:8000/api/optimization"
   def get(path):
    r=c.get(base+path);assert r.status_code==200;return r.json()
   initial=get("/comparisons")
   ids=[old[k]["scenario_id"] for k in ("D2","D3","D4")]
   r=c.post(base+"/compare",json={"ids":ids,"name":"Phase 5 completion · pinned 2 / 3 / 4 vehicle comparison"})
   assert r.status_code==200;snapshot=r.json()
   loaded=get("/comparisons/"+snapshot["id"]);assert loaded==snapshot
   assert all(row["solution_id"] and row["final_road_summary"] for row in loaded["rows"])
   solutions=get("/comparisons/"+snapshot["id"]+"/solutions")
   assert len(solutions["items"])==3
   road_count=vertices=0
   for row,item in zip(snapshot["rows"],solutions["items"]):
    assert row["scenario_id"]==item["scenario_id"] and row["solution_id"]==item["solution_id"]
    for route in item["result"]["routes"]:
     geom=shape(route["geometry"]);assert geom.is_valid and not geom.is_empty
     assert route["road_geometry_constraints_verified"]
     road_count+=1;vertices+=sum(len(line) for line in route["geometry"]["coordinates"])
   with get_engine().connect() as db:
    db.execute(text("SET TRANSACTION READ ONLY"))
    for item in solutions["items"]:
     stored=db.execute(text("select result from optimization_solutions where id=:id"),{"id":item["solution_id"]}).scalar_one()
     assert item["result"]=={**stored,"solution_id":item["solution_id"]}
   for legacy in initial["items"]:
    assert get("/comparisons/"+legacy["id"])["id"]==legacy["id"]
    assert len(get("/comparisons/"+legacy["id"]+"/solutions")["items"])==legacy["scenario_count"]
   listing=get("/comparisons?limit=1&offset=1");assert len(listing["items"])==1 and listing["total"]==initial["total"]+1
   assert c.get(base+"/comparisons/"+str(uuid4())).status_code==404
   assert c.get(base+"/comparisons/not-a-uuid").status_code==422
   assert c.get(base+"/comparisons?limit=10000").status_code==422
   assert c.get(base+"/comparisons",headers={"Origin":"https://foreign.example"}).status_code==403
   (docs/"phase5-completion-comparison.json").write_text(json.dumps(snapshot,indent=2),encoding="utf-8")
   (docs/"phase5-completion-solutions.json").write_text(json.dumps(solutions,indent=2),encoding="utf-8")
   report.update({"comparison_id":snapshot["id"],"exact_snapshot_roundtrip":True,"pinned_solution_ids":[r["solution_id"] for r in snapshot["rows"]],"scenario_count":3,"road_geometry_count":road_count,"road_vertices":vertices,"existing_comparisons_reopened":initial["total"],"pagination":"passed","guard_403_validation_422_missing_404":"passed","solution_geometry_identical_to_database":True})
  baseline=json.loads((docs/"phase5-completion-baseline.json").read_text(encoding="utf-8"))
  with get_engine().connect() as db:
   db.execute(text("SET TRANSACTION READ ONLY"))
   report["database"]=verify_connection(db,full=True)
   integrity={}
   for table,before in baseline["tables"].items():
    now=[r[0] for r in db.execute(text('select md5(row_to_json(t)::text) from public."'+table+'" t'))]
    missing=sum((Counter(before)-Counter(now)).values())
    integrity[table]={"before":len(before),"now":len(now),"missing_or_changed_original":missing}
   assert all(v["missing_or_changed_original"]==0 for v in integrity.values())
   report["integrity"]=integrity
  report["status"]="passed"
  (docs/"phase5-completion-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
  print(json.dumps({k:v for k,v in report.items() if k not in ("integrity","database","pinned_solution_ids")}))
  return 0
 except Exception as e:
  print(json.dumps(safe_error(e)));return 1
if __name__=="__main__":raise SystemExit(main())
