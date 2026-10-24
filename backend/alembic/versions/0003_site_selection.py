"""Additive site-selection snapshots only; no changes to existing rows."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
revision="0003_site_selection"
down_revision="0002_logistics"
branch_labels=None
depends_on=None
def identity():return [sa.Column("id",sa.String(36),primary_key=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False)]
def fk(name,target,nullable=False):return sa.Column(name,sa.String(36),sa.ForeignKey(target),nullable=nullable)
def upgrade():
 op.create_table("site_scenarios",*identity(),sa.Column("name",sa.String(160),nullable=False),sa.Column("parameters",JSONB,nullable=False))
 op.create_table("site_candidates",*identity(),fk("scenario_id","site_scenarios.id"),fk("feature_id","spatial_features.id",True),
  sa.Column("logical_key",sa.String(60),nullable=False),sa.Column("geometry",Geometry("GEOMETRY",srid=4326,spatial_index=False),nullable=False),
  sa.Column("provenance",JSONB,nullable=False),sa.UniqueConstraint("scenario_id","logical_key"),
  sa.CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry) AND array_position(ARRAY['ST_Point','ST_Polygon','ST_MultiPolygon'],ST_GeometryType(geometry)) IS NOT NULL"))
 op.create_index("ix_site_candidates_scenario_id","site_candidates",["scenario_id"])
 op.create_index("idx_site_candidates_geometry","site_candidates",["geometry"],postgresql_using="gist")
 op.create_table("site_evaluations",*identity(),fk("scenario_id","site_scenarios.id"),sa.Column("calculation_id",sa.String(64),nullable=False,unique=True),sa.Column("result",JSONB,nullable=False))
 op.create_index("ix_site_evaluations_scenario_id","site_evaluations",["scenario_id"])
 op.create_table("site_criterion_values",*identity(),fk("evaluation_id","site_evaluations.id"),fk("candidate_id","site_candidates.id"),
  sa.Column("criterion_id",sa.String(60),nullable=False),sa.Column("value",sa.Float(),nullable=True),sa.Column("provenance",JSONB,nullable=False),
  sa.UniqueConstraint("evaluation_id","candidate_id","criterion_id"),sa.CheckConstraint("value IS NULL OR value>=0"))
 op.create_index("ix_site_criterion_values_evaluation_id","site_criterion_values",["evaluation_id"])
 for table in ("site_scenarios","site_candidates","site_evaluations","site_criterion_values"):
  op.execute('ALTER TABLE "'+table+'" ENABLE ROW LEVEL SECURITY')
  op.execute('REVOKE ALL ON TABLE "'+table+'" FROM PUBLIC')
def downgrade():
 raise RuntimeError("Destructive downgrade blocked; use a separately reviewed backup/restore procedure.")
