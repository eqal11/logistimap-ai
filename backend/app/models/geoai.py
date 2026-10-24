from sqlalchemy import String,DateTime,ForeignKey,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.models.entities import Base,IdentityMixin
class GeoAISession(IdentityMixin,Base):
 __tablename__='geoai_sessions'
 expires_at:Mapped[object]=mapped_column(DateTime(timezone=True),index=True)
 snapshot:Mapped[dict]=mapped_column(JSONB)
 __table_args__=(CheckConstraint("octet_length(snapshot::text)<=8000000"),)
class GeoAIConfirmation(IdentityMixin,Base):
 __tablename__='geoai_confirmations'
 session_key:Mapped[str]=mapped_column(String(36),index=True)
 action:Mapped[str]=mapped_column(String(70))
 request_digest:Mapped[str]=mapped_column(String(64))
 outcome:Mapped[dict]=mapped_column(JSONB)
