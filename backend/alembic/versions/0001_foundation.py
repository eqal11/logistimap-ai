"""Phase 1 normalized spatial foundation. No synthetic records are seeded."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def identity():
    return [sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)]


def json_column(name, nullable=False):
    return sa.Column(name, JSONB, nullable=nullable)


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table("datasets", *identity(),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("source", sa.String(240), nullable=False),
        sa.Column("license", sa.String(240), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False), json_column("import_log"))
    op.create_table("categories",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("label", sa.String(100), nullable=False))
    category_table = sa.table("categories", sa.column("id", sa.String), sa.column("label", sa.String))
    op.bulk_insert(category_table, [
        {"id": key, "label": label} for key, label in [
            ("industrial", "Industrial facilities"), ("industrial_park", "Industrial parks"),
            ("warehouse", "Warehouses"), ("logistics_hub", "Logistics hubs"),
            ("port", "Ports"), ("airport", "Airports"), ("road", "Road references"),
            ("rail", "Rail infrastructure"), ("study_area", "Study areas")]])
    op.create_table("spatial_features", *identity(),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("source_id", sa.String(240), nullable=False),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=False),
        sa.Column("boundary_status", sa.String(30), nullable=False), json_column("attributes"),
        sa.UniqueConstraint("dataset_id", "source_id", name="uq_feature_source"),
        sa.CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)", name="ck_feature_valid"),
        sa.CheckConstraint("boundary_status IN ('not_applicable','unverified','verified','synthetic')", name="ck_boundary_status"))
    op.create_index("ix_spatial_features_name", "spatial_features", ["name"])
    op.create_index("ix_spatial_features_dataset_id", "spatial_features", ["dataset_id"])
    op.create_table("feature_categories",
        sa.Column("feature_id", sa.String(36), sa.ForeignKey("spatial_features.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", sa.String(40), sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True))
    op.create_index("ix_feature_categories_category_id", "feature_categories", ["category_id"])
    op.create_table("study_areas", *identity(),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
        json_column("provenance"))
    op.create_table("analysis_jobs", *identity(),
        sa.Column("study_area_id", sa.String(36), sa.ForeignKey("study_areas.id")),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), json_column("parameters"))
    op.create_table("analysis_results", *identity(),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326, spatial_index=False)), json_column("summary"))
    op.create_index("ix_analysis_results_job_id", "analysis_results", ["job_id"])
    op.create_table("candidate_sites", *identity(),
        sa.Column("feature_id", sa.String(36), sa.ForeignKey("spatial_features.id"), nullable=False, unique=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("analysis_jobs.id")), json_column("criteria"))
    op.create_table("optimization_scenarios", *identity(),
        sa.Column("name", sa.String(240), nullable=False), json_column("parameters"))
    op.create_table("vehicles", *identity(),
        sa.Column("scenario_id", sa.String(36), sa.ForeignKey("optimization_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("depot_id", sa.String(36), sa.ForeignKey("spatial_features.id"), nullable=False),
        sa.Column("capacity", sa.Float(), nullable=False),
        sa.Column("capacity_unit", sa.String(30), nullable=False), json_column("constraints"),
        sa.CheckConstraint("capacity > 0", name="ck_vehicle_capacity"))
    op.create_index("ix_vehicles_scenario_id", "vehicles", ["scenario_id"])
    op.create_table("shipments", *identity(),
        sa.Column("scenario_id", sa.String(36), sa.ForeignKey("optimization_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination_id", sa.String(36), sa.ForeignKey("spatial_features.id"), nullable=False),
        sa.Column("demand", sa.Float(), nullable=False),
        sa.Column("demand_unit", sa.String(30), nullable=False), json_column("time_window", nullable=True),
        sa.CheckConstraint("demand > 0", name="ck_shipment_demand"))
    op.create_index("ix_shipments_scenario_id", "shipments", ["scenario_id"])
    op.create_table("routing_references", *identity(),
        sa.Column("scenario_id", sa.String(36), sa.ForeignKey("optimization_scenarios.id")),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("profile", sa.String(80), nullable=False),
        sa.Column("geometry", Geometry("LINESTRING", srid=4326, spatial_index=False)), json_column("provenance"))
    for table in ["spatial_features", "study_areas", "analysis_results", "routing_references"]:
        op.create_index("idx_" + table + "_geometry", table, ["geometry"], postgresql_using="gist")
    # No anonymous/public Supabase Data API access. Use a backend-only read role.
    for table in ["datasets", "categories", "spatial_features", "feature_categories", "study_areas",
                  "analysis_jobs", "analysis_results", "candidate_sites", "optimization_scenarios",
                  "vehicles", "shipments", "routing_references"]:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL ON TABLE "{table}" FROM PUBLIC')


def downgrade():
    # Explicit operator command only; removes application data.
    for table in ["routing_references", "shipments", "vehicles", "optimization_scenarios",
                  "candidate_sites", "analysis_results", "analysis_jobs", "study_areas",
                  "feature_categories", "spatial_features", "categories", "datasets"]:
        op.drop_table(table)
    # Leave the shared PostGIS extension installed.
