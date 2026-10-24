"""Provider responses here are synthetic contract fixtures, never live route fallbacks."""
import copy
import json
import pytest
import httpx
from pydantic import ValidationError
from shapely.geometry import LineString
from app.core.config import get_settings
from app.routing import providers,service
from app.schemas.routing import GEOD,RoutePoint,RouteRequest,SaveRouteRequest

POINTS=[{"coordinates":[101,3],"label":"TEST origin"},{"coordinates":[101.002,3],"label":"TEST destination"}]

def raw_route():
    coords=[[101,3],[101.001,3.0002],[101.002,3]]
    length=GEOD.geometry_length(LineString(coords))
    return {"code":"Ok","waypoints":[{"location":p["coordinates"],"distance":0,"name":"TEST road"} for p in POINTS],
        "routes":[{"distance":length,"duration":30,"geometry":{"type":"LineString","coordinates":coords},
            "legs":[{"distance":length,"duration":30,"summary":"TEST road"}]}]}

@pytest.mark.parametrize("value",[[True,3],[181,3],[101,91],[float("nan"),3],[101,float("inf")],[101],[101,3,0]])
def test_bad_coordinates_rejected(value):
    with pytest.raises(ValidationError): RoutePoint(coordinates=value)

@pytest.mark.parametrize("body",[
    {"points":[]},{"points":[{"coordinates":[101,3]}]},
    {"points":[{"coordinates":[101,3]}]*9},
    {"points":[{"coordinates":[101,3]},{"coordinates":[101.1,3]}],"profile":"truck"},
    {"points":[{"coordinates":[101,3],"feature_id":"not-a-uuid"},{"coordinates":[101.1,3]}]},
    {"points":[{"coordinates":[101,3]},{"coordinates":[101.1,3]}],"sql":"SELECT 1"},
    {"points":[{"coordinates":[101,3]},{"coordinates":[101.1,3]}],"max_snap_m":2001},
])
def test_invalid_or_unsupported_route_contract_rejected(client,body):
    assert client.post("/api/routing/route",json=body).status_code==422

def test_real_provider_metrics_and_geometry_are_preserved():
    raw=raw_route()
    result=providers.normalize_osrm(raw,POINTS,1000)
    assert result["routes"][0]["geometry"]==raw["routes"][0]["geometry"]
    assert result["routes"][0]["distance_m"]==raw["routes"][0]["distance"]
    assert result["routes"][0]["duration_s"]==30
    assert result["waypoints"][0]["snapped_coordinates"]==[101,3]

@pytest.mark.parametrize("mutation",["no_geometry","wrong_type","wrong_distance","nan_duration","missing_waypoint","excess_snap","wrong_endpoint","missing_leg"])
def test_invalid_provider_result_is_not_presented_as_road_route(mutation):
    raw=raw_route()
    if mutation=="no_geometry": del raw["routes"][0]["geometry"]
    if mutation=="wrong_type": raw["routes"][0]["geometry"]["type"]="Polygon"
    if mutation=="wrong_distance": raw["routes"][0]["distance"]=10000
    if mutation=="nan_duration": raw["routes"][0]["duration"]=float("nan")
    if mutation=="missing_waypoint": raw["waypoints"].pop()
    if mutation=="excess_snap": raw["waypoints"][0]["distance"]=10000
    if mutation=="wrong_endpoint": raw["routes"][0]["geometry"]["coordinates"][0]=[101.01,3]
    if mutation=="missing_leg": raw["routes"][0]["legs"]=[]
    with pytest.raises(providers.RoutingError): providers.normalize_osrm(raw,POINTS,1000)

@pytest.mark.parametrize("code",["NoRoute","NoSegment"])
def test_unroutable_points_return_clear_error_without_straight_line(code):
    with pytest.raises(providers.RoutingError) as error:
        providers.normalize_osrm({"code":code},POINTS,1000)
    assert error.value.status==422

def test_same_point_and_unbounded_chain_rejected_before_provider_call():
    with pytest.raises(providers.RoutingError,match="1 meter"):
        service.resolve_points(RouteRequest(points=[{"coordinates":[101,3]}]*2))
    with pytest.raises(providers.RoutingError,match="3,000"):
        service.resolve_points(RouteRequest(points=[{"coordinates":[101,3]},{"coordinates":[-80,3]}]))

