import pytest
from pyproj import Geod
from app.gis.measure import distance_from_center_km


def test_geodesic_length_units(client):
    # One longitude degree at equator is approximately 111.31949 km.
    response = client.post("/api/spatial/measure", json={"geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]}})
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["length_km"] == pytest.approx(111.31949, abs=0.01)
    assert result["area_sq_km"] == 0


def test_polygon_hole_is_subtracted_regardless_of_winding(client):
    outer = [[101, 3], [101.1, 3], [101.1, 3.1], [101, 3.1], [101, 3]]
    hole = [[101.02, 3.02], [101.08, 3.02], [101.08, 3.08], [101.02, 3.08], [101.02, 3.02]]
    result = client.post("/api/spatial/measure", json={"geometry": {"type": "Polygon", "coordinates": [outer, hole]}}).json()["data"]
    geod = Geod(ellps="WGS84")
    expected = abs(geod.polygon_area_perimeter(*zip(*outer))[0]) - abs(geod.polygon_area_perimeter(*zip(*hole))[0])
    assert result["area_sq_km"] == pytest.approx(expected / 1e6, abs=0.01)


@pytest.mark.parametrize("geometry", [
    {"type": "Point", "coordinates": [181, 2]},
    {"type": "Point", "coordinates": [101, 91]},
    {"type": "Point", "coordinates": [True, 3]},
    {"type": "Point", "coordinates": [101, 3, 15]},
    {"type": "LineString", "coordinates": [[101, 3]]},
    {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]},
    {"type": "GeometryCollection", "coordinates": []},
    {"type": "Point", "coordinates": []},
    {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
])
def test_invalid_geometries_rejected(client, geometry):
    assert client.post("/api/spatial/measure", json={"geometry": geometry}).status_code == 422


def test_projected_crs_cannot_be_misrepresented_as_wgs84(client):
    assert client.post("/api/spatial/measure", json={"geometry": {"type": "Point", "coordinates": [101, 3]}, "crs": "EPSG:3857"}).status_code == 422
    assert client.post("/api/spatial/measure", json={"geometry": {"type": "Point", "coordinates": [101, 3]}, "python": "print(1)"}).status_code == 422


def test_radial_distance_in_meters_not_degrees():
    assert distance_from_center_km({"type": "Point", "coordinates": [1, 0]}, (0, 0)) == pytest.approx(111.31949, abs=0.01)
