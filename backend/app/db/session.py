from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings


class DatabaseConfigurationError(RuntimeError):
    pass


def build_database_url(settings: Settings) -> URL:
    """Build in memory. Never log/render this URL with hide_password=False."""
    if settings.database_url:
        try:
            url = make_url(settings.database_url.get_secret_value())
        except Exception:
            raise DatabaseConfigurationError("Format DATABASE_URL tidak sah.") from None
        if url.get_backend_name() != "postgresql":
            raise DatabaseConfigurationError("Hanya PostgreSQL/PostGIS disokong.")
        if not url.host or not url.username or not url.password or not url.database:
            raise DatabaseConfigurationError("Butiran sambungan PostgreSQL belum lengkap.")
        return url.set(drivername="postgresql+psycopg")
    if not settings.database_configured:
        raise DatabaseConfigurationError("Kata laluan atau butiran sambungan setempat belum lengkap.")
    # URL.create handles @ : / # % and other literal password characters safely.
    return URL.create(
        "postgresql+psycopg", host=settings.database_host, port=settings.database_port,
        database=settings.database_name, username=settings.database_user,
        password=settings.database_password.get_secret_value(),
    )


def create_database_engine(settings: Settings):
    engine = create_engine(
        build_database_url(settings), poolclass=NullPool, echo=False,
        hide_parameters=True,
        connect_args={"sslmode": settings.database_ssl_mode, "connect_timeout": 8,
                      "application_name": "LogistiMap AI"},
    )

    @event.listens_for(engine, "connect")
    def configure_connection(dbapi_connection, _):
        # Configure after connecting: poolers may reject libpq startup "options".
        previous = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        try:
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SELECT pg_catalog.set_config('statement_timeout', '10000', false)")
                cursor.execute("SELECT pg_catalog.set_config('lock_timeout', '5000', false)")
                cursor.execute("SELECT pg_catalog.set_config('TimeZone', 'UTC', false)")
                cursor.execute("""
                    SELECT pg_catalog.quote_ident(n.nspname)
                    FROM pg_catalog.pg_extension e
                    JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace
                    WHERE e.extname='postgis'
                """)
                extension = cursor.fetchone()
                path = "public,extensions" if extension is None else "public," + extension[0] + ",extensions"
                cursor.execute("SELECT pg_catalog.set_config('search_path', %s, false)", (path,))
        finally:
            dbapi_connection.autocommit = previous

    return engine


@lru_cache
def get_engine():
    return create_database_engine(get_settings())


def check_database() -> dict:
    from app.db.verification import verify_connection
    with get_engine().connect() as connection:
        return verify_connection(connection, full=False)
