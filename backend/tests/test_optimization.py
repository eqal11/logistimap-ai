"""Offline tests use explicit synthetic numeric matrices, never returned as real road data."""
import copy,json
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.schemas.optimization import Scenario,ImportLocations
from app.optimization.solver import solve,validate,OptimizationError,cost_components
from app.optimization.imports import import_locations
from app.optimization import matrix as mx
from app.routing.providers import RoutingError

def scenario(count=3,vehicles=2,capacity=4,**kw):
    data=dict(name="Synthetic solver unit test only",depots=[dict(id="d",name="test depot",coordinates=[101,3])],
        vehicles=[dict(id="v"+str(i),name="test vehicle "+str(i),capacity=capacity,start_depot="d",end_depot="d") for i in range(vehicles)],
        stops=[dict(id="s"+str(i),name="test stop "+str(i),coordinates=[101+i*.01,3],demand=2) for i in range(count)],solver_seconds=1)
    data.update(kw);return Scenario.model_validate(data)

def numeric(s):
    n=len(s.depots)+len(s.stops)
    return {"distances":[[0 if i==j else 100+abs(i-j)*10+i for j in range(n)] for i in range(n)],
            "durations":[[0 if i==j else 10+abs(i-j)+i for j in range(n)] for i in range(n)]}

def test_cvrp_capacity_partition_and_units():
    s=scenario();m=numeric(s);r=solve(s,m)
    assert r["validated"] and not r["unassigned"] and not r["proven_optimal"]
    assert len({p for route in r["routes"] for p in route["stop_ids"]})==3
    assert all(x["peak_load"]<=4 for x in r["routes"])
    assert r["summary"]["distance_m"]==sum(x["distance_m"] for x in r["routes"])

@pytest.mark.parametrize("objective",["distance","time","cost","vehicles","balance"])
def test_supported_objectives(objective):
    s=scenario(2,1,10,objective=objective);r=solve(s,numeric(s))
    assert r["validated"] and r["objective"]==objective and not r["unassigned"]

def test_capacity_shortfall_reports_unassigned():
    s=scenario(3,1,2);r=solve(s,numeric(s))
    assert len(r["unassigned"])==2 and r["summary"]["assigned_demand"]==2 and r["summary"]["unassigned_demand"]==4

def test_mandatory_shortfall_no_fake_feasible():
    s=scenario(2,1,1,allow_unassigned=False);r=solve(s,numeric(s))
    assert r["status"] in ("infeasible","timeout","no_solution_found") and not r["routes"] and not r["validated"]

def test_hard_time_windows_service_and_vehicle_duration():
    s=scenario(2,1,10)
    s.stops[0].window=(100,120);s.stops[0].service_s=15;s.stops[1].window=(200,250)
    r=solve(s,numeric(s));assert not r["unassigned"]
    rows={x["id"]:x for x in r["routes"][0]["schedule"]}
    assert 100<=rows["s0"]["arrival_s"]<=120 and rows["s0"]["departure_s"]==rows["s0"]["arrival_s"]+15
    assert 200<=rows["s1"]["arrival_s"]<=250

def test_pickup_delivery_same_vehicle_precedence_and_load():
    s=scenario(2,2,2);s.stops[0].kind="pickup";s.stops[1].pickup_id="s0"
    s=Scenario.model_validate(s.model_dump());r=solve(s,numeric(s))
    assert not r["unassigned"] and len(r["routes"])==1
    route=r["routes"][0];assert route["stop_ids"]==["s0","s1"]
    assert route["schedule"][0]["load_before"]==0 and route["peak_load"]==2

def test_multi_depot_assigned_start_and_end():
    s=scenario(2,2,10);s.depots.append(s.depots[0].model_copy(update={"id":"d2","coordinates":(101.2,3)}))
    s.vehicles[1].start_depot="d2";s.vehicles[1].end_depot="d2"
    r=solve(s,numeric(s));assert r["validated"] and not r["unassigned"]
    for route in r["routes"]:
        v=next(v for v in s.vehicles if v.id==route["vehicle_id"])
        assert route["schedule"][0]["id"]==v.start_depot and route["schedule"][-1]["id"]==v.end_depot

def test_unreachable_asymmetric_arc_not_used():
    s=scenario(2,1,10);m=numeric(s);m["distances"][1][2]=m["durations"][1][2]=None
    r=solve(s,m);assert r["validated"] and r["routes"][0]["node_indices"]==[0,2,1,0]

