import app.models.geoai
import io
from alembic import command
from alembic.config import Config
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from app.core.config import BACKEND_ROOT
from app.models.entities import Base
import app.models.logistics
import app.models.sites


def test_models_compile_for_postgres():
    assert len(Base.metadata.tables) == 26
    sql = "\n".join(str(CreateTable(table).compile(dialect=postgresql.dialect())) for table in Base.metadata.sorted_tables)
    assert "geometry(GEOMETRY,4326)" in sql
    assert "uq_feature_source" in sql
    assert "FOREIGN KEY" in sql


def test_offline_migration_compiles_spatial_indexes_and_rls():
    output = io.StringIO()
    config = Config(str(BACKEND_ROOT / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
    assert "USING gist" in sql
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert "0001_foundation" in sql
    assert "INSERT INTO categories" in sql
