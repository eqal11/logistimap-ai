from pyproj import CRS, Geod, Transformer
from shapely import orient_polygons, transform
from shapely.geometry import Point, shape

GEOD = Geod(ellps="WGS84")


def measure(geometry: dict) -> dict:
    geom = shape(geometry)
    area = 0.0
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        oriented = orient_polygons(geom)
        area = abs(GEOD.geometry_area_perimeter(oriented)[0]) / 1_000_000
    return {
        "length_km": GEOD.geometry_length(geom) / 1000,
        "area_sq_km": area,
        "method": "WGS84 ellipsoidal geodesic (PyProj/PROJ); polygon length is perimeter",
        "crs": "EPSG:4326",
    }


def distance_from_center_km(geometry: dict, center: tuple[float, float]) -> float:
    # Local azimuthal equidistant coordinates preserve radial distance from center.
    local = CRS.from_proj4(f"+proj=aeqd +lat_0={center[1]} +lon_0={center[0]} +datum=WGS84 +units=m")
    project = Transformer.from_crs("EPSG:4326", local, always_xy=True).transform
    return transform(shape(geometry), project, interleaved=False).distance(Point(0, 0)) / 1000
