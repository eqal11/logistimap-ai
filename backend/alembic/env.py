import app.models.geoai
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import context
from app.db.session import get_engine
from app.models.entities import Base
import app.models.logistics
import app.models.sites

target_metadata = Base.metadata


def run_online(connection):
    context.configure(connection=connection, target_metadata=target_metadata,
                      compare_type=True, version_table_schema="public")
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url="postgresql+psycopg://", target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"},
                      version_table_schema="public")
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    # Reuse the migration runner's advisory lock and transaction.
    run_online(context.config.attributes["connection"])
else:
    with get_engine().connect() as connection:
        run_online(connection)
