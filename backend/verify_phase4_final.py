"""Final read-only DB/runtime/export/secret checks. No credential output."""
import csv,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
import httpx
from sqlalchemy import text
from shapely.geometry import shape
from app.core.config import get_settings
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.services.osm import ssl_context
ROOT=Path(__file__).resolve().parents[1]
def main():
 with get_engine().connect() as c:
  report=verify_connection(c)
  report["verified_at"]=datetime.now(timezone.utc).isoformat()
  report["features"]=dict(c.execute(text("SELECT count(*) total,count(*) FILTER(WHERE d.synthetic) synthetic,count(*) FILTER(WHERE NOT ST_IsValid(f.geometry) OR ST_SRID(f.geometry)<>4326) invalid FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id")).mappings().one())
  baseline=json.loads((ROOT/"docs/phase4-scenarios.json").read_text(encoding="utf-8"))["baseline_route_ids"]
  now=set(c.execute(text("SELECT id FROM routing_references")).scalars())
  report["all_phase3_route_ids_preserved"]=set(baseline)<=now
  report["routes"]=dict(c.execute(text("SELECT count(*) total,count(*) FILTER(WHERE ST_IsValid(geometry) AND ST_SRID(geometry)=4326 AND GeometryType(geometry)='LINESTRING') valid,count(*) FILTER(WHERE provenance->>'archived_at' IS NOT NULL) archived FROM routing_references")).mappings().one())
  expected=[]
  phase3=json.loads((ROOT/"docs/phase3-routing-scenarios.json").read_text(encoding="utf-8"))
  for item in phase3["scenarios"]:
   if item.get("saved_id"):
    geo=json.loads((ROOT/item["export"]).read_text(encoding="utf-8"))["features"][0]["geometry"]
    expected.append((item["saved_id"],geo))
  browser3=json.loads((ROOT/"docs/phase3-browser-checks.json").read_text(encoding="utf-8"))
  alternative=json.loads((ROOT/"docs/phase3-browser-route-export.geojson").read_text(encoding="utf-8"))
  expected.append((browser3["alternatives"]["saved_id"],next(f["geometry"] for f in alternative["features"] if f["geometry"]["type"]=="LineString")))
  unchanged=[]
  for id,geometry in expected:
   actual=c.scalar(text("SELECT ST_AsGeoJSON(geometry) FROM routing_references WHERE id=:id"),{"id":id})
   unchanged.append(actual is not None and json.loads(actual)==geometry)
  report["phase3_geometry_snapshots_unchanged"]=len(unchanged)==8 and all(unchanged)
  report["analyses"]=dict(c.execute(text("SELECT count(*) total,count(*) FILTER(WHERE geometry IS NULL OR (ST_IsValid(geometry) AND ST_SRID(geometry)=4326)) valid,count(*) FILTER(WHERE summary->>'archived_at' IS NOT NULL) archived FROM analysis_results WHERE summary->>'kind'='phase4'")).mappings().one())
 checks={}
 with httpx.Client(verify=ssl_context(),timeout=65) as client:
  for base in ("http://127.0.0.1:8000","http://127.0.0.1:4173"):
   for path in ("/health","/ready","/api/history/routes","/api/network/capabilities"):
    r=client.get(base+path);checks[base+path]=r.status_code==200
  url="http://127.0.0.1:8000"
  empty=client.post(url+"/api/spatial/analyze",json={"operation":"grid","a":{"query":{"categories":["industrial"],"bbox":[118,5,118.01,5.01]}}})
  checks["empty_query_honest"]=empty.status_code==200 and empty.json()["features"]==[]
  large=client.post(url+"/api/spatial/analyze",json={"operation":"buffer","a":{"query":{"categories":["road"],"bbox":[99,1,120,8]}}})
  checks["large_input_rejected_without_partial_analysis"]=large.status_code==422
  invalid=client.post(url+"/api/spatial/analyze",json={"operation":"buffer","a":{"features":[{"id":"bad","geometry":{"type":"Polygon","coordinates":[[[101,3],[102,4],[102,3],[101,4],[101,3]]]}}]}})
  checks["invalid_polygon_rejected"]=invalid.status_code==422
  iso=client.post(url+"/api/network/isochrone",json={"minutes":20});checks["isochrone_explicitly_unsupported"]=iso.status_code==501
  (ROOT/"docs/openapi.json").write_text(json.dumps(client.get(url+"/openapi.json").json(),indent=2),encoding="utf-8")
 report["runtime_checks"]=checks
 geo=json.loads((ROOT/"docs/phase4-browser-buffer.geojson").read_text(encoding="utf-8"))
 with (ROOT/"docs/phase4-browser-buffer.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 report["browser_exports"]={"geojson_features":len(geo["features"]),"matched_count":geo["statistics"]["matched_count"],
  "all_geometries_valid":all(shape(f["geometry"]).is_valid for f in geo["features"]),"crs":geo["crs"],"csv_rows":len(rows),"csv_attribution_present":all("OpenStreetMap" in r.get("attribution","") for r in rows)}
 (ROOT/"docs/phase4-database-verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 s=get_settings();secrets=[v.get_secret_value() for v in (s.database_password,s.database_url) if v and v.get_secret_value()]
 ignore={".git",".venv","node_modules",".cache","__pycache__",".pytest_cache"};checked=0;matches=[]
 for p in ROOT.rglob("*"):
  if not p.is_file() or any(x in ignore for x in p.relative_to(ROOT).parts) or p.name==".env" or p.suffix in {".png",".jpg",".pyc",".exe",".dll",".woff2",".zip"}:continue
  try:data=p.read_text(encoding="utf-8")
  except (OSError,UnicodeError):continue
  checked+=1
  if any(secret in data for secret in secrets):matches.append(str(p.relative_to(ROOT)))
 scan={"checked_at":datetime.now(timezone.utc).isoformat(),"files_checked":checked,"secret_match_files":matches,
  "backend_env_ignored":subprocess.run(["git","check-ignore","-q","backend/.env"],cwd=ROOT,capture_output=True).returncode==0,
  "backend_env_untracked":not subprocess.run(["git","ls-files","backend/.env"],cwd=ROOT,capture_output=True,text=True).stdout.strip()}
 (ROOT/"docs/phase4-secret-scan.json").write_text(json.dumps(scan,indent=2),encoding="utf-8")
 print(json.dumps({"database":report,"secret_scan":scan}))
 return 0 if all(checks.values()) and report["features"]=={"total":5234,"synthetic":0,"invalid":0} and report["all_phase3_route_ids_preserved"] and report["phase3_geometry_snapshots_unchanged"] and report["browser_exports"]["csv_attribution_present"] and not matches else 1
if __name__=="__main__":
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps(safe_error(e)));raise SystemExit(1)
