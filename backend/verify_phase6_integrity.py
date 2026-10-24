"""Read-only final integrity + runtime evidence for Phase 6. Never prints configuration."""
import json,datetime,hashlib,asyncio
from collections import Counter
from sqlalchemy import text
import httpx
from app.core.config import PROJECT_ROOT,BACKEND_ROOT
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.services.osm import ssl_context
def main():
 try:
  docs=PROJECT_ROOT/"docs";baseline=json.loads((docs/"phase6-baseline.json").read_text(encoding="utf-8"))
  report={"verified_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
  with get_engine().connect() as db:
   db.execute(text("SET TRANSACTION READ ONLY"));report["database"]=verify_connection(db,full=True)
   integrity={}
   for table,old in baseline["tables"].items():
    now=[r[0] for r in db.execute(text('select md5(row_to_json(t)::text) from public."'+table+'" t'))]
    integrity[table]={"before":len(old),"now":len(now),"original_missing_or_changed":sum((Counter(old)-Counter(now)).values())}
   assert all(r["original_missing_or_changed"]==0 for r in integrity.values())
   report["integrity"]=integrity
   report["new_site_rows"]={t:db.execute(text('select count(*) from "'+t+'"')).scalar() for t in ("site_scenarios","site_candidates","site_evaluations","site_criterion_values")}
   report["site_geometry"]=dict(db.execute(text("select count(*) filter(where not ST_IsValid(geometry)) invalid,count(*) filter(where ST_SRID(geometry)<>4326) wrong_srid from site_candidates")).mappings().one())
   assert report["site_geometry"]=={"invalid":0,"wrong_srid":0}
  async def checks():
   async with httpx.AsyncClient(verify=ssl_context(),timeout=60) as c:
    paths=["/health","/ready","/api/sites/catalog","/api/sites/saved","/api/optimization/comparisons","/api/history/routes","/api/history/analyses","/api/industrial/features?categories=warehouse&categories=industrial&limit=1"]
    results=await asyncio.gather(*[c.get("http://127.0.0.1:8000"+p) for p in paths]);assert all(r.status_code==200 for r in results)
    preview=await c.get("http://127.0.0.1:4173/");assert preview.status_code==200
    assert any(f.name in preview.text for f in (PROJECT_ROOT/"frontend"/"dist"/"assets").glob("index-*.js"))
    return {"api":dict(zip(paths,[r.status_code for r in results])),"preview":200,"latest_build_served":True}
  report["runtime"]=asyncio.run(checks())
  previous=json.loads((docs/"phase5-review-secret-scan.json").read_text(encoding="utf-8"))
  report["env_unchanged"]=hashlib.sha256((BACKEND_ROOT/".env").read_bytes()).hexdigest()==previous["env_sha256"];assert report["env_unchanged"]
  report["phase5_browser_acceptance"]="pending";report["phase6_browser"]="unavailable; manual checklist provided";report["phase7_started"]=False;report["status"]="passed"
  (docs/"phase6-integrity.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
  from app.main import app
  (docs/"openapi.json").write_text(json.dumps(app.openapi(),indent=2),encoding="utf-8")
  print(json.dumps({k:v for k,v in report.items() if k not in ("integrity","database")}));return 0
 except Exception as e:print(json.dumps(safe_error(e)));return 1
if __name__=="__main__":raise SystemExit(main())
