"""Bounded, typed discovery requests; no caller-supplied Overpass expressions."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pyproj import Geod
from app.schemas.spatial import Category, SearchParams

DISCOVERY_CATEGORIES = [c for c in Category if c != Category.study_area]
STUDY_TARGETS = [
    {"id":"tanjong-malim","name":"AHTV / Tanjong Malim","query":"Tanjong Malim, Perak, Malaysia","note":"Town search reference only; not an AHTV boundary."},
    {"id":"rawang","name":"Rawang","query":"Rawang, Selangor, Malaysia","note":"OSM place search reference."},
    {"id":"shah-alam","name":"Shah Alam","query":"Shah Alam, Selangor, Malaysia","note":"OSM place search reference."},
    {"id":"bukit-raja","name":"Bukit Raja","query":"Bandar Bukit Raja, Malaysia","note":"OSM place search reference; verify the selected match."},
    {"id":"klang","name":"Klang","query":"Klang, Selangor, Malaysia","note":"OSM place search reference."},
    {"id":"port-klang","name":"Port Klang","query":"Port Klang, Selangor, Malaysia","note":"Town/port search reference; not a verified port boundary."},
]

class DiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categories: list[Category] = Field(min_length=1, max_length=8)
    bbox: tuple[float,float,float,float] | None = None
    center: tuple[float,float] | None = None
    radius_km: float | None = Field(default=None, gt=0, le=10)
    label: str = Field(default="User study area", min_length=1, max_length=200)

    @model_validator(mode="after")
    def bounded_scope(self):
        SearchParams(bbox=self.bbox, center=self.center, radius_km=self.radius_km)
        if (self.bbox is None) == (self.center is None):
            raise ValueError("Choose exactly one bounded box or center with radius.")
        if Category.study_area in self.categories:
            raise ValueError("Study areas are user-defined, not an OSM discovery category.")
        self.categories = list(dict.fromkeys(self.categories))
        if self.bbox:
            west,south,east,north = self.bbox
            area,_ = Geod(ellps="WGS84").polygon_area_perimeter(
                [west,east,east,west,west],[south,south,north,north,south])
            if abs(area) > 400_000_000 or east-west > 1 or north-south > 1:
                raise ValueError("Discovery box must be at most 400 km² and 1 degree per side.")
        return self
