"""Read-only database verification. Return allowlisted facts, never connection secrets."""
import geoalchemy2  # Register PostGIS reflection types.
from sqlalchemy import inspect, text

EXPECTED_REVISION = "0004_geoai"
EXPECTED_TABLES = {
    "datasets", "categories", "spatial_features", "feature_categories", "study_areas",
    "analysis_jobs", "analysis_results", "candidate_sites", "optimization_scenarios",
    "vehicles", "shipments", "routing_references",
}
FOUNDATION_TABLES = set(EXPECTED_TABLES)
EXPECTED_TABLES |= {"logistics_depots","logistics_stops","logistics_vehicles","logistics_demands","optimization_jobs","optimization_solutions","vehicle_route_assignments","logistics_comparisons"}
PHASE5_TABLES = set(EXPECTED_TABLES)
EXPECTED_TABLES |= {"site_scenarios","site_candidates","site_evaluations","site_criterion_values"}
PHASE6_TABLES = set(EXPECTED_TABLES)
EXPECTED_TABLES |= {"geoai_sessions","geoai_confirmations"}
EXPECTED_GEOMETRY = {
    "site_candidates": ("GEOMETRY", False),
    "logistics_depots": ("POINT", False),
    "logistics_stops": ("POINT", False),
    "vehicle_route_assignments": ("MULTILINESTRING", True),
    "spatial_features": ("GEOMETRY", False),
    "study_areas": ("MULTIPOLYGON", False),
    "analysis_results": ("GEOMETRY", True),
    "routing_references": ("LINESTRING", True),
}
EXPECTED_INDEXES = {
    "spatial_features": {"ix_spatial_features_name", "ix_spatial_features_dataset_id"},
    "feature_categories": {"ix_feature_categories_category_id"},
    "analysis_results": {"ix_analysis_results_job_id"},
    "vehicles": {"ix_vehicles_scenario_id"},
    "shipments": {"ix_shipments_scenario_id"},
}


class DatabaseVerificationError(RuntimeError):
    pass


def verify_postgis(connection) -> dict:
    extension = connection.execute(text("""
        SELECT e.extversion, n.nspname FROM pg_catalog.pg_extension e
        JOIN pg_catalog.pg_namespace n ON n.oid=e.extnamespace
        WHERE e.extname='postgis'
    """)).first()
    if extension is None:
        raise DatabaseVerificationError("PostGIS belum diaktifkan pada pangkalan data sasaran.")
    raw = connection.connection.driver_connection
    if not raw.pgconn.ssl_in_use:
        raise DatabaseVerificationError("Sambungan SSL tidak dapat disahkan.")
    result = connection.execute(text("""
        SELECT ST_SRID(ST_SetSRID(ST_MakePoint(101.5, 3.1),4326)) AS srid,
        ST_Distance(ST_SetSRID(ST_MakePoint(0,0),4326)::geography,
                    ST_SetSRID(ST_MakePoint(1,0),4326)::geography)/1000 AS distance_km,
        ST_IsValid(ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))',4326)) AS valid,
        ST_Intersects(ST_MakeEnvelope(101,3,102,4,4326),
                      ST_SetSRID(ST_MakePoint(101.5,3.5),4326)) AS intersects
    """)).mappings().one()
    if result["srid"] != 4326 or not 111.30 < result["distance_km"] < 111.34 or not result["valid"] or not result["intersects"]:
        raise DatabaseVerificationError("Pemeriksaan fungsi spatial PostGIS gagal.")
    return {"connected": True, "ssl": True, "postgis_version": extension[0],
            "postgis_schema": extension[1], "spatial_function_checks": 4}


