"""Synthetic numerical/geometry unit tests only, never production facility records."""
import copy,math
import pytest
from pydantic import ValidationError
from app.schemas.sites import SiteScenario,AHPRequest,SiteImport,SiteCandidate
from app.sites.mcda import normalize,ahp,evaluate_mcda,SiteError
from app.sites.imports import import_candidates
from app.api import sites as api
def scenario():
 return SiteScenario(name="TEST synthetic MCDA",candidates=[{"id":k,"name":"TEST "+k,"geometry":{"type":"Point","coordinates":[101+i*.01,3]}} for i,k in enumerate("abc")],
  criteria=[{"id":"road_distance_m","source":"gis","direction":"cost","weight":1},{"id":"industrial_count","source":"gis","direction":"benefit","weight":3}])
def values():
 return {k:{"road_distance_m":{"value":x},"industrial_count":{"value":y}} for k,x,y in (("a",10,100),("b",20,50),("c",15,75))}
def test_wlc_directions_weights_contributions_known_answer():
 r=evaluate_mcda(scenario(),values());assert r["weights"]=={"road_distance_m":.25,"industrial_count":.75}
 assert [(x["candidate_id"],x["score"]) for x in r["rankings"]]==[("a",100),("c",50),("b",0)]
 assert all(sum(x["contributions"].values())==pytest.approx(x["score"]) for x in r["rankings"])
def test_constant_criterion_neutral_and_ties_stable():
 s=scenario();v=values()
 for row in v.values():
  for cell in row.values():cell["value"]=10
 r=evaluate_mcda(s,v);assert all(x["score"]==50 and x["rank"]==1 for x in r["rankings"])
 assert [x["candidate_id"] for x in r["rankings"]]==list("abc")
@pytest.mark.parametrize("weights",[{},{"a":0},{"a":-1},{"a":float("nan")},{"a":float("inf")}])
def test_bad_weights(weights):
 with pytest.raises(SiteError):normalize(weights)
def test_ahp_known_consistent_eigenvector():
 w=[.5,.3,.2];a=[[x/y for y in w] for x in w];r=ahp(a)
 assert r["weights"]==pytest.approx(w) and r["cr"]<1e-10 and r["consistent"]
@pytest.mark.parametrize("matrix",[[[1]],[[1,3],[1/3,1]]])
def test_ahp_order_one_two_cr_zero(matrix):assert ahp(matrix)["cr"]==0
@pytest.mark.parametrize("matrix",[[],[[1,2]],[[2]],[[1,2],[2,1]],[[1,10],[.1,1]],[[1,float("nan")],[1,1]]])
def test_invalid_pairwise(matrix):
 with pytest.raises(SiteError):ahp(matrix)
def test_inconsistent_ahp_requires_explicit_override():
 s=scenario();s.criteria.append(s.criteria[0].model_copy(update={"id":"warehouse_distance_m"}));s.method="ahp";s.ahp_matrix=[[1,9,1/9],[1/9,1,9],[9,1/9,1]]
 v=values()
 for row in v.values():row["warehouse_distance_m"]={"value":100}
 assert ahp(s.ahp_matrix)["cr"]>.1
 with pytest.raises(SiteError,match="consistency"):evaluate_mcda(s,v)
 s.allow_inconsistent=True;assert evaluate_mcda(s,v)["warnings"]
def test_missing_policies_never_impute_or_rank_incomparable_rows():
 s=scenario();v=values();v["a"]["road_distance_m"]["value"]=None
 with pytest.raises(SiteError):evaluate_mcda(s,v)
 s.missing_policy="exclude_criterion";r=evaluate_mcda(s,v);assert r["excluded_criteria"]==["road_distance_m"] and r["weights"]=={"industrial_count":1}
 s.missing_policy="exclude_candidate";r=evaluate_mcda(s,v);assert r["excluded_candidates"]==["a"] and len(r["rankings"])==2
def test_sensitivity_is_reproducible_and_renormalized():
 s=scenario();s.criteria[0].weight=s.criteria[1].weight=1;v=values();v["a"]["industrial_count"]["value"]=50;v["b"]["industrial_count"]["value"]=100
 r=evaluate_mcda(s,v);assert r==evaluate_mcda(s,v)
 assert len(r["sensitivity"]["runs"])==4 and any(any(run["rank_changes"].values()) for run in r["sensitivity"]["runs"])
 assert all(sum(run["weights"].values())==pytest.approx(1) for run in r["sensitivity"]["runs"])
@pytest.mark.parametrize("patch",[{"criteria":[{"id":"flood_risk","direction":"cost","source":"gis"}]},{"candidates":[]},{"criteria":[{"id":"port_time_s","source":"network","direction":"cost"}]},{"candidates":[{"id":"x","name":"TEST","geometry":{"type":"Point","coordinates":[0,0]}}]}])
def test_invalid_scenarios_and_unavailable_official_sources(patch):
 with pytest.raises(ValidationError):SiteScenario.model_validate({**scenario().model_dump(),**patch})
@pytest.mark.parametrize("content",["[]","null",'{"type":"FeatureCollection","features":[null]}','{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[181,3]}}]}'])
def test_bad_imports(content):
 with pytest.raises(SiteError):import_candidates(SiteImport(format="geojson",content=content))
def test_point_and_polygon_imports_and_legacy_crs_rejection():
 r=import_candidates(SiteImport(format="csv",content="id,name,longitude,latitude\na,TEST candidate,101,3"));assert r["candidates"][0]["kind"]=="hypothetical_site"
 r=import_candidates(SiteImport(format="geojson",content='{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[101,3],[101.01,3],[101,3.01],[101,3]]]},"properties":{"name":"TEST hypothetical polygon"}}]}'))
 assert r["candidates"][0]["geometry"]["type"]=="Polygon"
def test_api_bounds_guards_and_no_arbitrary_operations(client,monkeypatch):
 assert client.post("/api/sites/evaluate",json=scenario().model_dump(mode="json")).status_code==409
 monkeypatch.setattr(api,"guard",lambda request:None)
 assert client.post("/api/sites/ahp",json={"matrix":[[1,3],[1/3,1]]}).json()["cr"]==0
 assert client.post("/api/sites/import",json={"format":"geojson","content":"[]"}).status_code==422
 assert client.get("/api/sites/saved?limit=1000").status_code==422
 assert client.post("/api/sites/evaluate",json={**scenario().model_dump(mode="json"),"sql":"DROP"}).status_code==422
 assert client.post("/api/sites/import",content=b"x"*1_500_001).status_code==413
def test_additive_phase6_preflight_and_collision_rejection():
 from app.db.migrate import classify_schema
 from app.db.verification import PHASE5_TABLES,DatabaseVerificationError
 assert classify_schema(PHASE5_TABLES|{"alembic_version"},["0002_logistics"])=="upgrade"
 with pytest.raises(DatabaseVerificationError):classify_schema(PHASE5_TABLES|{"site_scenarios","alembic_version"},["0002_logistics"])
