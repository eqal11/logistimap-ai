"""Strict routing contracts. Distances and durations are provider-derived only."""
import math
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pyproj import Geod

GEOD=Geod(ellps="WGS84")
def coordinate(value):
    if (not isinstance(value,(list,tuple)) or len(value)!=2 or
        any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in value) or
        not -180<=value[0]<=180 or not -90<=value[1]<=90):
        raise ValueError("Use finite EPSG:4326 [longitude, latitude] coordinates.")
    return tuple(float(v) for v in value)

class RoutePoint(BaseModel):
    model_config=ConfigDict(extra="forbid")
    coordinates: tuple[float,float] | None=None
    feature_id: str | None=None
    label: str=Field(default="",max_length=160)

    @field_validator("coordinates",mode="before")
    @classmethod
    def valid_coordinate(cls,value): return coordinate(value) if value is not None else None

    @field_validator("feature_id")
    @classmethod
    def valid_feature_id(cls,value):
        if value is not None: UUID(value)
        return value

    @model_validator(mode="after")
    def one_source(self):
        if (self.coordinates is None)==(self.feature_id is None):
            raise ValueError("Choose coordinates or an existing GIS feature ID, exactly one.")
        return self

class RouteRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    points: list[RoutePoint]=Field(min_length=2,max_length=8)
    profile: Literal["car"]="car"
    alternatives: bool=True
    max_snap_m: int=Field(default=1000,ge=25,le=2000)

class SaveRouteRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    calculation_id: str=Field(pattern=r"^[a-f0-9]{64}$")
    route_index: int=Field(ge=0,le=2)
