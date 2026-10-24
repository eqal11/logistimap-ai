"""Re-solve every review payload with the final imported source; read-only database access."""
import json,datetime
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from app.core.config import PROJECT_ROOT
from app.db.session import get_engine
from app.models.entities import OptimizationScenario
from app.schemas.optimization import Scenario
from app.optimization.jobs import calculate_solution
from app.db.verification import safe_error
def main():
 try:
  evidence=json.loads((PROJECT_ROOT/"docs"/"phase5-review-live.json").read_text(encoding="utf-8"))
  cases={k:v["scenario_id"] for k,v in evidence.items() if isinstance(v,dict) and "scenario_id" in v}
  with Session(get_engine()) as db:
   db.execute(text("SET TRANSACTION READ ONLY"))
   payloads={r.id:r.parameters["scenario"] for r in db.scalars(select(OptimizationScenario).where(OptimizationScenario.id.in_(list(cases.values()))))}
  results={}
  for case,key in cases.items():
   r=calculate_solution(Scenario.model_validate(payloads[key]))
   if case=="mandatory":
    assert not r["validated"] and not r["routes"] and len(r["unassigned"])==10
   else:
    assert r["validated"] and r["geometry_complete"] and r["road_geometry_constraints_verified"]
    assert r["summary"]["assigned_stops"]==evidence[case]["summary"]["assigned_stops"]
    assert r["summary"]["unassigned_stops"]==evidence[case]["summary"]["unassigned_stops"]
   results[case]={"status":"passed","solver_status":r["solver_status"],"result_status":r["status"],"matrix_cached":r["matrix"]["cached"],"matrix_retrieved_at":r["matrix"]["retrieved_at"],"geometry_complete":r["geometry_complete"],"road_geometry_constraints_verified":r["road_geometry_constraints_verified"],"summary":r["summary"],"routed_summary":r["routed_summary"]}
   print(json.dumps({"final_source_case":case,"status":"passed"}),flush=True)
  report={"verified_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"method":"Final source imported in new Python process; fresh OR-Tools solves on genuine OSRM matrices retrieved during this review, cached road geometry; no saved result overwritten","cases":results,"status":"passed"}
  (PROJECT_ROOT/"docs"/"phase5-review-final-source.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
  return 0
 except Exception as exc:
  print(json.dumps(safe_error(exc)));return 1
if __name__=="__main__":raise SystemExit(main())
