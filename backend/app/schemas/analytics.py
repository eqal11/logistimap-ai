from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.schemas.spatial import Geometry,SearchParams,Category

class InlineFeature(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id:str=Field(max_length=100)
    geometry:Geometry
    name:str=Field(default="User geometry",max_length=160)

class LayerInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    ids:list[UUID]=Field(default_factory=list,max_length=200)
    query:SearchParams|None=None
    features:list[InlineFeature]=Field(default_factory=list,max_length=200)
    saved_id:UUID|None=None
    @model_validator(mode="after")
    def one(self):
        if sum((bool(self.ids),self.query is not None,bool(self.features),self.saved_id is not None))!=1:
            raise ValueError("Choose exactly one source: IDs, bounded query, user geometry or saved analysis")
        if self.query and not (self.query.bbox or self.query.center):
            raise ValueError("Analysis queries require a bbox or center/radius")
        if self.query and (self.query.offset or self.query.q):
            raise ValueError("Use bounded category queries; offset/name filtering is not accepted for analysis")
        return self

class SpatialAnalysis(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    operation:Literal["buffer","intersection","clip","union","dissolve","difference","spatial_join","nearest","aggregate","clusters","grid"]
    title:str=Field(default="Spatial analysis",min_length=1,max_length=160)
    a:LayerInput
    b:LayerInput|None=None
    crs:Literal["EPSG:4326"]="EPSG:4326"
    distance_m:float=Field(default=5000,gt=0,le=50000)
    predicate:Literal["intersects","within","contains","nearest"]="intersects"
    eps_m:float=Field(default=1000,ge=25,le=20000)
    min_points:int=Field(default=3,ge=2,le=100)
    grid_m:float=Field(default=1000,ge=100,le=20000)
    dissolve_by:Literal["all","category"]="all"
    @model_validator(mode="after")
    def second(self):
        if self.operation in ("intersection","clip","difference","spatial_join","nearest","aggregate") and not self.b:
            raise ValueError("This operation requires input B")
        return self

class SaveAnalysis(BaseModel):
    model_config=ConfigDict(extra="forbid")
    calculation_id:str=Field(pattern="^[a-f0-9]{64}$")
class ArchiveRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    confirmed:Literal[True]

from app.schemas.routing import RoutePoint
class MatrixRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    origins:list[RoutePoint]=Field(min_length=1,max_length=5)
    destinations:list[RoutePoint]=Field(min_length=1,max_length=5)
    max_snap_m:int=Field(default=1000,ge=25,le=2000)
    score_reference_minutes:float=Field(default=60,ge=1,le=240)

class RegionComparison(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    origins:list[RoutePoint]=Field(min_length=1,max_length=6)
    radius_km:float=Field(default=5,ge=0.1,le=50)
    categories:list[Category]=Field(default_factory=lambda:[Category.industrial,Category.industrial_park],min_length=1,max_length=9)
