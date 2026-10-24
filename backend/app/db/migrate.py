"""Project-scoped, transactional migration runner. No stamping, drops or fixture seeding."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.config import BACKEND_ROOT
from app.db.verification import (
    EXPECTED_REVISION, EXPECTED_TABLES, FOUNDATION_TABLES, PHASE5_TABLES, PHASE6_TABLES, DatabaseVerificationError,
    verify_connection, verify_postgis,
)


def classify_schema(tables: set[str], revisions: list[str]) -> str:
    project_tables = tables & EXPECTED_TABLES
    if "alembic_version" in tables:
        if revisions == ["0001_foundation"] and project_tables == FOUNDATION_TABLES:
            return "upgrade"
        if revisions == ["0002_logistics"] and project_tables == PHASE5_TABLES:
            return "upgrade"
        if revisions == ["0003_site_selection"] and project_tables == PHASE6_TABLES:
            return "upgrade"
        if revisions != [EXPECTED_REVISION] or project_tables != EXPECTED_TABLES:
            raise DatabaseVerificationError(
                "Sejarah Alembic atau jadual sedia ada tidak sepadan. Migrasi dihentikan tanpa overwrite atau stamp."
            )
        return "current"
    if project_tables:
        raise DatabaseVerificationError(
            "Nama jadual projek bertindih dengan jadual sedia ada tanpa sejarah migrasi. Tiada perubahan dibuat."
        )
    return "fresh"


def migration_config(connection=None) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    if ScriptDirectory.from_config(config).get_current_head() != EXPECTED_REVISION:
        raise DatabaseVerificationError("Migrasi pada cakera tidak sepadan dengan versi yang disemak.")
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def migrate_safely(engine) -> dict:
    with engine.begin() as connection:
        locked = connection.execute(text("SELECT pg_catalog.pg_try_advisory_xact_lock(1748835340,1)")).scalar_one()
        if not locked:
            raise DatabaseVerificationError("Satu lagi proses migrasi projek sedang berjalan.")
        verify_postgis(connection)
        tables = set(inspect(connection).get_table_names(schema="public"))
        revisions = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all() if "alembic_version" in tables else []
        state = classify_schema(tables, revisions)
        if state in ("fresh","upgrade"):
            # Existing migration is additive. One external transaction owns all DDL.
            command.upgrade(migration_config(connection), "head")
        report = verify_connection(connection, full=True)
        report["migration_action"] = "applied" if state in ("fresh","upgrade") else "already_current"
    # Only reached after PostgreSQL committed the verified transaction.
    return report
