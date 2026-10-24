"""Synthetic provider contracts are tests only; live discovery never uses these fixtures."""
import json
import pytest
import httpx
from pydantic import ValidationError
from shapely.geometry import shape
from app.schemas.discovery import DiscoveryRequest
from app.schemas.spatial import Category
from app.services import osm

def request(**kw):
    return DiscoveryRequest(categories=[Category.warehouse,Category.industrial,Category.port],
                            center=(101.5,3.1),radius_km=2,**kw)

def way(id,tags,pts):
    return {"type":"way","id":id,"tags":tags,"geometry":[{"lon":x,"lat":y} for x,y in pts]}

def test_union_queries_every_requested_category_and_uses_lat_lon():
    query=osm.build_query(request())
    assert '["building"="warehouse"]' in query and '["man_made"="works"]' in query and '["harbour"="yes"]' in query
    assert "(around:2000.0,3.1,101.5)" in query
    assert "[timeout:60]" in query and "out meta geom" in query

@pytest.mark.parametrize("values",[
    {"categories":["warehouse"]}, {"categories":["study_area"],"center":[101,3],"radius_km":1},
    {"categories":["warehouse"],"center":[101,3],"radius_km":11},
    {"categories":["warehouse"],"bbox":[100,2,102,4]},
    {"categories":["warehouse"],"bbox":[102,2,100,4]},
    {"categories":["warehouse"],"center":[101,3],"radius_km":1,"bbox":[101,3,101.01,3.01]},
    {"categories":["warehouse"],"center":[float("nan"),3],"radius_km":1},
    {"categories":["warehouse"],"center":[101,3],"radius_km":1,"query":"arbitrary QL"},
])
def test_unbounded_or_untrusted_requests_rejected(values):
    with pytest.raises(ValidationError): DiscoveryRequest.model_validate(values)

def test_multicategory_normalization_preserves_geometry_and_source_ids():
    polygon=[(101,3),(101.001,3),(101.001,3.001),(101,3.001),(101,3)]
    warehouse=way(1,{"building":"warehouse","industrial":"logistics","name":"TEST Warehouse"},polygon)
    road=way(2,{"highway":"primary"},polygon)
    raw={"elements":[warehouse,warehouse,road,{"type":"node","id":3,"lon":101,"lat":3,"tags":{"harbour":"yes"}}]}
    payload=DiscoveryRequest(categories=list(osm.SELECTORS),center=[101,3],radius_km=1)
    features,report=osm.normalize(raw,payload)
    assert len(features)==3 and report["duplicates_in_response"]==1
    assert {f["geometry"]["type"] for f in features}=={"Polygon","LineString","Point"}
    assert features[0]["categories"]==["industrial","warehouse","logistics_hub"]
    assert features[0]["boundary_status"]=="unverified"
    assert features[0]["attributes"]["capacity"] is None
    assert report["category_counts"]["warehouse"]==1
    assert "airport" in report["missing_categories"] and report["failed_categories"]==[]

def test_relation_polygon_hole_and_split_outer_members():
    ring=[(101,3),(101.01,3),(101.01,3.01),(101,3.01),(101,3)]
    hole=[(101.002,3.002),(101.003,3.002),(101.003,3.003),(101.002,3.003),(101.002,3.002)]
    relation={"type":"relation","id":4,"tags":{"type":"multipolygon","landuse":"industrial"},"members":[
        {"type":"way","role":"outer","geometry":way(1,{},ring[:3])["geometry"]},
        {"type":"way","role":"outer","geometry":way(2,{},ring[2:])["geometry"]},
        {"type":"way","role":"inner","geometry":way(3,{},hole)["geometry"]}]}
    features,report=osm.normalize({"elements":[relation]},DiscoveryRequest(categories=["industrial_park"],center=[101,3],radius_km=1))
    assert report["valid_features"]==1
    assert len(features[0]["geometry"]["coordinates"])==2
    assert shape(features[0]["geometry"]).is_valid

