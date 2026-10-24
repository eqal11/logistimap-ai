"""Fresh Phase 6 API acceptance on real imported candidates and road matrices; adds site snapshots only."""
import json,copy,datetime
from pathlib import Path
import httpx
from sqlalchemy import text
from shapely.geometry import shape
from app.core.config import PROJECT_ROOT
from app.db.session import get_engine
from app.db.verification import safe_error
from app.services.osm import ssl_context
DOCS=PROJECT_ROOT/"docs"
def main():
 report={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"assumptions":"User-chosen hypothetical priorities, not verified development land or investment advice"}
 try:
  selection=json.loads((DOCS/"phase6-candidate-selection.json").read_text(encoding="utf-8"))
  candidates=[{"id":area["area_id"]+"-"+str(i+1),"name":area["area"]+" · "+c["name"][:100],"feature_id":c["id"]} for area in selection for i,c in enumerate(area["candidates"])]
  assert len(candidates)==12 and len({c["feature_id"] for c in candidates})==12
  with get_engine().connect() as db:
   airport=db.execute(text("select f.id from spatial_features f where exists(select 1 from feature_categories c where c.feature_id=f.id and c.category_id='airport') limit 1")).scalar_one()
  port=next(a["source_reference"] for a in selection if a["area_id"]=="port-klang")
  base={"name":"Phase 6 · six areas · mapped candidates GIS WLC","candidates":candidates,
    "criteria":[{"id":key,"source":"gis","direction":direction,"weight":1} for key,direction in (("road_distance_m","cost"),("warehouse_distance_m","cost"),("industrial_count","benefit"),("industrial_density_km2","benefit"),("industrial_overlap_pct","benefit"),("parcel_area_m2","benefit"))],
    "missing_policy":"reject","radius_m":5000}
  with httpx.Client(verify=ssl_context(),timeout=150) as client:
   def api(method,path,body=None):
    r=client.request(method,"http://127.0.0.1:8000/api/sites"+path,json=body)
    if r.status_code!=200:raise AssertionError("API rejected acceptance case; status "+str(r.status_code))
    return r.json()
   def case(key,payload,save=True):
    result=api("POST","/evaluate",payload)
    assert len(result["features"])==12 and all(shape(f["geometry"]).is_valid for f in result["features"])
    assert sum(result["weights"].values())==__import__("pytest").approx(1)
    assert all(abs(sum(r["contributions"].values())-r["score"])<1e-7 and 0<=r["score"]<=100 for r in result["rankings"])
    for c in result["candidates"]:assert c["provenance"]["source_id"] and c["feature_id"]
    saved=api("POST","/saved",{"calculation_id":result["calculation_id"]}) if save else None
    if saved:
     assert api("POST","/saved",{"calculation_id":result["calculation_id"]})["id"]==saved["id"]
     opened=api("GET","/saved/"+saved["id"])
     assert opened["features"]==result["features"] and opened["scenario"]==result["scenario"] and opened["sensitivity"]==result["sensitivity"]
     result=opened
    (DOCS/("phase6-"+key+"-result.json")).write_text(json.dumps(result,indent=2),encoding="utf-8")
    report[key]={"status":"passed","saved_id":saved["id"] if saved else None,"candidates":12,"weights":result["weights"],"ahp":result["ahp"],"top_three":[{"name":next(c["name"] for c in result["candidates"] if c["id"]==r["candidate_id"]),**r} for r in result["rankings"][:3]],"sensitivity_runs":len(result["sensitivity"]["runs"]),"routing":{k:result["routing"].get(k) for k in ("id","nodes","pairs","cached","upstream_requests","retrieved_at","unreachable_pairs")} if result.get("routing") else None}
    print(json.dumps({"case":key,**report[key]}),flush=True)
    (DOCS/"phase6-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return result
   gis=case("gis",base)
   network=copy.deepcopy(base);network["name"]="Phase 6 · six areas · road-accessibility WLC"
   weights=[.2,.15,.25,.25,.15]
   network["criteria"]=[{"id":k,"source":"network" if k.endswith("time_s") else "gis","direction":"benefit" if k=="industrial_count" else "cost","weight":w} for k,w in zip(("road_distance_m","warehouse_distance_m","industrial_count","port_time_s","airport_time_s"),weights)]
   network["targets"]={"port":{"coordinates":port["center"],"label":"Port Klang town OSM "+port["source_id"]+"; NOT a terminal/gate"},"airport":{"feature_id":airport,"label":"Mapped airport reference; NOT verified cargo gate"}}
   network["max_snap_m"]=2000
   wlc=case("road-wlc",network)
   again=api("POST","/evaluate",network);assert again["rankings"]==wlc["rankings"]
   ahp=copy.deepcopy(network);ahp["name"]="Phase 6 · six areas · consistent AHP";ahp["method"]="ahp";ahp["ahp_matrix"]=[[x/y for y in weights] for x in weights]
   ahp_result=case("road-ahp",ahp)
   assert ahp_result["ahp"]["cr"]<1e-9
   assert [r["candidate_id"] for r in ahp_result["rankings"]]==[r["candidate_id"] for r in wlc["rankings"]]
   assert all(abs(a["score"]-b["score"])<1e-7 for a,b in zip(ahp_result["rankings"],wlc["rankings"]))
   report["repeatability_and_wlc_ahp_parity"]="passed"
   report["areas"]=[{"name":a["area"],"candidate_count":len(a["candidates"]),"reference_only":True} for a in selection]
   report["status"]="passed"
   (DOCS/"phase6-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
   return 0
 except Exception as exc:
  report["status"]="failed";report["error_type"]=type(exc).__name__
  (DOCS/"phase6-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(safe_error(exc)));return 1
if __name__=="__main__":raise SystemExit(main())
