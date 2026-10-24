"""Read-only acceptance/export against this local app and its configured PostGIS."""
import json
from datetime import datetime,timezone
from pathlib import Path
import httpx
from shapely.geometry import shape
from sqlalchemy import text
from app.core.config import PROJECT_ROOT
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.services.osm import ssl_context

def verify():
    with get_engine().connect() as connection:
        facts=verify_connection(connection)
        facts.update({
            "feature_count":connection.execute(text("SELECT count(*) FROM spatial_features")).scalar_one(),
            "synthetic_features":connection.execute(text("SELECT count(*) FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id WHERE d.synthetic")).scalar_one(),
            "category_counts":dict(connection.execute(text("SELECT category_id,count(*) FROM feature_categories GROUP BY category_id ORDER BY category_id")).all()),
            "geometry_counts":dict(connection.execute(text("SELECT ST_GeometryType(geometry),count(*) FROM spatial_features GROUP BY 1")).all()),
            "invalid_geometries":connection.execute(text("SELECT count(*) FROM spatial_features WHERE NOT ST_IsValid(geometry) OR ST_SRID(geometry)<>4326")).scalar_one(),
            "duplicate_source_ids":connection.execute(text("SELECT count(*) FROM (SELECT dataset_id,source_id FROM spatial_features GROUP BY 1,2 HAVING count(*)>1) x")).scalar_one(),
        })
    checks={}
    with httpx.Client(base_url="http://127.0.0.1:8000",timeout=35,verify=ssl_context()) as client:
        def get(path,params=None):
            response=client.get(path,params=params)
            if response.status_code!=200: raise RuntimeError("Local API acceptance request failed.")
            return response.json()
        checks["health_postgis"]=get("/health")["mode"]=="postgis"
        checks["ready_verified"]=get("/ready")["database_verified"] is True
        mixed=get("/api/industrial/features",params=[("categories",c) for c in ("industrial","warehouse","logistics_hub","port")]+[("bbox","101.25,2.72,101.87,3.4"),("limit","1000")])
        checks["all_four_categories_present"]=all(mixed["meta"]["category_counts"][c]>0 for c in ("industrial","warehouse","logistics_hub","port"))
        checks["multicategory_unique_ids"]=len({f["id"] for f in mixed["features"]})==len(mixed["features"])
        radius=get("/api/industrial/features",params={"center":"101.3966735,3.0027625","radius_km":5,"categories":"port","limit":1000})
        checks["actual_radius_port_query"]=radius["meta"]["total"]>0
        checks["empty_no_fallback"]=get("/api/industrial/features",params={"q":"__PHASE2_NONEXISTENT_FEATURE__"})["features"]==[]
        first=get("/api/industrial/features",params={"limit":1000})
        features=list(first["features"])
        for offset in range(1000,first["meta"]["total"],1000):
            features.extend(get("/api/industrial/features",params={"limit":1000,"offset":offset})["features"])
        checks["full_export_count"]=len(features)==facts["feature_count"]==len({f["id"] for f in features})
        checks["valid_real_wgs84_export"]=all(not f["properties"]["synthetic"] and f["properties"]["license"] and shape(f["geometry"]).is_valid for f in features)
        export={**first,"features":features,"meta":{**first["meta"],"limit":len(features),"returned":len(features),
                "has_more":False,"warnings":[w for w in first["meta"]["warnings"] if "paginated" not in w]}}
        target=PROJECT_ROOT/"data"/"exports"/"phase2-osm-malaysia.geojson"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(export,ensure_ascii=False),encoding="utf-8")
        jobs=get("/api/discovery/jobs")["jobs"]
        checks["all_import_jobs_completed"]=all(j["status"]=="completed" for j in jobs)
        facts["import_jobs"]=[{"id":j["id"],"label":j["parameters"]["label"],"status":j["status"],
            "valid_features":(j["report"] or {}).get("valid_features"),
            "skipped":(j["report"] or {}).get("skipped",{})} for j in jobs]
        path=PROJECT_ROOT/"docs"/"phase2-coverage.json"
        coverage=json.loads(path.read_text(encoding="utf-8"))
        initial={a["id"] for a in coverage["areas"] if "id" in a}
        coverage["supplemental_imports"]=[j for j in jobs if j["id"] not in initial]
        path.write_text(json.dumps(coverage,indent=2,ensure_ascii=False),encoding="utf-8")
        (PROJECT_ROOT/"docs"/"openapi.json").write_text(json.dumps(get("/openapi.json"),indent=2),encoding="utf-8")
    facts["http_acceptance_checks"]=checks
    facts["generated_at"]=datetime.now(timezone.utc).isoformat()
    (PROJECT_ROOT/"docs"/"phase2-database-verification.json").write_text(json.dumps(facts,indent=2),encoding="utf-8")
    print(json.dumps({"feature_count":facts["feature_count"],"category_counts":facts["category_counts"],
                      "geometry_counts":facts["geometry_counts"],"checks":checks,"export":"data/exports/phase2-osm-malaysia.geojson"}))
    return 0 if all(checks.values()) and facts["invalid_geometries"]==facts["duplicate_source_ids"]==facts["synthetic_features"]==0 else 1

if __name__=="__main__":
    try: raise SystemExit(verify())
    except Exception as exc:
        print(json.dumps(safe_error(exc)));raise SystemExit(1)
