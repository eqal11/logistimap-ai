"""Guarded API contract tests; no real network or database mutation."""
from types import SimpleNamespace
from uuid import uuid4
from app.api import optimization as api
from app.optimization import jobs
from app.routing.providers import RoutingError
import pytest

@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(api,"guard",lambda request:None)
    monkeypatch.setattr(api,"get_settings",lambda:SimpleNamespace(optimization_enabled=True,routing_enabled=True))

def test_scenario_roundtrip_and_safe_archive_confirmation(client,enabled,monkeypatch):
    key=str(uuid4())
    monkeypatch.setattr(api.repo,"get_scenario",lambda *a,**kw:{"id":key,"name":"Test snapshot","scenario":{}})
    assert client.get("/api/optimization/scenarios/"+key).json()["id"]==key
    assert client.post("/api/optimization/scenarios/"+key+"/archive",json={"confirmed":False}).status_code==422
    monkeypatch.setattr(api.repo,"archive",lambda *a:{"id":key,"status":"archived"})
    assert client.post("/api/optimization/scenarios/"+key+"/archive",json={"confirmed":True}).json()["status"]=="archived"

def test_solve_job_poll_and_provider_failure(client,enabled,monkeypatch):
    key=str(uuid4());job=str(uuid4())
    monkeypatch.setattr(jobs,"start",lambda *a:{"job_id":job,"status":"queued"})
    r=client.post("/api/optimization/scenarios/"+key+"/solve",json={});assert r.status_code==202 and r.json()["job_id"]==job
    monkeypatch.setattr(api.repo,"get_job",lambda *a:{"id":job,"status":"failed","stage":"Routing provider unavailable"})
    assert client.get("/api/optimization/jobs/"+job).json()["status"]=="failed"

def test_unknown_fields_and_unbounded_import_rejected(client,enabled):
    assert client.post("/api/optimization/import",json={"format":"csv","content":"x","path":"C:/secret"}).status_code==422
    assert client.post("/api/optimization/compare",json={"ids":["not-a-uuid","other"]}).status_code==422
    assert client.get("/api/optimization/scenarios?limit=100000").status_code==422

def test_database_errors_do_not_expose_credentials(client,enabled,monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    def fail(*a,**kw):raise SQLAlchemyError("TEST-SECRET-sentinel")
    monkeypatch.setattr(api.repo,"list_scenarios",fail)
    r=client.get("/api/optimization/scenarios");assert r.status_code==503 and "TEST-SECRET" not in r.text

def test_background_worker_lock_prevents_concurrent_jobs(enabled,monkeypatch):
    monkeypatch.setattr(jobs,"active","already-running")
    with pytest.raises(RoutingError):jobs.start(str(uuid4()))

def test_matrix_and_import_require_explicit_road_mode(client,monkeypatch):
    # Existing guard must reject requests from a foreign Origin even in live mode.
    import app.api.analytics as analytics
    monkeypatch.setattr(analytics,"get_settings",lambda:SimpleNamespace(analytics_enabled=True,data_mode="postgis",cors_origins=["http://localhost:5173"]))
    r=client.get("/api/optimization/scenarios",headers={"Origin":"https://attacker.example"})
    assert r.status_code==403


def test_oversized_optimization_body_rejected_before_parsing(client):
    response=client.post("/api/optimization/import",content=b"x"*1_500_001,headers={"Content-Type":"application/json"})
    assert response.status_code==413


@pytest.mark.parametrize('content',['[]','null','{"type":"FeatureCollection","features":[null]}'])
def test_malformed_geojson_returns_422_not_500(client,enabled,content):
    response=client.post('/api/optimization/import',json={'format':'geojson','content':content})
    assert response.status_code==422


def test_comparison_history_and_snapshot_endpoints(client,enabled,monkeypatch):
    key=str(uuid4())
    monkeypatch.setattr(api.repo,"list_comparisons",lambda limit,offset:{"items":[{"id":key,"name":"TEST comparison"}],"total":1,"limit":limit,"offset":offset})
    monkeypatch.setattr(api.repo,"get_comparison",lambda id:{"id":id,"rows":[],"name":"TEST comparison"})
    monkeypatch.setattr(api.repo,"comparison_solutions",lambda id:{"comparison_id":id,"items":[]})
    assert client.get("/api/optimization/comparisons?limit=10").json()["items"][0]["id"]==key
    assert client.get("/api/optimization/comparisons/"+key).json()["id"]==key
    assert client.get("/api/optimization/comparisons/"+key+"/solutions").json()["comparison_id"]==key
    assert client.get("/api/optimization/comparisons?limit=1000").status_code==422
    assert client.get("/api/optimization/comparisons/not-a-uuid").status_code==422

def test_missing_and_unavailable_historical_comparison_are_explicit(client,enabled,monkeypatch):
    def missing(*args):raise api.repo.ComparisonNotFound("Saved comparison not found")
    monkeypatch.setattr(api.repo,"get_comparison",missing)
    assert client.get("/api/optimization/comparisons/"+str(uuid4())).status_code==404
    def unavailable(*args):raise api.repo.ComparisonUnavailable("Exact historical solution unavailable; no substitute")
    monkeypatch.setattr(api.repo,"comparison_solutions",unavailable)
    r=client.get("/api/optimization/comparisons/"+str(uuid4())+"/solutions")
    assert r.status_code==409 and "no substitute" in r.json()["error"]["message"]

def test_comparison_history_never_exposes_database_exception(client,enabled,monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    def fail(*args):raise SQLAlchemyError("TEST-SECRET-comparison")
    monkeypatch.setattr(api.repo,"list_comparisons",fail)
    r=client.get("/api/optimization/comparisons")
    assert r.status_code==503 and "TEST-SECRET" not in r.text
