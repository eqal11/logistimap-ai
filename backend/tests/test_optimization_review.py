"""Acceptance-review regressions; all numeric matrices here are synthetic unit-test data."""
import pytest
from app.schemas.optimization import Scenario,ImportLocations
from app.optimization.solver import solve,validate,OptimizationError
from app.optimization.imports import import_locations

def paired():
    return Scenario(name="Review synthetic pickup pair",solver_seconds=1,
        depots=[{"id":"d","name":"test depot","coordinates":[101,3]}],
        vehicles=[{"id":"v","name":"test vehicle","capacity":1,"start_depot":"d","end_depot":"d"}],
        stops=[{"id":"p","name":"test pickup","coordinates":[101.1,3],"demand":2,"kind":"pickup"},
               {"id":"s","name":"test delivery","coordinates":[101.2,3],"demand":2,"pickup_id":"p"}])
def numeric(n):
    return {"distances":[[0 if i==j else 100 for j in range(n)] for i in range(n)],
            "durations":[[0 if i==j else 10 for j in range(n)] for i in range(n)]}

def test_optional_infeasible_pickup_pair_can_be_dropped_together():
    s=paired();result=solve(s,numeric(3))
    assert result["validated"], "Dropping both optional stops is a feasible solution"
    assert not result["routes"] and {p["id"] for p in result["unassigned"]}=={"p","s"}

@pytest.mark.parametrize("content",['[]','null','{"type":"FeatureCollection","features":[null]}','{"type":"FeatureCollection","features":[{"type":"Feature","geometry":null,"properties":{"demand":1}}]}'])
def test_malformed_geojson_has_controlled_error(content):
    with pytest.raises(OptimizationError):
        import_locations(ImportLocations(format="geojson",content=content))

def test_validator_rejects_wrong_service_departure():
    s=paired();s.vehicles[0].capacity=4
    s.stops[0].service_s=20
    matrix=numeric(3);r=solve(s,matrix)
    assert r["validated"] and r["routes"]
    r["routes"][0]["schedule"][1]["departure_s"]-=20
    with pytest.raises(OptimizationError):
        validate(s,r["routes"],[],matrix["distances"],matrix["durations"])


def test_service_priority_penalty_includes_depot_cost_arcs():
    s=Scenario(name="Synthetic high-cost depot arc regression",objective="cost",solver_seconds=1,
        depots=[{"id":"d","name":"Test depot","coordinates":[101,3]}],
        vehicles=[{"id":"v","name":"Test vehicle","capacity":2,"start_depot":"d","end_depot":"d","cost_per_km":10000,"max_distance_m":3000000}],
        stops=[{"id":"s","name":"Test stop","coordinates":[102,3],"demand":1}])
    r=solve(s,{"distances":[[0,1000000],[1000000,0]],"durations":[[0,100],[100,0]]})
    assert r["validated"] and not r["unassigned"], "Service priority must dominate even costly depot legs"
