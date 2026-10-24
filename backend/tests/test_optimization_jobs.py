import copy
from app.optimization import jobs
from app.schemas.optimization import Scenario
from app.routing.providers import RoutingError

def payload():
    return Scenario(name="Synthetic job test only",depots=[{"id":"d","name":"test depot","coordinates":[101,3]}],
        vehicles=[{"id":"v","name":"test vehicle","capacity":4,"start_depot":"d","end_depot":"d","cost_per_km":2}],
        stops=[{"id":"s","name":"test stop","coordinates":[101.1,3],"demand":2}],solver_seconds=1)
def matrix():return {"id":"test","distances":[[0,100],[150,0]],"durations":[[0,10],[15,0]],"nodes":2,"pairs":4}
def test_geometry_failure_retains_solution_but_never_invents_lines(monkeypatch):
    monkeypatch.setattr(jobs,"road_matrix",lambda *a,**kw:matrix())
    def fail(*a,**kw):raise RoutingError("Provider unavailable")
    monkeypatch.setattr(jobs,"calculate",fail)
    r=jobs.calculate_solution(payload())
    assert r["validated"] and r["routes"][0]["geometry"] is None and not r["geometry_complete"] and r["routed_summary"] is None
    assert "no straight-line" in " ".join(r["warnings"])

def test_final_road_geometry_revalidates_limits_and_cost(monkeypatch):
    monkeypatch.setattr(jobs,"road_matrix",lambda *a,**kw:matrix())
    geometry={"type":"LineString","coordinates":[[101,3],[101.05,3.01],[101.1,3],[101.05,3.01],[101,3]]}
    monkeypatch.setattr(jobs,"calculate",lambda *a,**kw:{"routes":[{"geometry":geometry,"distance_m":300,"duration_s":30,"legs":[{"distance_m":100,"duration_s":10},{"distance_m":200,"duration_s":20}]}]})
    r=jobs.calculate_solution(payload())
    assert r["routes"][0]["road_geometry_constraints_verified"]
    assert r["summary"]["distance_m"]==250 and r["routed_summary"]["distance_m"]==300
    assert r["routed_summary"]["estimated_cost"]==.6

def test_final_geometry_timing_violation_is_not_dispatch_verified(monkeypatch):
    monkeypatch.setattr(jobs,"road_matrix",lambda *a,**kw:matrix())
    monkeypatch.setattr(jobs,"calculate",lambda *a,**kw:{"routes":[{"geometry":{"type":"LineString","coordinates":[[101,3],[101.1,3],[101,3]]},"distance_m":300,"duration_s":100,"legs":[{"distance_m":100,"duration_s":50},{"distance_m":200,"duration_s":50}]}]})
    s=payload();s.vehicles[0].max_duration_s=40
    r=jobs.calculate_solution(s)
    assert r["validated"] and not r["routes"][0]["road_geometry_constraints_verified"]
    assert r["routed_summary"] is None

def test_worker_persists_safe_failure_stage(monkeypatch):
    states=[]
    monkeypatch.setattr(jobs.repo,"update_job",lambda key,status,stage:states.append((status,stage)))
    monkeypatch.setattr(jobs.repo,"get_scenario",lambda id:{"scenario":payload().model_dump(mode="json")})
    monkeypatch.setattr(jobs,"calculate_solution",lambda *args:(_ for _ in ()).throw(RuntimeError("TEST-SECRET-never-save")))
    jobs.worker("test-job","test-scenario")
    assert states[-1][0]=="failed" and "TEST-SECRET" not in str(states)
