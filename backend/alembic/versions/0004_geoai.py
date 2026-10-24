"""Two additive local GeoAI snapshot/audit tables. Existing records untouched."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0004_geoai'
down_revision='0003_site_selection'
branch_labels=None
depends_on=None
def identity():return [sa.Column('id',sa.String(36),primary_key=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False)]
def upgrade():
 op.create_table('geoai_sessions',*identity(),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('snapshot',JSONB,nullable=False),sa.CheckConstraint('octet_length(snapshot::text)<=8000000'))
 op.create_index('ix_geoai_sessions_expires_at','geoai_sessions',['expires_at'])
 op.create_table('geoai_confirmations',*identity(),sa.Column('session_key',sa.String(36),nullable=False),sa.Column('action',sa.String(70),nullable=False),sa.Column('request_digest',sa.String(64),nullable=False),sa.Column('outcome',JSONB,nullable=False))
 op.create_index('ix_geoai_confirmations_session_key','geoai_confirmations',['session_key'])
 for t in ('geoai_sessions','geoai_confirmations'):
  op.execute('ALTER TABLE "'+t+'" ENABLE ROW LEVEL SECURITY')
  op.execute('REVOKE ALL ON TABLE "'+t+'" FROM PUBLIC')
def downgrade():raise RuntimeError('Destructive downgrade blocked; separately reviewed backup/restore required.')
