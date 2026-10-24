"""Read-only database integrity and fresh API regression evidence. No migration calls."""
import json,hashlib,datetime
from pathlib import Path
import httpx
from sqlalchemy import text
from shapely.geometry import shape
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.core.config import PROJECT_ROOT
from app.services.osm import ssl_context
def main():
 try:
  report={"verified_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"migration_applied":False}
  baseline=json.loads((PROJECT_ROOT/"docs"/"phase5-review-baseline.json").read_text())
  with get_engine().connect() as db:
   db.execute(text("SET TRANSACTION READ ONLY"))
   report["database"]=verify_connection(db,full=True)
   retained={}
   for table,expected in baseline["tables"].items():
    actual=dict(db.execute(text('SELECT id,md5(row_to_json(t)::text) FROM public."'+table+'" t')).all())
    retained[table]={"before":len(expected),"now":len(actual),"missing_old":len(set(expected)-set(actual)),"changed_old":sum(actual.get(key)!=value for key,value in expected.items())}
   report["integrity"]=retained
   assert all(r["missing_old"]==r["changed_old"]==0 for r in retained.values())
   report["geometry_validity"]=dict(db.execute(text("select count(*) filter(where not ST_IsValid(geometry)) as invalid, count(*) filter(where ST_SRID(geometry)<>4326) as wrong_srid from vehicle_route_assignments where geometry is not null")).mappings().one())
   report["osm_validity"]=dict(db.execute(text("select count(*) as features,count(*) filter(where not ST_IsValid(f.geometry)) as invalid,count(*) filter(where d.synthetic) as synthetic from spatial_features f join datasets d on d.id=f.dataset_id")).mappings().one())
   report["category_counts"]=dict(db.execute(text("select category_id,count(*) from feature_categories group by category_id")).all())
   report["logistics_constraints"]={}
   for table in ("logistics_depots","logistics_stops","logistics_vehicles","logistics_demands","optimization_jobs","optimization_solutions","vehicle_route_assignments","logistics_comparisons"):
    report["logistics_constraints"][table]={"foreign_keys":db.execute(text("select count(*) from information_schema.table_constraints where table_schema='public' and table_name=:t and constraint_type='FOREIGN KEY'"),{"t":table}).scalar()}
  with httpx.Client(verify=ssl_context(),timeout=60) as client:
   def get(path):
    r=client.get("http://127.0.0.1:8000"+path);assert r.status_code==200;return r.json()
   report["api"]={"health":get("/health")["status"],"ready":get("/ready")["status"]}
   found=get("/api/industrial/features?categories=industrial&categories=warehouse&categories=port&bbox=101.2,2.85,101.8,3.5&limit=25")
   report["api"]["multi_category_search"]={k:found["meta"][k] for k in ("total","returned","category_counts")}
   assert found["features"]
   for kind in ("routes","analyses"):
    history=get("/api/history/"+kind)
    saved=get("/api/history/"+kind+"/"+history["items"][0]["id"])
    assert saved["features"] and all(shape(f["geometry"]).is_valid for f in saved["features"])
    report["api"][kind]={"saved_count":history["total"],"reloaded_features":len(saved["features"]),"geometry_valid":True}
   payload={"operation":"buffer","a":{"ids":["335bcf23-dccb-5eb4-b14a-737040e1e784"]},"distance_m":1000,"title":"Fresh review read-only spatial buffer"}
   raw=client.post("http://127.0.0.1:8000/api/spatial/analyze",json=payload)
   assert raw.status_code==200
   geo=raw.json();assert geo["features"] and all(shape(f["geometry"]).is_valid for f in geo["features"])
   report["api"]["buffer"]={"geometry_valid":True,"feature_count":len(geo["features"])}
   capabilities=get("/api/network/capabilities");assert not capabilities["isochrone"]
   assert client.post("http://127.0.0.1:8000/api/network/isochrone",json={}).status_code==501
   report["api"]["isochrone"]="unsupported (501); no fake polygon"
   bad=client.post("http://127.0.0.1:8000/api/optimization/import",json={"format":"geojson","content":"[]"})
   assert bad.status_code==422;report["api"]["malformed_geojson"]=422
   preview=client.get("http://127.0.0.1:4173/")
   report["preview_http_status"]=preview.status_code;assert preview.status_code==200
  report["status"]="passed"
  (PROJECT_ROOT/"docs"/"phase5-review-database.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
  print(json.dumps(report))
 except Exception as exc:
  print(json.dumps(safe_error(exc)));return 1
 return 0
if __name__=="__main__":raise SystemExit(main())
