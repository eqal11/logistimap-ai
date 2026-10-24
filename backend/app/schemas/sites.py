from typing import Literal
from uuid import UUID
from pydantic import Field,model_validator,field_validator
from shapely.geometry import shape
from app.schemas.optimization import Strict
from app.schemas.spatial import Geometry
from app.schemas.routing import RoutePoint
from app.sites.catalog import CATALOG

class SuppliedValue(Strict):
 value:float=Field(ge=0,le=1e12)
 note:str=Field(min_length=3,max_length=500)
class SiteCandidate(Strict):
 id:str=Field(min_length=1,max_length=60,pattern=r"^[\w.:-]+$")
 name:str=Field(min_length=1,max_length=160)
 feature_id:UUID|None=None
 geometry:Geometry|None=None
 kind:Literal["hypothetical_site","reported_existing_facility"]="hypothetical_site"
 values:dict[str,SuppliedValue]=Field(default_factory=dict,max_length=8)
 @model_validator(mode="after")
 def valid(self):
  if (self.feature_id is None)==(self.geometry is None):raise ValueError("Choose a mapped feature ID or user geometry")
  if self.geometry:
   if self.geometry.type not in ("Point","Polygon","MultiPolygon"):raise ValueError("Candidates require Point, Polygon or MultiPolygon")
   bounds=shape(self.geometry.model_dump()).bounds
   if not (99<=bounds[0]<=bounds[2]<=120 and 0<=bounds[1]<=bounds[3]<=8):raise ValueError("Candidate must be in the Malaysian study region")
   if bounds[2]-bounds[0]>1 or bounds[3]-bounds[1]>1:raise ValueError("Candidate extent exceeds 1 degree")
  if set(self.values)-set(CATALOG):raise ValueError("Unknown criterion value")
  return self
class SiteCriterion(Strict):
 id:str
 source:Literal["gis","network","user"]="gis"
 direction:Literal["cost","benefit"]
 weight:float=Field(default=1,ge=0,le=1e6)
 @model_validator(mode="after")
 def known(self):
  if self.id not in CATALOG:raise ValueError("Unknown criterion")
  native=CATALOG[self.id][3]
  if self.source!="user" and self.source!=native:raise ValueError("Dataset unavailable; use explicitly supplied values or another criterion")
  return self
class SiteScenario(Strict):
 name:str=Field(min_length=1,max_length=160)
 candidates:list[SiteCandidate]=Field(min_length=1,max_length=12)
 criteria:list[SiteCriterion]=Field(min_length=1,max_length=8)
 method:Literal["wlc","ahp"]="wlc"
 ahp_matrix:list[list[float]]|None=Field(default=None,max_length=8)
 allow_inconsistent:bool=False
 missing_policy:Literal["reject","exclude_criterion","exclude_candidate"]="reject"
 radius_m:int=Field(default=5000,ge=100,le=25000)
 targets:dict[Literal["port","airport","network"],RoutePoint]=Field(default_factory=dict,max_length=3)
 max_snap_m:int=Field(default=1000,ge=25,le=2000)
 sensitivity_delta:float=Field(default=.2,gt=0,le=.9)
 @model_validator(mode="after")
 def unique(self):
  if len({p.id for p in self.candidates})!=len(self.candidates):raise ValueError("Candidate IDs must be unique")
  refs=[str(p.feature_id) for p in self.candidates if p.feature_id]
  if len(set(refs))!=len(refs):raise ValueError("Mapped candidates must be distinct")
  if len({p.id for p in self.criteria})!=len(self.criteria):raise ValueError("Criterion IDs must be unique")
  for c in self.criteria:
   if c.source=="network" and c.id.split("_")[0] not in self.targets:raise ValueError("Choose an exact target reference for each road criterion")
  return self
class AHPRequest(Strict):
 matrix:list[list[float]]=Field(min_length=1,max_length=8)
class SiteImport(Strict):
 format:Literal["csv","geojson"]
 content:str=Field(min_length=1,max_length=1_000_000)
class SiteSave(Strict):
 calculation_id:str=Field(pattern="^[a-f0-9]{64}$")
