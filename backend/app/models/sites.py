from sqlalchemy import String,Float,ForeignKey,UniqueConstraint,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.models.entities import Base,IdentityMixin
class SiteScenario(IdentityMixin,Base):
 __tablename__="site_scenarios"
 name:Mapped[str]=mapped_column(String(160))
 parameters:Mapped[dict]=mapped_column(JSONB)
class SiteCandidate(IdentityMixin,Base):
 __tablename__="site_candidates"
 scenario_id:Mapped[str]=mapped_column(ForeignKey("site_scenarios.id"),index=True)
 feature_id:Mapped[str|None]=mapped_column(ForeignKey("spatial_features.id"))
 logical_key:Mapped[str]=mapped_column(String(60))
 geometry:Mapped[object]=mapped_column(Geometry("GEOMETRY",srid=4326))
 provenance:Mapped[dict]=mapped_column(JSONB)
 __table_args__=(UniqueConstraint("scenario_id","logical_key"),CheckConstraint("ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry) AND array_position(ARRAY['ST_Point','ST_Polygon','ST_MultiPolygon'],ST_GeometryType(geometry)) IS NOT NULL"))
class SiteEvaluation(IdentityMixin,Base):
 __tablename__="site_evaluations"
 scenario_id:Mapped[str]=mapped_column(ForeignKey("site_scenarios.id"),index=True)
 calculation_id:Mapped[str]=mapped_column(String(64),unique=True)
 result:Mapped[dict]=mapped_column(JSONB)
class SiteCriterionValue(IdentityMixin,Base):
 __tablename__="site_criterion_values"
 evaluation_id:Mapped[str]=mapped_column(ForeignKey("site_evaluations.id"),index=True)
 candidate_id:Mapped[str]=mapped_column(ForeignKey("site_candidates.id"))
 criterion_id:Mapped[str]=mapped_column(String(60))
 value:Mapped[float|None]=mapped_column(Float)
 provenance:Mapped[dict]=mapped_column(JSONB)
 __table_args__=(UniqueConstraint("evaluation_id","candidate_id","criterion_id"),CheckConstraint("value IS NULL OR value>=0"))
