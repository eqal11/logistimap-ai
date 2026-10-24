"""Normalized shared feature model; category memberships can overlap.

Infrastructure types (parks, warehouses, ports, airports, roads, rail) share
provenance/geometry in spatial_features; categories avoid duplicate geometries.
Scenario entities are schema foundations only, not implemented workflows.
"""
from datetime import datetime, timezone
from uuid import uuid4

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def now():
    return datetime.now(timezone.utc)


class IdentityMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


feature_categories = Table(
    "feature_categories", Base.metadata,
    Column("feature_id", ForeignKey("spatial_features.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Dataset(IdentityMixin, Base):
    __tablename__ = "datasets"
    name: Mapped[str] = mapped_column(String(240))
    source: Mapped[str] = mapped_column(String(240))
    license: Mapped[str] = mapped_column(String(240))
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    import_log: Mapped[dict] = mapped_column(JSONB, default=dict)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))


class SpatialFeature(IdentityMixin, Base):
    __tablename__ = "spatial_features"
    __table_args__ = (
        UniqueConstraint("dataset_id", "source_id", name="uq_feature_source"),
        CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)", name="ck_feature_valid"),
        CheckConstraint("boundary_status IN ('not_applicable','unverified','verified','synthetic')", name="ck_boundary_status"),
    )
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    source_id: Mapped[str] = mapped_column(String(240))
    geometry: Mapped[object] = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=True))
    boundary_status: Mapped[str] = mapped_column(String(30), default="unverified")
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    categories: Mapped[list[Category]] = relationship(secondary=feature_categories, lazy="selectin")
    dataset: Mapped[Dataset] = relationship(lazy="joined")


class StudyArea(IdentityMixin, Base):
    __tablename__ = "study_areas"
    name: Mapped[str] = mapped_column(String(240))
    geometry: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=True))
    provenance: Mapped[dict] = mapped_column(JSONB, default=dict)


class AnalysisJob(IdentityMixin, Base):
    __tablename__ = "analysis_jobs"
    study_area_id: Mapped[str | None] = mapped_column(ForeignKey("study_areas.id"))
    operation: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)


class AnalysisResult(IdentityMixin, Base):
    __tablename__ = "analysis_results"
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    geometry: Mapped[object | None] = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=True))
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)


class CandidateSite(IdentityMixin, Base):
    __tablename__ = "candidate_sites"
    feature_id: Mapped[str] = mapped_column(ForeignKey("spatial_features.id"), unique=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_jobs.id"))
    criteria: Mapped[dict] = mapped_column(JSONB, default=dict)


class OptimizationScenario(IdentityMixin, Base):
    __tablename__ = "optimization_scenarios"
    name: Mapped[str] = mapped_column(String(240))
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)


class Vehicle(IdentityMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (CheckConstraint("capacity > 0", name="ck_vehicle_capacity"),)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("optimization_scenarios.id", ondelete="CASCADE"), index=True)
    depot_id: Mapped[str] = mapped_column(ForeignKey("spatial_features.id"))
    capacity: Mapped[float] = mapped_column(Float)
    capacity_unit: Mapped[str] = mapped_column(String(30))
    constraints: Mapped[dict] = mapped_column(JSONB, default=dict)


class Shipment(IdentityMixin, Base):
    __tablename__ = "shipments"
    __table_args__ = (CheckConstraint("demand > 0", name="ck_shipment_demand"),)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("optimization_scenarios.id", ondelete="CASCADE"), index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("spatial_features.id"))
    demand: Mapped[float] = mapped_column(Float)
    demand_unit: Mapped[str] = mapped_column(String(30))
    time_window: Mapped[dict | None] = mapped_column(JSONB)


class RoutingReference(IdentityMixin, Base):
    __tablename__ = "routing_references"
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("optimization_scenarios.id"))
    provider: Mapped[str] = mapped_column(String(100))
    profile: Mapped[str] = mapped_column(String(80))
    geometry: Mapped[object | None] = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=True))
    provenance: Mapped[dict] = mapped_column(JSONB, default=dict)