def test_calculation_cache_prevents_repeated_provider_requests(tmp_path,monkeypatch):
    monkeypatch.setattr(get_settings(),"provider_cache_dir",tmp_path)
    calls=[]
    class Provider:
        name="test-osrm"
        def route(self,points,alternatives,max_snap_m):
            calls.append((points,alternatives,max_snap_m))
            return providers.normalize_osrm(raw_route(),points,max_snap_m)
    monkeypatch.setattr(service,"get_provider",lambda:Provider())
    request=RouteRequest(points=POINTS)
    first=service.calculate(request);second=service.calculate(request)
    assert len(calls)==1 and not first["cached"] and second["cached"]
    assert first["calculation_id"]==second["calculation_id"]
    assert not first["heavy_vehicle_verified"] and first["profile"]=="car"
    assert "no alternatives" in " ".join(first["warnings"]).lower()
    assert first["retrieved_at"]==second["retrieved_at"]

def test_multistop_preserves_order_and_does_not_claim_alternatives(tmp_path,monkeypatch):
    monkeypatch.setattr(get_settings(),"provider_cache_dir",tmp_path)
    points=[POINTS[0],{"coordinates":[101.001,3.0002],"label":"TEST via"},POINTS[1]]
    calls=[]
    class Provider:
        name="test"
        def route(self,stops,alternatives,max_snap_m):
            calls.append((stops,alternatives))
            raw=raw_route()
            raw["waypoints"]=[{"location":p["coordinates"],"distance":0} for p in stops]
            length=raw["routes"][0]["distance"]/2
            raw["routes"][0]["legs"]=[{"distance":length,"duration":15}]*2
            return providers.normalize_osrm(raw,stops,max_snap_m)
    monkeypatch.setattr(service,"get_provider",lambda:Provider())
    result=service.calculate(RouteRequest(points=points))
    assert not calls[0][1] and not result["alternatives_queried"]
    assert [w["label"] for w in result["waypoints"]]==["TEST origin","TEST via","TEST destination"]
    assert len(result["routes"][0]["legs"])==2

def test_osrm_adapter_sends_geojson_radiuses_and_enforces_cooldown(tmp_path,monkeypatch):
    original=httpx.Client
    calls=[]
    def response(request):
        calls.append(request);return httpx.Response(429,headers={"Retry-After":"120"})
    monkeypatch.setattr(providers.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(response)))
    monkeypatch.setattr(providers,"last_request",0)
    monkeypatch.setattr(providers,"cooldown_until",0)
    monkeypatch.setattr(providers,"request_times",providers.deque())
    with pytest.raises(providers.RoutingError,match="429"): providers.OSRMProvider().route(POINTS,True,1000)
    with pytest.raises(providers.RoutingError,match="cooling"): providers.OSRMProvider().route(POINTS,True,1000)
    assert len(calls)==1
    params=calls[0].url.params
    assert params["geometries"]=="geojson" and params["overview"]=="full" and params["radiuses"]=="1000;1000"

def test_api_provider_failure_is_clear_and_does_not_fallback(client,monkeypatch):
    def fail(request): raise providers.RoutingError("Routing provider timed out; no straight-line fallback.",504)
    monkeypatch.setattr(service,"calculate",fail)
    result=client.post("/api/routing/route",json={"points":POINTS})
    assert result.status_code==504 and "fallback" in result.json()["error"]["message"]
    assert "routes" not in result.json()

def test_local_access_and_fixture_feature_restrictions(client):
    assert client.post("/api/routing/route",json={"points":POINTS},headers={"Origin":"https://untrusted.example"}).status_code==403
    assert client.get("/api/routing/features/00000000-0000-0000-0000-000000000001/anchor").status_code==409
    assert client.get("/api/routing/provider").json()["heavy_vehicle_verified"] is False

def test_save_rejects_client_geometry_and_arbitrary_cache_paths(client):
    assert client.post("/api/routing/saved",json={"geometry":{"type":"LineString","coordinates":[]},"calculation_id":"../.env","route_index":0}).status_code==422
    with pytest.raises(providers.RoutingError,match="Invalid calculation"): service.cache_path("../.env")
    with pytest.raises(providers.RoutingError,match="expired"):
        service.save_calculation(SaveRouteRequest(calculation_id="0"*64,route_index=0))