def test_route_distance_duration_limits_can_drop():
    s=scenario(2,1,10);s.vehicles[0].max_distance_m=1
    r=solve(s,numeric(s));assert len(r["unassigned"])==2 and not r["routes"]

def test_cost_components_explicit_no_invented_prices():
    v=scenario().vehicles[0];v.cost_per_km=2;v.fixed_cost=10;v.driver_cost_per_hour=12;v.fuel_l_per_100km=20;v.fuel_price_per_l=3
    c=cost_components(v,10000,3600);assert c=={"distance_cost":20,"fixed_cost":10,"driver_cost":12,"fuel_cost":6}

def test_postvalidator_rejects_tampered_schedule():
    s=scenario(2,1,10);m=numeric(s);r=solve(s,m)
    r["routes"][0]["schedule"][1]["load_before"]=999
    with pytest.raises(OptimizationError):validate(s,r["routes"],[],m["distances"],m["durations"])

@pytest.mark.parametrize("patch",[{"solver_seconds":99},{"stops":[]},{"capacity_unit":""},{"depots":[dict(id="d",name="bad",coordinates=[181,3])]},{"vehicles":[]}])
def test_bounded_scenario_rejects_invalid(patch):
    with pytest.raises(ValidationError):Scenario.model_validate({**scenario().model_dump(),**patch})

def test_schema_rejects_bad_pair_and_unknown_operation():
    s=scenario().model_dump();s["stops"][0]["pickup_id"]="missing"
    with pytest.raises(ValidationError):Scenario.model_validate(s)
    s=scenario().model_dump();s["python"]="import os"
    with pytest.raises(ValidationError):Scenario.model_validate(s)

def test_valid_csv_and_geojson_import():
    r=import_locations(ImportLocations(format="csv",content="id,name,longitude,latitude,demand\na,OSM candidate,101.5,3.1,4"))
    assert r["count"]==1 and r["stops"][0]["demand"]==4
    geo={"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[101,3]},"properties":{"demand":2,"source_id":"way/123"}}]}
    r=import_locations(ImportLocations(format="geojson",content=json.dumps(geo)));assert r["stops"][0]["source_id"]=="way/123"

@pytest.mark.parametrize("content",["longitude,latitude,demand\n181,3,1","longitude,latitude,demand\n101,3,-1","path,demand\nC:/secret,1","longitude,latitude,demand\n101,3,1.5"])
def test_import_rejects_invalid_or_path(content):
    with pytest.raises(OptimizationError):import_locations(ImportLocations(format="csv",content=content))

def test_matrix_validates_and_caches_asymmetry(tmp_path,monkeypatch):
    monkeypatch.setattr(mx,"get_settings",lambda:SimpleNamespace(provider_cache_dir=tmp_path,routing_base_url="https://example.test",routing_osrm_profile="car"))
    points=[{"coordinates":[101,3]},{"coordinates":[101.1,3]}];calls=[]
    class Provider:
        def table(self,ps,src,dst,snap):
            calls.append(1);return {"code":"Ok","sources":[{"location":p["coordinates"],"distance":0} for p in ps],"destinations":[{"location":p["coordinates"],"distance":0} for p in ps],"distances":[[0,100],[150,0]],"durations":[[0,10],[15,0]]}
    r=mx.road_matrix(points,provider=Provider());assert r["distances"][1][0]==150
    assert mx.road_matrix(points,provider=Provider())["cached"] and len(calls)==1

def test_matrix_rejects_fallback_and_bad_dimensions(tmp_path,monkeypatch):
    monkeypatch.setattr(mx,"get_settings",lambda:SimpleNamespace(provider_cache_dir=tmp_path,routing_base_url="https://example.test",routing_osrm_profile="car"))
    class Provider:
        def table(self,*args):return {"code":"Ok","fallback_speed_cells":[[0,1]]}
    with pytest.raises(RoutingError):mx.road_matrix([{"coordinates":[101,3]},{"coordinates":[101.1,3]}],provider=Provider())

def test_optimization_api_guard_no_fixture_fallback(client):
    r=client.post("/api/optimization/scenarios",json=scenario().model_dump(mode="json"))
    assert r.status_code==409
    assert client.post("/api/optimization/scenarios",json={"python":"x"}).status_code==422


def test_unselected_depot_is_not_an_intermediate_delivery():
    s=scenario(2,1,10)
    s.depots.append(s.depots[0].model_copy(update={"id":"unused","name":"Unused depot","coordinates":(101.2,3)}))
    r=solve(s,numeric(s))
    assert r["validated"] and not r["unassigned"]
    assert all(row["id"]!="unused" for route in r["routes"] for row in route["schedule"])
