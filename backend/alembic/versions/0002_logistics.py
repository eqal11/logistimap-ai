"""Phase 5 additive logistics tables. Does not update or delete existing records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
revision="0002_logistics"
down_revision="0001_foundation"
branch_labels=None
depends_on=None

def identity():return [sa.Column("id",sa.String(36),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False)]
def fk(name,target,nullable=False):return sa.Column(name,sa.String(36),sa.ForeignKey(target),nullable=nullable)
def json(name):return sa.Column(name,JSONB,nullable=False)
def upgrade():
    for table in ("logistics_depots","logistics_stops"):
        op.create_table(table,*identity(),fk("scenario_id","optimization_scenarios.id"),
            sa.Column("logical_key",sa.String(60),nullable=False),
            sa.Column("geometry",Geometry("POINT",srid=4326,spatial_index=False),nullable=False),json("parameters"),
            sa.UniqueConstraint("scenario_id","logical_key"),sa.CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)"))
        op.create_index("ix_"+table+"_scenario_id",table,["scenario_id"])
        op.create_index("idx_"+table+"_geometry",table,["geometry"],postgresql_using="gist")
    op.create_table("logistics_vehicles",*identity(),fk("scenario_id","optimization_scenarios.id"),
        fk("start_depot_id","logistics_depots.id"),fk("end_depot_id","logistics_depots.id"),
        sa.Column("logical_key",sa.String(60),nullable=False),sa.Column("capacity",sa.Integer(),nullable=False),json("parameters"),
        sa.UniqueConstraint("scenario_id","logical_key"),sa.CheckConstraint("capacity>0"))
    op.create_index("ix_logistics_vehicles_scenario_id","logistics_vehicles",["scenario_id"])
    op.create_table("logistics_demands",*identity(),fk("stop_id","logistics_stops.id"),fk("pickup_stop_id","logistics_stops.id",True),
        sa.Column("amount",sa.Integer(),nullable=False),sa.Column("unit",sa.String(30),nullable=False),
        sa.Column("context",sa.String(30),nullable=False),sa.UniqueConstraint("stop_id"),sa.CheckConstraint("amount>0"))
    op.create_table("optimization_jobs",*identity(),fk("scenario_id","optimization_scenarios.id"),
        sa.Column("status",sa.String(30),nullable=False),json("metadata"))
    op.create_index("ix_optimization_jobs_scenario_id","optimization_jobs",["scenario_id"])
    op.create_table("optimization_solutions",*identity(),fk("scenario_id","optimization_scenarios.id"),
        fk("job_id","optimization_jobs.id"),json("result"),sa.UniqueConstraint("job_id"))
    op.create_index("ix_optimization_solutions_scenario_id","optimization_solutions",["scenario_id"])
    op.create_table("vehicle_route_assignments",*identity(),fk("solution_id","optimization_solutions.id"),
        fk("vehicle_id","logistics_vehicles.id"),
        sa.Column("geometry",Geometry("MULTILINESTRING",srid=4326,spatial_index=False),nullable=True),json("summary"))
    op.create_index("ix_vehicle_route_assignments_solution_id","vehicle_route_assignments",["solution_id"])
    op.create_index("idx_vehicle_route_assignments_geometry","vehicle_route_assignments",["geometry"],postgresql_using="gist")
    op.create_table("logistics_comparisons",*identity(),sa.Column("name",sa.String(160),nullable=False),json("result"))
    for table in ("logistics_depots","logistics_stops","logistics_vehicles","logistics_demands","optimization_jobs","optimization_solutions","vehicle_route_assignments","logistics_comparisons"):
        op.execute('ALTER TABLE "'+table+'" ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE "'+table+'" FROM PUBLIC')
def downgrade():
    raise RuntimeError("Phase 5 downgrade is intentionally blocked to preserve logistics records. Use an explicitly reviewed backup/restore procedure.")
