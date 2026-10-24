"""Safe reviewed additive migration + allowlisted integrity evidence; no secrets in output."""
import json,hashlib
from pathlib import Path
from sqlalchemy import text
from app.db.session import get_engine
from app.db.migrate import migrate_safely
from app.db.verification import safe_error
from app.core.config import PROJECT_ROOT

def baseline(engine):
    out={}
    with engine.connect() as tx:
        for table in ("spatial_features","routing_references","analysis_jobs","analysis_results"):
            # Table names are a fixed source-code allowlist.
            row=tx.execute(text('SELECT count(*),md5(coalesce(string_agg(md5(row_to_json(t)::text),\'\' ORDER BY id),\'\')) FROM public.'+table+' t')).one()
            out[table]={"count":row[0],"digest":row[1]}
    return out
def main():
    try:
        engine=get_engine();before=baseline(engine)
        path=PROJECT_ROOT/"docs"/"phase5-database-baseline.json"
        if not path.exists():path.write_text(json.dumps(before,indent=2),encoding="utf-8")
        report=migrate_safely(engine);after=baseline(engine)
        if before!=after:raise RuntimeError("Legacy integrity changed")
        evidence={"status":"ok","migration":report,"legacy_unchanged":True,"legacy_counts":{k:v["count"] for k,v in after.items()}}
        (PROJECT_ROOT/"docs"/"phase5-database-verification.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
        print(json.dumps(evidence))
    except Exception as e:print(json.dumps(safe_error(e)));return 1
    return 0
if __name__=="__main__":raise SystemExit(main())
