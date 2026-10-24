import pytest
from pydantic import ValidationError
from sqlalchemy import create_mock_engine
from app.core.config import Settings
from app.db.session import build_database_url, DatabaseConfigurationError
from app.db.migrate import classify_schema, migration_config
from app.db.verification import EXPECTED_TABLES, EXPECTED_REVISION, DatabaseVerificationError, safe_error


def config(**kwargs):
    return Settings(_env_file=None, **kwargs)


def test_split_settings_build_psycopg_url_without_exposing_secret():
    # Test-only sentinel, never a user's credential.
    secret = "unit-test-only:@/#%?[]"
    settings = config(database_host="db.example.test", database_user="sample.user",
                      database_password=secret)
    url = build_database_url(settings)
    assert url.drivername == "postgresql+psycopg"
    assert url.password == secret and url.port == 5432
    assert secret not in repr(settings)
    assert secret not in str(url)
    assert settings.database_configured


def test_complete_url_remains_supported_and_uses_psycopg3():
    url = build_database_url(config(database_url="postgresql://sample:test-only@db.example.test:5432/postgres"))
    assert url.drivername == "postgresql+psycopg" and url.password == "test-only"


@pytest.mark.parametrize("kwargs", [
    {}, {"database_host":"db.example.test","database_user":"sample","database_password":""},
    {"database_url":"not-a-url"}, {"database_url":"sqlite:///test.db"},
    {"database_url":"postgresql://sample@db.example.test/postgres"},
])
def test_missing_or_invalid_credentials_fail_without_echoing_inputs(kwargs):
    with pytest.raises(DatabaseConfigurationError):
        build_database_url(config(**kwargs))


def test_insecure_ssl_mode_is_not_allowed():
    with pytest.raises(ValidationError):
        config(database_ssl_mode="disable")


def test_connection_engine_forces_ssl_and_hides_query_parameters(monkeypatch):
    from app.db import session
    captured = {}
    class FakeEngine:
        pass
    monkeypatch.setattr(session, "create_engine", lambda url, **kwargs: captured.update({"url":url,**kwargs}) or FakeEngine())
    monkeypatch.setattr(session.event, "listens_for", lambda *args,**kwargs: lambda fn: fn)
    settings = config(database_host="db.example.test",database_user="sample",database_password="test-only")
    session.create_database_engine(settings)
    assert captured["connect_args"]["sslmode"] == "require"
    assert captured["hide_parameters"] is True and captured["echo"] is False
    assert "options" not in captured["connect_args"]


def test_preflight_allows_new_project_without_touching_other_tables():
    assert classify_schema({"auth_data","unrelated_table"},[]) == "fresh"
    assert classify_schema(EXPECTED_TABLES|{"alembic_version"},[EXPECTED_REVISION]) == "current"


@pytest.mark.parametrize(("tables","revisions"),[
    ({"datasets"},[]),
    ({"alembic_version"},[]),
    (EXPECTED_TABLES|{"alembic_version"},["other_project_revision"]),
    ({"spatial_features","alembic_version"},[EXPECTED_REVISION]),
])
def test_preflight_refuses_collisions_and_unknown_history(tables,revisions):
    with pytest.raises(DatabaseVerificationError):
        classify_schema(tables,revisions)


def test_migration_plan_is_the_reviewed_phase1_revision():
    from alembic.script import ScriptDirectory
    assert ScriptDirectory.from_config(migration_config()).get_heads() == [EXPECTED_REVISION]


def test_database_error_messages_never_serialize_provider_details():
    # Deliberately simulate an upstream exception containing a secret.
    sentinel = "unit-test-secret-do-not-echo"
    error = safe_error(RuntimeError("postgresql://sample:"+sentinel+"@db.example.test/postgres"))
    assert sentinel not in str(error)
    assert "postgresql://" not in str(error)
    assert error["status"] == "blocked"
