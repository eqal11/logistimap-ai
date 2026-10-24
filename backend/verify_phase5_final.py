"""Read-only legacy integrity, persistence, runtime, browser-export and secret checks."""
import csv,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
import httpx
from sqlalchemy import text
from shapely.geometry import shape
from app.core.config import PROJECT_ROOT,get_settings
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.services.osm import ssl_context
from verify_phase5_db import baseline
ROOT=PROJECT_ROOT

def main():
    engine=get_engine();current=baseline(engine)
    initial=json.loads((ROOT/"docs/phase5-database-baseline.json").read_text(encoding="utf-8"))
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"legacy_digests_unchanged":initial==current,
            "legacy_counts":{k:v["count"] for k,v in current.items()}}
    with engine.connect() as db:
        report["schema"]=verify_connection(db)
        report["features"]=dict(db.execute(text("SELECT count(*) total,count(*) FILTER(WHERE d.synthetic) synthetic,count(*) FILTER(WHERE NOT ST_IsValid(f.geometry) OR ST_SRID(f.geometry)<>4326) invalid FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id")).mappings().one())
        report["logistics_counts"]={t:db.scalar(text("SELECT count(*) FROM "+t)) for t in ("optimization_scenarios","logistics_depots","logistics_vehicles","logistics_stops","logistics_demands","optimization_jobs","optimization_solutions","vehicle_route_assignments","logistics_comparisons")}
        report["assignments"]=dict(db.execute(text("SELECT count(*) total,count(*) FILTER(WHERE geometry IS NOT NULL) with_geometry,count(*) FILTER(WHERE geometry IS NOT NULL AND (NOT ST_IsValid(geometry) OR ST_SRID(geometry)<>4326)) invalid FROM vehicle_route_assignments")).mappings().one())
        row=db.execute(text("SELECT s.id,s.parameters,r.result FROM optimization_scenarios s JOIN optimization_solutions r ON r.scenario_id=s.id WHERE s.name=:name ORDER BY r.created_at DESC LIMIT 1"),{"name":"Phase 5 browser verification · hypothetical demand"}).first()
        if row:
            r=row[2];report["browser_scenario"]={"id":row[0],"parameters_match":row[1]["scenario"]==r["scenario"],"status":r["status"],"summary":r["summary"],"routed_summary":r.get("routed_summary"),"matrix_pairs":r["matrix"]["pairs"],"geometry_complete":r["geometry_complete"],"road_constraints_verified":r.get("road_geometry_constraints_verified"),"demand_context":r["scenario"]["demand_context"]}
        else:r=None
    checks={}
    with httpx.Client(verify=ssl_context(),timeout=60) as client:
        for base in ("http://127.0.0.1:8000","http://127.0.0.1:4173"):
            for path in ("/health","/ready","/api/history/routes","/api/history/analyses","/api/optimization/scenarios","/api/network/capabilities"):
                response=client.get(base+path);checks[base+path]=response.status_code==200
        foreign=client.get("http://127.0.0.1:8000/api/optimization/scenarios",headers={"Origin":"https://attacker.example"})
        checks["foreign_origin_rejected"]=foreign.status_code==403
    report["runtime_checks"]=checks
    exports={}
    geo_path=ROOT/"docs/phase5-browser-routes.geojson"
    if r and geo_path.exists():
        geo=json.loads(geo_path.read_text(encoding="utf-8"))
        lines=[f for f in geo["features"] if f["geometry"]["type"] in ("LineString","MultiLineString")]
        expected={route["vehicle_id"]:route["geometry"] for route in r["routes"] if route["geometry"]}
        exports={"road_features":len(lines),"points":len(geo["features"])-len(lines),
            "valid":all(shape(f["geometry"]).is_valid for f in geo["features"]),
            "exact_saved_provider_geometry":len(lines)==len(expected) and all(f["geometry"]==expected.get(f["id"]) for f in lines),
            "vertices":sum(sum(len(line) for line in f["geometry"]["coordinates"]) for f in lines),
            "crs":geo.get("metadata",{}).get("crs"),"hypothetical_demand":geo.get("metadata",{}).get("scenario",{}).get("demand_context")=="hypothetical"}
        for kind in ("assignments","schedules","summary"):
            p=ROOT/("docs/phase5-browser-"+kind+".csv")
            if p.exists():
                with p.open(encoding="utf-8-sig",newline="") as file:rows=list(csv.DictReader(file))
                exports[kind]={"rows":len(rows),"attribution":all("OpenStreetMap" in x.get("attribution","") for x in rows),"demand_context":all(x.get("demand_context")=="hypothetical" for x in rows)}
    report["browser_exports"]=exports
    settings=get_settings();secrets=[v.get_secret_value() for v in (settings.database_password,settings.database_url) if v and v.get_secret_value()]
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
    (ROOT/"docs/phase5-secret-scan.json").write_text(json.dumps(scan,indent=2),encoding="utf-8")
    report["secret_scan"]=scan
    (ROOT/"docs/phase5-final-verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report))
    ok=report["legacy_digests_unchanged"] and report["features"]=={"total":5234,"synthetic":0,"invalid":0} and report["assignments"]["invalid"]==0 and all(checks.values()) and not matches and scan["backend_env_ignored"] and scan["backend_env_untracked"] and exports.get("exact_saved_provider_geometry") and all(exports.get(k,{}).get("attribution") for k in ("assignments","schedules","summary"))
    return 0 if ok else 1
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as e:print(json.dumps(safe_error(e)));raise SystemExit(1)