def verify_connection(connection, full=True) -> dict:
    report = verify_postgis(connection)
    tables = set(inspect(connection).get_table_names(schema="public"))
    missing = EXPECTED_TABLES - tables
    if missing or "alembic_version" not in tables:
        raise DatabaseVerificationError("Skema projek belum lengkap; jalankan migrasi selamat.")
    revision = connection.execute(text("SELECT version_num FROM public.alembic_version")).scalars().all()
    if revision != [EXPECTED_REVISION]:
        raise DatabaseVerificationError("Versi migrasi tidak sepadan dengan projek ini.")
    connection.execute(text("SELECT id FROM public.spatial_features LIMIT 1"))
    report.update({"migration": EXPECTED_REVISION, "database_verified": True})
    if not full:
        return report
    inspector = inspect(connection)
    geometries = connection.execute(text("""
        SELECT f_table_name AS table_name, f_geometry_column AS column_name, srid, type
        FROM geometry_columns WHERE f_table_schema='public'
    """)).mappings().all()
    geometry_lookup = {row["table_name"]: row for row in geometries}
    checked = []
    for table, (kind, nullable) in EXPECTED_GEOMETRY.items():
        row = geometry_lookup.get(table)
        if row is None or row["column_name"] != "geometry" or row["srid"] != 4326 or row["type"].upper() != kind:
            raise DatabaseVerificationError("Jenis geometri atau SRID jadual projek tidak sepadan.")
        column = next(c for c in inspector.get_columns(table, schema="public") if c["name"] == "geometry")
        if bool(column["nullable"]) != nullable:
            raise DatabaseVerificationError("Kekangan nullable geometri tidak sepadan.")
        checked.append({"table": table, "column": "geometry", "srid": 4326, "type": kind})
    indexes = connection.execute(text("""
        SELECT t.relname AS table_name, i.relname AS index_name, am.amname AS method,
               x.indisvalid, x.indisready
        FROM pg_catalog.pg_index x
        JOIN pg_catalog.pg_class t ON t.oid=x.indrelid
        JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
        JOIN pg_catalog.pg_class i ON i.oid=x.indexrelid
        JOIN pg_catalog.pg_am am ON am.oid=i.relam
        WHERE n.nspname='public'
    """)).mappings().all()
    for table in EXPECTED_GEOMETRY:
        expected = "idx_" + table + "_geometry"
        if not any(r["table_name"] == table and r["index_name"] == expected and
                   r["method"] == "gist" and r["indisvalid"] and r["indisready"] for r in indexes):
            raise DatabaseVerificationError("Indeks GiST geometri projek tidak lengkap.")
    for table, expected in EXPECTED_INDEXES.items():
        actual = {r["index_name"] for r in indexes if r["table_name"] == table and r["indisvalid"]}
        if not expected <= actual:
            raise DatabaseVerificationError("Indeks carian projek tidak lengkap.")
    rls = dict(connection.execute(text("""
        SELECT c.relname,c.relrowsecurity FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind='r'
    """)).all())
    if not all(rls.get(table) for table in EXPECTED_TABLES):
        raise DatabaseVerificationError("Perlindungan RLS jadual projek tidak lengkap.")
    categories = set(connection.execute(text("SELECT id FROM public.categories")).scalars())
    expected_categories = {"industrial","industrial_park","warehouse","logistics_hub",
                           "port","airport","road","rail","study_area"}
    if not expected_categories <= categories:
        raise DatabaseVerificationError("Kamus kategori projek belum lengkap.")
    report.update({"table_count": len(EXPECTED_TABLES), "geometry_columns": checked,
                   "spatial_indexes": len(EXPECTED_GEOMETRY), "rls_tables": len(EXPECTED_TABLES),
                   "category_count": len(categories)})
    return report


def safe_error(exc: Exception) -> dict:
    # Never serialize str(exc), repr(exc), engine URLs, parameters or tracebacks.
    from app.db.session import DatabaseConfigurationError
    if isinstance(exc, (DatabaseConfigurationError, DatabaseVerificationError)):
        return {"status": "blocked", "message": str(exc)}
    state = getattr(getattr(exc, "orig", exc), "sqlstate", None)
    messages = {
        "28P01": "Pengesahan gagal. Semak kata laluan dalam fail setempat.",
        "28000": "Akses sambungan tidak dibenarkan oleh pangkalan data.",
        "42501": "Akaun ini tidak mempunyai kebenaran yang diperlukan.",
        "42P01": "Jadual projek belum tersedia.",
        "55P03": "Pangkalan data sibuk; tiada perubahan diteruskan.",
    }
    return {"status": "blocked", "error_type": type(exc).__name__,
            "message": messages.get(state, "Sambungan atau operasi pangkalan data gagal. Semak rangkaian, kata laluan dan konfigurasi setempat.")}
