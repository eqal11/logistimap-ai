"""Read-only final database/runtime/security verification; prints no credentials."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import httpx
from sqlalchemy import text
from app.core.config import get_settings
from app.db.session import get_engine
from app.db.verification import verify_connection, safe_error
from app.services.osm import ssl_context

ROOT=Path(__file__).resolve().parents[1]
def main():
    with get_engine().connect() as c:
        report=verify_connection(c)
        report["verified_at"]=datetime.now(timezone.utc).isoformat()
        report["features"]=dict(c.execute(text("""
          SELECT count(*) AS total, count(*) FILTER(WHERE d.synthetic) AS synthetic,
          count(*) FILTER(WHERE NOT ST_IsValid(f.geometry) OR ST_SRID(f.geometry)<>4326) AS invalid
          FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id
        """)).mappings().one())
        report["routes"]=dict(c.execute(text("""
          SELECT count(*) AS saved, count(*) FILTER(WHERE ST_IsValid(geometry)
            AND ST_SRID(geometry)=4326 AND GeometryType(geometry)='LINESTRING') AS valid_linestring_4326,
            count(*) FILTER(WHERE profile='car' AND (provenance->>'heavy_vehicle_verified')='false'
            AND (provenance->'selected_route'->>'distance_m')::float>0
            AND (provenance->'selected_route'->>'duration_s')::float>0) AS valid_metrics_car_provenance
          FROM routing_references
        """)).mappings().one())
        report["browser_save_verified"]=bool(c.execute(text("SELECT ST_IsValid(geometry) AND ST_SRID(geometry)=4326 FROM routing_references WHERE id=:id"),
            {"id":"085a56ed-e8cc-5c6b-99e7-681ea3b65024"}).scalar())
    with httpx.Client(verify=ssl_context(),timeout=30) as client:
        runtime={}
        for base in ("http://127.0.0.1:8000","http://127.0.0.1:4173"):
            for path in ("/health","/ready","/api/routing/provider"):
                response=client.get(base+path)
                runtime[base+path]=response.status_code
        schema=client.get("http://127.0.0.1:8000/openapi.json")
        schema.raise_for_status()
        (ROOT/"docs/openapi.json").write_text(json.dumps(schema.json(),indent=2),encoding="utf-8")
        report["runtime_http_statuses"]=runtime
    (ROOT/"docs/phase3-database-verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    settings=get_settings()
    secrets=[v.get_secret_value() for v in (settings.database_password,settings.database_url) if v and v.get_secret_value()]
    ignored={".git",".venv","node_modules",".cache","__pycache__",".pytest_cache"}
    checked=0; matches=[]
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.relative_to(ROOT).parts) or path.name==".env" or path.suffix in {".png",".jpg",".pyc",".exe",".dll",".woff2",".zip"}:continue
        try: data=path.read_text(encoding="utf-8")
        except (OSError,UnicodeError):continue
        checked+=1
        if any(secret in data for secret in secrets):matches.append(str(path.relative_to(ROOT)))
    env_ignored=subprocess.run(["git","check-ignore","-q","backend/.env"],cwd=ROOT,capture_output=True).returncode==0
    env_untracked=subprocess.run(["git","ls-files","backend/.env"],cwd=ROOT,capture_output=True,text=True).stdout.strip()==""
    scan={"checked_at":datetime.now(timezone.utc).isoformat(),"files_checked":checked,"secret_match_files":matches,
          "backend_env_ignored":env_ignored,"backend_env_untracked":env_untracked}
    (ROOT/"docs/phase3-secret-scan.json").write_text(json.dumps(scan,indent=2),encoding="utf-8")
    print(json.dumps({"database":report,"secret_scan":scan},ensure_ascii=False))
    return 0 if not matches and env_ignored and env_untracked and report["features"]=={"total":5234,"synthetic":0,"invalid":0} and report["browser_save_verified"] and all(v==200 for v in runtime.values()) else 1
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps(safe_error(exc)));raise SystemExit(1)
