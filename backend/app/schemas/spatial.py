import math
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from shapely.geometry import shape
from shapely.validation import explain_validity


class Category(StrEnum):
    industrial = "industrial"
    industrial_park = "industrial_park"
    warehouse = "warehouse"
    logistics_hub = "logistics_hub"
    port = "port"
    airport = "airport"
    road = "road"
    rail = "rail"
    study_area = "study_area"


class Geometry(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    type: Literal["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]
    coordinates: list[Any]

    @model_validator(mode="after")
    def validate_geometry(self):
        count = 0

        def visit(value, depth=0):
            nonlocal count
            if depth > 5:
                raise ValueError("Coordinate nesting exceeds geometry limits")
            if not isinstance(value, list) or not value:
                raise ValueError("Coordinates must be nonempty arrays")
            if isinstance(value[0], (int, float)):
                if len(value) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
                    raise ValueError("Use finite, two-dimensional [longitude, latitude] coordinates")
                if not -180 <= value[0] <= 180 or not -90 <= value[1] <= 90:
                    raise ValueError("Coordinates must use EPSG:4326 longitude/latitude")
                count += 1
                if count > 10000:
                    raise ValueError("Geometry exceeds 10000 vertices")
            else:
                for part in value:
                    visit(part, depth + 1)

        visit(self.coordinates)
        rings = self.coordinates if self.type == "Polygon" else [ring for polygon in self.coordinates for ring in polygon] if self.type == "MultiPolygon" else []
        for ring in rings:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("Polygon rings need at least four positions and must be explicitly closed")
        try:
            geom = shape(self.model_dump())
        except Exception as exc:
            raise ValueError("Malformed GeoJSON geometry") from exc
        if geom.is_empty or not geom.is_valid:
            raise ValueError("Invalid geometry: " + explain_validity(geom))
        return self


class FeatureProperties(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=240)
    categories: list[Category] = Field(min_length=1)
    source: str
    license: str | None = None
    source_id: str
    dataset_id: str
    imported_at: str
    synthetic: bool
    boundary_status: Literal["not_applicable", "unverified", "verified", "synthetic"] = "not_applicable"
    attributes: dict[str, Any] = Field(default_factory=dict)


class Feature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["Feature"] = "Feature"
    id: str
    geometry: Geometry
    properties: FeatureProperties


class SearchParams(BaseModel):
    categories: list[Category] = Field(default_factory=list)
    q: str = Field(default="", max_length=200)
    bbox: tuple[float, float, float, float] | None = None
    center: tuple[float, float] | None = None
    radius_km: float | None = Field(default=None, gt=0, le=200)
    limit: int = Field(default=250, ge=1, le=1000)
    offset: int = Field(default=0, ge=0, le=100000)

    @field_validator("bbox")
    @classmethod
    def valid_bbox(cls, value):
        if value is not None:
            west, south, east, north = value
            if not all(math.isfinite(x) for x in value) or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise ValueError("bbox must be west,south,east,north; antimeridian crossing is not supported")
        return value

    @field_validator("center")
    @classmethod
    def valid_center(cls, value):
        if value is not None and not (all(math.isfinite(x) for x in value) and -180 <= value[0] <= 180 and -90 <= value[1] <= 90):
            raise ValueError("center must be longitude,latitude")
        return value

    @model_validator(mode="after")
    def paired_radius(self):
        if (self.center is None) != (self.radius_km is None):
            raise ValueError("Provide both center and radius_km")
        return self


class SearchMetadata(BaseModel):
    mode: Literal["fixture", "postgis"]
    crs: Literal["EPSG:4326"] = "EPSG:4326"
    total: int
    returned: int
    offset: int
    limit: int
    has_more: bool
    category_counts: dict[str, int]
    missing_categories: list[str]
    failed_categories: list[str] = Field(default_factory=list)
    warnings: list[str]
    attribution: str


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]
    meta: SearchMetadata


class MeasurementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geometry: Geometry
    crs: Literal["EPSG:4326"] = "EPSG:4326"
