"""Strict GeoAI boundary: only approved tools and bounded requests."""
from typing import Literal,Any
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.schemas.spatial import Category
class Strict(BaseModel):
 model_config=ConfigDict(extra="forbid",allow_inf_nan=False,hide_input_in_errors=True)
class Empty(Strict):pass
class Search(Strict):
 place:str=Field(min_length=1,max_length=80)
 categories:list[Category]=Field(min_length=1,max_length=8)
 radius_km:float=Field(gt=0,le=25)
 limit:int=Field(default=100,ge=1,le=200)
 offset:int=Field(default=0,ge=0,le=2000)
class Feature(Strict):
 feature_id:UUID|None=None
class Buffer(Strict):
 feature_ids:list[UUID]=Field(default_factory=list,max_length=20)
 distance_m:float=Field(gt=0,le=25000)
class Intersection(Strict):
 feature_ids:list[UUID]=Field(min_length=2,max_length=2)
class Clusters(Search):
 eps_m:float=Field(default=1000,ge=25,le=20000)
 min_points:int=Field(default=3,ge=2,le=100)
class Density(Strict):
 places:list[str]=Field(min_length=2,max_length=6)
 radius_km:float=Field(gt=0,le=25)
class Road(Strict):
 origin:str=Field(min_length=1,max_length=80)
 destination:str=Field(min_length=1,max_length=80)
class Accessibility(Strict):
 origins:list[str]=Field(min_length=1,max_length=5)
 destination:str=Field(min_length=1,max_length=80)
class Rank(Strict):
 destination:str=Field(default="Port Klang",min_length=1,max_length=80)
 top:int=Field(default=3,ge=1,le=5)
class Saved(Strict):
 id:UUID|None=None
class MCDA(Strict):
 id:UUID|None=None
 weights:dict[str,float]=Field(default_factory=dict,max_length=8)
 @model_validator(mode="after")
 def valid(self):
  if any(not isinstance(v,(int,float)) or v<0 or v>1000 for v in self.weights.values()):raise ValueError("Invalid weights")
  return self
class Explain(Saved):
 candidate_a:str|None=Field(default=None,max_length=60)
 candidate_b:str|None=Field(default=None,max_length=60)
class Compare(Strict):
 ids:list[UUID]=Field(min_length=2,max_length=4)
class Fleet(Saved):
 vehicle_counts:list[int]=Field(default_factory=list,max_length=3)
 @model_validator(mode="after")
 def counts(self):
  if any(x<1 or x>6 for x in self.vehicle_counts) or len(set(self.vehicle_counts))!=len(self.vehicle_counts):raise ValueError("Use 1â€“8 unique vehicle counts")
  return self
class Filter(Strict):
 top:int=Field(default=3,ge=1,le=200)
class ToolCall(Strict):
 tool:str=Field(min_length=1,max_length=70)
 arguments:dict[str,Any]=Field(default_factory=dict,max_length=12)
class Chat(Strict):
 session_id:UUID|None=None
 message:str=Field(min_length=1,max_length=1800)
 language:Literal["auto","ms","en"]="auto"
 mode:Literal["deterministic","llm"]="deterministic"
 selected_feature_ids:list[UUID]=Field(default_factory=list,max_length=20)
 scenario_id:UUID|None=None
 mcda_id:UUID|None=None
class Execute(Strict):
 session_id:UUID|None=None
 calls:list[ToolCall]=Field(min_length=1,max_length=6)
 language:Literal["ms","en"]="en"
class Confirm(Strict):
 session_id:UUID
 token:str=Field(pattern="^[a-f0-9]{64}$")
 confirmed:Literal[True]
class SaveRequest(Strict):
 session_id:UUID
class ToolResult(Strict):
 id:str
 tool:str
 status:Literal["completed","failed","pending_confirmation","cancelled"]
 data:dict[str,Any]=Field(default_factory=dict)
 features:list[dict[str,Any]]=Field(default_factory=list,max_length=2000)
 rows:list[dict[str,Any]]=Field(default_factory=list,max_length=2000)
 summary:dict[str,Any]=Field(default_factory=dict)
 warnings:list[str]=Field(default_factory=list)
 attribution:str="Â© OpenStreetMap contributors Â· ODbL 1.0; supplied scenario assumptions unverified"
 crs:Literal["EPSG:4326"]="EPSG:4326"
 executed_at:str
 measurement_method:str="See tool output and methodology"
