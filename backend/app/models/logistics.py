"""Additive Phase 5 models. Foundation vehicles/shipments are retained unchanged."""
from sqlalchemy import String,Float,Integer,ForeignKey,UniqueConstraint,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.models.entities import Base,IdentityMixin

class LogisticsDepot(IdentityMixin,Base):
    __tablename__="logistics_depots"
    scenario_id:Mapped[str]=mapped_column(ForeignKey("optimization_scenarios.id"),index=True)
    logical_key:Mapped[str]=mapped_column(String(60))
    geometry:Mapped[object]=mapped_column(Geometry("POINT",srid=4326))
    parameters:Mapped[dict]=mapped_column(JSONB)
    __table_args__=(UniqueConstraint("scenario_id","logical_key"),CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)"),)

class LogisticsVehicle(IdentityMixin,Base):
    __tablename__="logistics_vehicles"
    scenario_id:Mapped[str]=mapped_column(ForeignKey("optimization_scenarios.id"),index=True)
    start_depot_id:Mapped[str]=mapped_column(ForeignKey("logistics_depots.id"))
    end_depot_id:Mapped[str]=mapped_column(ForeignKey("logistics_depots.id"))
    logical_key:Mapped[str]=mapped_column(String(60))
    capacity:Mapped[int]=mapped_column(Integer)
    parameters:Mapped[dict]=mapped_column(JSONB)
    __table_args__=(UniqueConstraint("scenario_id","logical_key"),CheckConstraint("capacity>0"),)

class LogisticsStop(IdentityMixin,Base):
    __tablename__="logistics_stops"
    scenario_id:Mapped[str]=mapped_column(ForeignKey("optimization_scenarios.id"),index=True)
    logical_key:Mapped[str]=mapped_column(String(60))
    geometry:Mapped[object]=mapped_column(Geometry("POINT",srid=4326))
    parameters:Mapped[dict]=mapped_column(JSONB)
    __table_args__=(UniqueConstraint("scenario_id","logical_key"),CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)"),)

class LogisticsDemand(IdentityMixin,Base):
    __tablename__="logistics_demands"
    stop_id:Mapped[str]=mapped_column(ForeignKey("logistics_stops.id"),unique=True)
    pickup_stop_id:Mapped[str|None]=mapped_column(ForeignKey("logistics_stops.id"))
    amount:Mapped[int]=mapped_column(Integer)
    unit:Mapped[str]=mapped_column(String(30))
    context:Mapped[str]=mapped_column(String(30))
    __table_args__=(CheckConstraint("amount>0"),)

class OptimizationJob(IdentityMixin,Base):
    __tablename__="optimization_jobs"
    scenario_id:Mapped[str]=mapped_column(ForeignKey("optimization_scenarios.id"),index=True)
    status:Mapped[str]=mapped_column(String(30))
    metadata_json:Mapped[dict]=mapped_column("metadata",JSONB)

class OptimizationSolution(IdentityMixin,Base):
    __tablename__="optimization_solutions"
    scenario_id:Mapped[str]=mapped_column(ForeignKey("optimization_scenarios.id"),index=True)
    job_id:Mapped[str]=mapped_column(ForeignKey("optimization_jobs.id"),unique=True)
    result:Mapped[dict]=mapped_column(JSONB)

class VehicleAssignment(IdentityMixin,Base):
    __tablename__="vehicle_route_assignments"
    solution_id:Mapped[str]=mapped_column(ForeignKey("optimization_solutions.id"),index=True)
    vehicle_id:Mapped[str]=mapped_column(ForeignKey("logistics_vehicles.id"))
    geometry:Mapped[object|None]=mapped_column(Geometry("MULTILINESTRING",srid=4326))
    summary:Mapped[dict]=mapped_column(JSONB)

class LogisticsComparison(IdentityMixin,Base):
    __tablename__="logistics_comparisons"
    name:Mapped[str]=mapped_column(String(160))
    result:Mapped[dict]=mapped_column(JSONB)