def test_bad_or_missing_geometry_is_reported_and_never_repaired_or_invented():
    bowtie=way(1,{"building":"warehouse"},[(101,3),(101.01,3.01),(101,3.01),(101.01,3),(101,3)])
    incomplete={"type":"way","id":2,"tags":{"building":"warehouse"}}
    features,report=osm.normalize({"elements":[bowtie,incomplete]},request())
    assert features==[] and report["skipped"]=={"invalid_or_incomplete_geometry":2}
    assert len(report["failed_record_examples"])==2

def test_incomplete_relation_rejected():
    relation={"type":"relation","id":4,"tags":{"type":"multipolygon","landuse":"industrial"},
              "members":[{"type":"way","role":"outer","geometry":[{"lon":101,"lat":3},{"lon":101.1,"lat":3.1}]}]}
    features,report=osm.normalize({"elements":[relation]},DiscoveryRequest(categories=["industrial_park"],center=[101,3],radius_km=1))
    assert not features and report["skipped"]

def test_provider_partial_response_fails_without_cache(tmp_path,monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(),"provider_cache_dir",tmp_path)
    original=httpx.Client
    def client(**kwargs):
        return original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"remark":"timeout","elements":[]})))
    monkeypatch.setattr(osm.httpx,"Client",client)
    monkeypatch.setitem(osm.last_request,"overpass",0)
    with pytest.raises(osm.ProviderError,match="incomplete"):
        osm.public_json("overpass","https://provider.example/api","partial",data={"data":"bounded"})
    assert not list(tmp_path.glob("*.json"))

def test_provider_cache_avoids_repeated_public_requests(tmp_path,monkeypatch):
    from app.core.config import get_settings
    original=httpx.Client;calls=[]
    monkeypatch.setattr(get_settings(),"provider_cache_dir",tmp_path)
    def respond(r): calls.append(r);return httpx.Response(200,json=[])
    monkeypatch.setattr(osm.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(respond)))
    monkeypatch.setitem(osm.last_request,"geocode",0)
    first,cached=osm.public_json("geocode","https://provider.example/search","Klang")
    second,cached2=osm.public_json("geocode","https://provider.example/search","Klang")
    assert first==second==[] and not cached and cached2 and len(calls)==1

def test_discovery_requires_postgis_and_restricts_external_requests(client):
    assert client.post("/api/discovery/jobs",json=request().model_dump(mode="json")).status_code==409
    assert client.get("/api/locations/search?q=Klang",headers={"Origin":"https://evil.example"}).status_code==403
    assert client.get("/api/locations/search?q=Klang",headers={"Host":"evil.example"}).status_code==403
    assert len(client.get("/api/discovery/study-areas").json()["areas"])==6

def test_geocoding_failure_is_actionable_and_returns_no_fixture(client,monkeypatch):
    from app.api import discovery
    def fail(q): raise osm.ProviderError("geocode provider returned HTTP 429; wait before retrying.")
    monkeypatch.setattr(discovery,"geocode",fail)
    result=client.get("/api/locations/search?q=Klang")
    assert result.status_code==502 and "429" in result.json()["error"]["message"]


def test_overpass_rate_limit_sets_cooldown_without_retry(tmp_path,monkeypatch):
    from app.core.config import get_settings
    original=httpx.Client
    calls=[]
    def response(r):
        calls.append(r)
        return httpx.Response(429,headers={"Retry-After":"120"})
    monkeypatch.setattr(get_settings(),"provider_cache_dir",tmp_path)
    monkeypatch.setattr(osm.httpx,"Client",lambda **kw:original(transport=httpx.MockTransport(response)))
    monkeypatch.setitem(osm.last_request,"overpass",0)
    monkeypatch.setitem(osm.blocked_until,"overpass",0)
    with pytest.raises(osm.ProviderError,match="HTTP 429"):
        osm.public_json("overpass","https://provider.example/api","limited",data={"data":"bounded"})
    with pytest.raises(osm.ProviderError,match="cooldown"):
        osm.public_json("overpass","https://provider.example/api","limited",data={"data":"bounded"})
    assert len(calls)==1 and not list(tmp_path.glob("*.json"))


def test_excessive_results_are_rejected_before_any_import():
    with pytest.raises(osm.ProviderError,match="12,000"):
        osm.normalize({"elements":[{}]*12001},request())
