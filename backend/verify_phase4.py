"""Bounded live Phase 4 acceptance. No credentials or raw exceptions printed."""
import json,time
from datetime import datetime,timezone
from pathlib import Path
import httpx
from shapely.geometry import shape,box,mapping
from sqlalchemy import text
from app.db.session import get_engine
from app.db.verification import safe_error,verify_connection
from app.services.osm import ssl_context
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/phase4-scenarios.json"
def main():
 report={"started_at":datetime.now(timezone.utc).isoformat(),"scenarios":[]}
 with get_engine().connect() as c:
  report["baseline_features"]=c.scalar(text("SELECT count(*) FROM spatial_features"))
  report["baseline_route_ids"]=list(c.execute(text("SELECT id FROM routing_references ORDER BY id")).scalars())
 with httpx.Client(base_url="http://127.0.0.1:8000",verify=ssl_context(),timeout=65) as client:
  def get(path,params=None):
   r=client.get(path,params=params);r.raise_for_status();return r.json()
  def post(path,data):
   r=client.post(path,json=data)
   if r.status_code!=200:raise ValueError("HTTP "+str(r.status_code)+" "+r.json().get("error",{}).get("message","Unavailable"))
   return r.json()
  def query(cats,**extra):return {"query":{"categories":cats,**extra}}
  def geometry(g):return {"features":[{"id":"user-klang-study-area","name":"User-defined Klang study rectangle; not verified boundary","geometry":json.loads(json.dumps(mapping(g)))}]}
  def record(key,label,fn):
   try:
    r=fn()
    if isinstance(r,dict) and "features" in r:
     valid=all(shape(f["geometry"]).is_valid and not shape(f["geometry"]).is_empty for f in r["features"])
     if not valid:raise ValueError("Invalid output geometry")
     path=ROOT/"data/exports/analyses"/(key+".geojson");path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(r,ensure_ascii=False),encoding="utf-8")
     item={"id":key,"label":label,"status":"passed","title":r.get("title"),"feature_count":len(r["features"]),"statistics":r.get("statistics"),"rows":r.get("rows",[])[:20],"inputs":r.get("inputs"),"calculation_id":r.get("calculation_id"),"export":str(path.relative_to(ROOT))}
    else:item={"id":key,"label":label,"status":"passed",**(r or {})}
   except Exception as e:
    # No DB exceptions are rendered; HTTP messages above are allowlisted API errors.
    item={"id":key,"label":label,"status":"failed","error_type":type(e).__name__}
   report["scenarios"].append(item);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
   print(json.dumps({k:item.get(k) for k in ("id","status","feature_count","error_type")}),flush=True)
   return item
  town=get("/api/locations/search",{"q":"Tanjong Malim, Perak, Malaysia"})["matches"][0]
  shah=get("/api/locations/search",{"q":"Shah Alam, Selangor, Malaysia"})["matches"][0]
  rawang=get("/api/locations/search",{"q":"Rawang, Selangor, Malaysia"})["matches"][0]
  port=get("/api/locations/search",{"q":"Port Klang, Selangor, Malaysia"})["matches"][0]
  a=record("A","Industrial facilities within 10 km of Tanjong Malim",lambda:post("/api/spatial/analyze",{"operation":"buffer","title":"Tanjong Malim 10 km reference buffer",
    "a":geometry(__import__("shapely").geometry.Point(town["center"])),"b":query(["industrial"],center=town["center"],radius_km=10),"distance_m":10000}))
  warehouses=get("/api/industrial/features",{"categories":"warehouse","center":",".join(map(str,shah["center"])),"radius_km":10,"limit":100})["features"]
  if not warehouses:raise ValueError("No warehouse mapped around Shah Alam")
  warehouse=warehouses[0]
  report["shah_warehouse"]={"id":warehouse["id"],"name":warehouse["properties"]["name"],"source_id":warehouse["properties"]["source_id"]}
  record("B","5 km warehouse buffer and industrial counts near Shah Alam",lambda:post("/api/spatial/analyze",{"operation":"buffer","title":"Shah Alam warehouse 5 km buffer","a":{"ids":[warehouse["id"]]},
    "b":query(["industrial"],bbox=[101.25,2.72,101.87,3.4]),"distance_m":5000}))
  c=record("C","Clip industrial land-use to user-defined Klang rectangle",lambda:post("/api/spatial/analyze",{"operation":"clip","title":"Klang user-boundary industrial clip",
    "a":query(["industrial_park"],bbox=[101.25,2.72,101.87,3.4]),"b":geometry(box(101.35,3.0,101.5,3.12))}))
  facility="335bcf23-dccb-5eb4-b14a-737040e1e784"
  record("D","Nearest mapped warehouse to Canpac by footprint distance",lambda:post("/api/spatial/analyze",{"operation":"nearest","title":"Canpac geographic warehouse proximity",
    "a":{"ids":[facility]},"b":query(["warehouse"],bbox=[101.25,2.72,101.87,3.4])}))
  record("E","Rawang vs Shah Alam mapped industrial density, equal 5 km windows",lambda:post("/api/analysis/regions",{"origins":[{"coordinates":p["center"],"label":p["name"][:160]} for p in (rawang,shah)],"radius_km":5,"categories":["industrial","industrial_park"]}))
  record("F","Road-network matrix Canpac and warehouse to Port Klang",lambda:post("/api/routing/matrix",{"origins":[{"feature_id":facility},{"feature_id":warehouse["id"]}],
    "destinations":[{"coordinates":port["center"],"label":port["name"][:160]}],"score_reference_minutes":60}))
  record("G","Actual industrial land-use / user rectangle intersection export",lambda:post("/api/spatial/analyze",{"operation":"intersection","title":"Klang industrial intersection",
    "a":query(["industrial_park"],bbox=[101.35,3.0,101.5,3.12]),"b":geometry(box(101.38,3.02,101.46,3.10))}))
  def save_reload():
   key=c.get("calculation_id");saved=post("/api/analysis/saved",{"calculation_id":key})
   loaded=get("/api/history/analyses/"+saved["id"])
   original=json.loads((ROOT/c["export"]).read_text(encoding="utf-8"))
   assert loaded["features"]==original["features"] and loaded["statistics"]==original["statistics"]
   assert post("/api/analysis/saved",{"calculation_id":key})["id"]==saved["id"]
   report["saved_analysis_id"]=saved["id"]
   return {"saved_id":saved["id"],"reload_geometry_identical":True,"idempotent":True}
  record("H","Save analysis, reload and idempotency in Supabase",save_reload)
  def saved_route():
   page=get("/api/history/routes");assert page["total"]>=len(report["baseline_route_ids"])
   id=next(i["id"] for i in page["items"] if i["id"] in report["baseline_route_ids"])
   loaded=get("/api/history/routes/"+id)
   assert shape(loaded["features"][0]["geometry"]).geom_type=="LineString"
   assert loaded["statistics"]["distance_m"]>0 and loaded["statistics"]["duration_s"]>0
   return loaded
  record("I","Reopen existing Phase 3 route geometry and metrics",saved_route)
  unsupported=client.post("/api/network/isochrone",json={"minutes":20})
  report["scenarios"].append({"id":"J","label":"Real network isochrone","status":"unsupported" if unsupported.status_code==501 else "failed",
    "http_status":unsupported.status_code,"reason":"OSRM route/table has no isochrone capability; imported source lines are not a validated routing graph."})
  for op in ("clusters","grid","dissolve","union","difference","spatial_join","aggregate"):
   record("extra-"+op,op+" on real mapped industrial geometry",lambda op=op:post("/api/spatial/analyze",{"operation":op,"title":"Live "+op,
    "a":query(["industrial"],center=shah["center"],radius_km=10),
    **({"b":geometry(box(101.4,3.0,101.6,3.15))} if op in ("difference","union","spatial_join","aggregate") else {}),"eps_m":1000,"min_points":3,"grid_m":1000}))
  with get_engine().connect() as conn:
   report["database"]=verify_connection(conn)
   report["features_preserved"]=conn.scalar(text("SELECT count(*) FROM spatial_features"))==report["baseline_features"]==5234
   now_ids=set(conn.execute(text("SELECT id FROM routing_references")).scalars());report["phase3_routes_preserved"]=set(report["baseline_route_ids"])<=now_ids
   report["synthetic_features"]=conn.scalar(text("SELECT count(*) FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id WHERE d.synthetic"))
  (ROOT/"docs/openapi.json").write_text(json.dumps(get("/openapi.json"),indent=2),encoding="utf-8")
 report["finished_at"]=datetime.now(timezone.utc).isoformat();OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 return 0 if all(s["status"]=="passed" for s in report["scenarios"] if s["id"]!="J") and report["features_preserved"] and report["phase3_routes_preserved"] else 1
if __name__=="__main__":
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps(safe_error(e)));raise SystemExit(1)
