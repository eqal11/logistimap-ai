"""Synthetic geometries below are test-only, never imported as facilities."""
import math,json
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from shapely.geometry import Point,LineString,Polygon,box,mapping,shape
from app.schemas.analytics import SpatialAnalysis,LayerInput,MatrixRequest,ArchiveRequest
from app.gis.analytics import execute,dbscan,GEOD,AnalysisError

def f(g,id="test",cats=None):
    return {"type":"Feature","id":id,"geometry":mapping(g),"properties":{"name":id,"source":"TEST ONLY","categories":cats or ["industrial"]}}
def params(op,**kwargs):
    return SpatialAnalysis(operation=op,a={"features":[{"id":"test","geometry":mapping(Point(101.5,3.1))}]},
        b={"features":[{"id":"boundary","geometry":json.loads(json.dumps(mapping(box(101.49,3.09,101.51,3.11))))}]} if op in ("intersection","clip","difference","spatial_join","nearest","aggregate") else None,**kwargs)
@pytest.mark.parametrize("g",[Point(101.5,3.1),LineString([(101.5,3.1),(101.51,3.1)]),box(101.5,3.1,101.51,3.11)])
def test_buffers_are_valid_metric(g):
    out,rows,stats,warnings,crs=execute(params("buffer",distance_m=1000),[f(g)],[])
    assert shape(out[0]["geometry"]).is_valid
    assert "+proj=aeqd" in crs
    if g.geom_type=="Point":
        ring=shape(out[0]["geometry"]).exterior.coords
        assert all(abs(GEOD.inv(g.x,g.y,x,y)[2]-1000)<.1 for x,y in ring)
        assert abs(stats["summed_output_area_km2"]-math.pi)<.01
@pytest.mark.parametrize("g",[Point(101.5,3.1),LineString([(101.48,3.1),(101.52,3.1)]),box(101.48,3.08,101.52,3.12)])
def test_intersection_geometry_types(g):
    out,*_=execute(params("intersection"),[f(g)],[f(box(101.49,3.09,101.51,3.11),"b")])
    assert out and all(shape(x["geometry"]).is_valid for x in out)
    assert out[0]["properties"]["join_id"]=="b"
@pytest.mark.parametrize("op",["intersection","clip","difference"])
def test_empty_mask(op):
    out,*_=execute(params(op),[f(Point(101.5,3.1))],[])
    assert len(out)==(1 if op=="difference" else 0)
def test_clip_difference_union_dissolve():
    a=[f(box(101.49,3.09,101.51,3.11))]
    b=[f(box(101.5,3.09,101.52,3.11),"b")]
    intersection=execute(params("clip"),a,b)[0]
    difference=execute(params("difference"),a,b)[0]
    assert shape(intersection[0]["geometry"]).area>0
    assert shape(difference[0]["geometry"]).area>0
    for op in ("union","dissolve"):
        result=execute(params(op),a,b)[0];assert result and shape(result[0]["geometry"]).is_valid
def test_invalid_crs_geometry_and_source_rejected():
    with pytest.raises(ValidationError):SpatialAnalysis(operation="buffer",a={"ids":["bad"]})
    with pytest.raises(ValidationError):SpatialAnalysis(operation="buffer",a={"query":{}},crs="EPSG:3857")
    with pytest.raises(ValidationError):LayerInput(features=[{"id":"x","geometry":mapping(Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]))}])
    with pytest.raises(ValidationError):LayerInput(ids=["00000000-0000-0000-0000-000000000001"],features=[{"id":"x","geometry":mapping(Point(101,3))}])
    with pytest.raises(AnalysisError):execute(params("buffer"),[f(Point(105,3)),f(Point(115,3))],[])
def test_join_within_aggregate_and_nearest_preserve_sources():
    a=[f(Point(101.5,3.1),"a"),f(Point(101.53,3.1),"c")]
    b=[f(box(101.49,3.09,101.51,3.11),"b")]
    out,rows,stats,*_=execute(params("spatial_join",predicate="within"),a,b)
    assert len(rows)==1 and rows[0]["input_id"]=="a" and rows[0]["join_source"]=="TEST ONLY"
    out,rows,stats,*_=execute(params("aggregate"),a,b)
    assert out[0]["properties"]["matched_count"]==1
    out,rows,*_=execute(params("nearest"),a,b)
    assert len(rows)==2 and rows[0]["distance_m"]==0 and rows[1]["distance_m"]>2000
def test_dbscan_noise_border_and_grid_counts():
    assert dbscan([Point(0,0),Point(10,0),Point(20,0),Point(2000,0)],15,2)==[0,0,0,-1]
    a=[f(Point(101.5+i*.0001,3.1),str(i)) for i in range(4)]
    out,rows,stats,*_=execute(params("clusters",eps_m=100,min_points=3),a,[])
    assert stats["clusters"]==1 and stats["noise"]==0 and stats["clustered"]==4
    out,rows,stats,*_=execute(params("grid",grid_m=1000),a,[])
    assert sum(r["count"] for r in rows)==4
    assert all(r["density_per_km2"]>0 for r in rows)
    assert sum(f["properties"].get("role")=="density_point" for f in out)==4
def test_buffer_counts_each_candidate_once_for_overlaps():
    a=[f(Point(101.5,3.1),"a"),f(Point(101.5001,3.1),"b")]
    b=[f(Point(101.5,3.1),"c",["industrial","warehouse"])]
    out,rows,stats,*_=execute(params("buffer",distance_m=500),a,b)
    assert stats["matched_count"]==1 and stats["matched_category_counts"]=={"industrial":1,"warehouse":1}
def test_empty_cluster_data():
    assert execute(params("clusters"),[],[])[2]["clusters"]==0
def test_limits_and_confirmation():
    with pytest.raises(ValidationError):ArchiveRequest(confirmed=False)
    with pytest.raises(ValidationError):MatrixRequest(origins=[],destinations=[])
    with pytest.raises(ValidationError):SpatialAnalysis(operation="exec",a={"features":[]})
def test_api_guard_and_isochrone_truth(client,monkeypatch):
    from app.api import analytics
    monkeypatch.setattr(analytics,"get_settings",lambda:SimpleNamespace(analytics_enabled=True,data_mode="postgis",cors_origins=[]))
    assert client.post("/api/network/isochrone").status_code==501
    assert client.get("/api/network/capabilities").json()["isochrone"] is False
    assert client.post("/api/spatial/analyze",json={"operation":"__import__('os')"}).status_code==422
    assert client.get("/api/history/routes",headers={"host":"evil.example"}).status_code==403
    assert client.post("/api/history/routes/00000000-0000-0000-0000-000000000001/archive",json={"confirmed":False}).status_code==422

def test_geodesic_area_subtracts_holes_regardless_of_ring_orientation():
    from app.gis.analytics import geodesic_area
    outer=[(101,3),(101.02,3),(101.02,3.02),(101,3.02),(101,3)]
    inner=[(101.005,3.005),(101.015,3.005),(101.015,3.015),(101.005,3.015),(101.005,3.005)]
    polygon=Polygon(outer,[inner]) # intentionally same ring orientation
    assert abs(geodesic_area(polygon)-(geodesic_area(Polygon(outer))-geodesic_area(Polygon(inner))))<1e-8
