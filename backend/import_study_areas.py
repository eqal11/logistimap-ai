"""One-off six-area import. Explicit execution only; never scheduled or run at startup."""
import argparse
import json
from datetime import datetime, timezone
from app.core.config import PROJECT_ROOT, get_settings
from app.db.verification import safe_error
from app.schemas.discovery import DiscoveryRequest, STUDY_TARGETS, DISCOVERY_CATEGORIES
from app.services.osm import geocode, ProviderError
from app.services.discovery import create_job, run_job, job_record

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--initial-six",action="store_true",required=True)
    args=parser.parse_args()
    if get_settings().data_mode!="postgis": raise SystemExit("PostGIS mode is required.")
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"radius_km":5,"areas":[],
            "note":"OSM place references, not verified industrial boundaries. Counts overlap across study areas/categories."}
    path=PROJECT_ROOT/"docs"/"phase2-coverage.json"
    for target in STUDY_TARGETS:
        try:
            matches=geocode(target["query"])["matches"]
            if not matches:
                item={"target":target,"status":"unresolved","message":"No geocoder match; no guessed coordinates used."}
            else:
                match=matches[0]
                payload=DiscoveryRequest(categories=DISCOVERY_CATEGORIES,center=match["center"],radius_km=5,label=target["name"])
                job_id=create_job(payload)
                print(json.dumps({"area":target["id"],"status":"started","job_id":job_id}),flush=True)
                run_job(job_id,payload)
                item={"target":target,"reference":match,**job_record(job_id)}
        except ProviderError as exc:
            item={"target":target,"status":"failed","message":str(exc)}
        except Exception as exc:
            item={"target":target,**safe_error(exc)}
        report["areas"].append(item)
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        summary=item.get("report") or {}
        print(json.dumps({"area":target["id"],"status":item["status"],"inserted":summary.get("inserted",0),
            "updated":summary.get("updated",0),"category_counts":summary.get("category_counts",{}),
            "message":summary.get("message")}),flush=True)
    return 0 if all(a["status"]=="completed" for a in report["areas"]) else 1

if __name__=="__main__":
    raise SystemExit(main())
