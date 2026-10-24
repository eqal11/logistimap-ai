"""Bounded logistics inputs. Times: seconds from day start; distance: metres; cost: MYR."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from app.schemas.routing import coordinate

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid",hide_input_in_errors=True,allow_inf_nan=False)

class Location(Strict):
    id:str=Field(min_length=1,max_length=60,pattern=r"^[\w.:-]+$")
    name:str=Field(min_length=1,max_length=160)
    coordinates:tuple[float,float]
    feature_id:str|None=Field(default=None,max_length=36)
    source_id:str|None=Field(default=None,max_length=240)
    @field_validator("coordinates",mode="before")
    @classmethod
    def coords(cls,v):return coordinate(v)

class Depot(Location):
    window:tuple[int,int]=(0,86400)
    @field_validator("window")
    @classmethod
    def window_valid(cls,v):
        if not 0<=v[0]<v[1]<=86400:raise ValueError("Window must increase within 0–86400 seconds")
        return v

class Stop(Depot):
    demand:int=Field(ge=1,le=1_000_000)
    service_s:int=Field(default=0,ge=0,le=14400)
    priority:int=Field(default=1,ge=1,le=10)
    mandatory:bool=False
    kind:Literal["delivery","pickup"]="delivery"
    pickup_id:str|None=Field(default=None,max_length=60)

class FleetVehicle(Strict):
    id:str=Field(min_length=1,max_length=60,pattern=r"^[\w.:-]+$")
    name:str=Field(min_length=1,max_length=100)
    vehicle_type:str=Field(default="User-defined vehicle",max_length=80)
    enabled:bool=True
    capacity:int=Field(ge=1,le=10_000_000)
    start_depot:str=Field(min_length=1,max_length=60)
    end_depot:str=Field(min_length=1,max_length=60)
    window:tuple[int,int]=(0,86400)
    max_distance_m:int=Field(default=1_000_000,ge=1,le=3_000_000)
    max_duration_s:int=Field(default=43200,ge=1,le=86400)
    cost_per_km:float=Field(default=0,ge=0,le=10000)
    fixed_cost:float=Field(default=0,ge=0,le=1_000_000)
    driver_cost_per_hour:float=Field(default=0,ge=0,le=10000)
    fuel_l_per_100km:float=Field(default=0,ge=0,le=200)
    fuel_price_per_l:float=Field(default=0,ge=0,le=100)
    _window=field_validator("window")(Depot.window_valid.__func__)
    @model_validator(mode="after")
    def fuel(self):
        if bool(self.fuel_l_per_100km)!=bool(self.fuel_price_per_l):raise ValueError("Fuel consumption and price must both be supplied or both zero")
        return self

class Scenario(Strict):
    name:str=Field(min_length=1,max_length=160)
    capacity_unit:str=Field(default="units",min_length=1,max_length=30)
    demand_context:Literal["hypothetical","user_supplied"]="hypothetical"
    notes:str=Field(default="",max_length=2000)
    depots:list[Depot]=Field(min_length=1,max_length=4)
    vehicles:list[FleetVehicle]=Field(min_length=1,max_length=6)
    stops:list[Stop]=Field(min_length=1,max_length=20)
    objective:Literal["distance","time","cost","vehicles","balance"]="distance"
    allow_unassigned:bool=True
    solver_seconds:int=Field(default=3,ge=1,le=20)
    max_snap_m:int=Field(default=1000,ge=25,le=2000)
    @model_validator(mode="after")
    def relations(self):
        ids=[p.id for p in self.depots+self.stops]
        if len(set(ids))!=len(ids):raise ValueError("Depot and stop identifiers must be unique")
        if len({v.id for v in self.vehicles})!=len(self.vehicles):raise ValueError("Vehicle identifiers must be unique")
        if not any(v.enabled for v in self.vehicles):raise ValueError("Enable at least one vehicle")
        depots={p.id:p for p in self.depots};stops={p.id:p for p in self.stops};paired=set()
        for v in self.vehicles:
            if v.start_depot not in depots or v.end_depot not in depots:raise ValueError("Vehicle refers to unknown depot")
            for depot in (depots[v.start_depot],depots[v.end_depot]):
                if max(v.window[0],depot.window[0])>=min(v.window[1],depot.window[1]):raise ValueError("Vehicle and depot operating windows do not overlap")
        for p in self.stops:
            if p.pickup_id:
                other=stops.get(p.pickup_id)
                if p.kind!="delivery" or not other or other.kind!="pickup" or other.demand!=p.demand or other.id in paired:raise ValueError("Delivery must pair with one unique equal-demand pickup")
                if p.mandatory!=other.mandatory:raise ValueError("Paired stops must share mandatory status")
                paired.add(other.id)
        if paired!={p.id for p in self.stops if p.kind=="pickup"}:raise ValueError("Every pickup requires exactly one paired delivery")
        return self

class Confirm(Strict):
    confirmed:Literal[True]

class Comparison(Strict):
    ids:list[str]=Field(min_length=2,max_length=4)
    name:str=Field(default="Fleet comparison",max_length=160)

class ImportLocations(Strict):
    format:Literal["csv","geojson"]
    content:str=Field(min_length=1,max_length=1_000_000)
    demand_context:Literal["hypothetical","user_supplied"]="hypothetical"
