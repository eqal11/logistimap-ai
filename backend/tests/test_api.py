import pytest
from app.core.config import get_settings
from app.main import settings
from app.schemas.spatial import SearchParams
from app.services.features import search


def test_health_and_explicit_limited_mode(client):
    body = client.get("/health").json()
    assert body["mode"] == "fixture"
    assert body["database_configured"] is False
    assert client.get("/ready").json()["database_verified"] is False
    assert "DATABASE_URL" not in str(body)


def test_all_geometry_types_and_provenance(client):
    response = client.get("/api/industrial/features")
    assert response.status_code == 200
    data = response.json()
    assert {f["geometry"]["type"] for f in data["features"]} == {"Point", "LineString", "Polygon"}
    assert all(f["properties"]["synthetic"] for f in data["features"])
    assert all(f["properties"]["source_id"] and f["properties"]["imported_at"] for f in data["features"])
    assert data["meta"]["crs"] == "EPSG:4326"
    assert data["meta"]["returned"] == data["meta"]["total"] == len(data["features"])


def test_all_requested_categories_preserved_without_duplicates(client):
    data = client.get("/api/industrial/features", params=[
        ("categories", "warehouse"), ("categories", "industrial"),
        ("categories", "logistics_hub"), ("categories", "port"),
    ]).json()
    counts = data["meta"]["category_counts"]
    assert all(counts[c] > 0 for c in ["warehouse", "industrial", "logistics_hub", "port"])
    assert data["meta"]["missing_categories"] == []
    ids = [f["id"] for f in data["features"]]
    assert len(ids) == len(set(ids))
    assert next(f for f in data["features"] if f["id"] == "test-w1")["properties"]["categories"] == ["warehouse", "logistics_hub"]


def test_missing_categories_are_reported(client):
    data = client.get("/api/industrial/features?categories=rail&categories=warehouse").json()
    assert data["meta"]["category_counts"] == {"rail": 0, "warehouse": 3}
    assert data["meta"]["missing_categories"] == ["rail"]


def test_empty_results_do_not_substitute_data(client):
    data = client.get("/api/industrial/features?q=unmapped-name").json()
    assert data["features"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["mode"] == "fixture"


def test_bbox_uses_geometry_intersection(client):
    data = client.get("/api/industrial/features?bbox=101.46,3.12,101.47,3.13").json()
    assert "test-z1" in [f["id"] for f in data["features"]]
    assert "test-a1" not in [f["id"] for f in data["features"]]


def test_radius_units_and_pagination(client):
    data = client.get("/api/industrial/features?center=101.455,3.07&radius_km=0.1").json()
    assert [f["id"] for f in data["features"]] == ["test-w1"]
    page = client.get("/api/industrial/features?limit=2&offset=1").json()
    assert len(page["features"]) == 2 and page["meta"]["has_more"] is True
    assert page["meta"]["total"] == 11
    assert sum(page["meta"]["category_counts"].values()) > 2


@pytest.mark.parametrize("query", [
    "bbox=1,2,3", "bbox=10,4,2,5", "bbox=nan,1,3,4", "bbox=-181,0,10,20",
    "center=101,95&radius_km=1", "radius_km=2", "center=101,3",
    "categories=unknown", "limit=1001", "radius_km=-1", "offset=-1",
])
def test_invalid_queries_rejected(client, query):
    assert client.get("/api/industrial/features?" + query).status_code == 422


def test_database_failure_never_falls_back_to_fixture(client, monkeypatch):
    monkeypatch.setattr(settings, "data_mode", "postgis")
    response = client.get("/api/industrial/features")
    assert response.status_code == 503
    assert "fixture fallback" in response.json()["error"]["message"]
    assert client.get("/ready").status_code == 503


def test_no_arbitrary_geoai_or_upload_endpoints(client):
    for path in ["/api/geoai/query", "/api/data/import"]:
        assert client.post(path, json={"code": "print(1)", "sql": "SELECT 1"}).status_code == 404
    assert client.post("/api/routing/route",json={"code":"print(1)","sql":"SELECT 1"}).status_code==422
    capabilities = client.get("/api/capabilities").json()
    assert "geoai_copilot" in capabilities["available"]


def test_cors_restricted_to_configured_origin(client):
    allowed = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    blocked = client.get("/health", headers={"Origin": "https://untrusted.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-origin" not in blocked.headers
    assert allowed.headers["X-Request-ID"]


def test_rate_guard_returns_retry_after(client, monkeypatch):
    monkeypatch.setattr(settings, "request_limit_per_minute", 10)
    for _ in range(10):
        assert client.get("/health").status_code == 200
    response = client.get("/health")
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"
