"""Run local integration without supplying secrets through CLI arguments or output."""
import argparse
import json

from dotenv import set_key

from app.core.config import BACKEND_ROOT, Settings
from app.db.migrate import migrate_safely
from app.db.session import build_database_url, create_database_engine
from app.db.verification import DatabaseVerificationError, safe_error, verify_postgis

TARGET_HOST = "aws-0-ap-northeast-2.pooler.supabase.com"
TARGET_USER = "postgres.ogzxijcbdihitxpwbolo"


def main():
    parser = argparse.ArgumentParser(description="LogistiMap AI: semak sambungan dan migrasi Supabase dengan selamat.")
    parser.add_argument("--apply", action="store_true", help="Jalankan migrasi projek dalam transaksi.")
    parser.add_argument("--activate", action="store_true", help="Tukar DATA_MODE selepas migrasi dan semakan berjaya.")
    args = parser.parse_args()
    engine = None
    try:
        if args.activate and not args.apply:
            raise DatabaseVerificationError("--activate memerlukan --apply dan semakan skema berjaya.")
        settings = Settings()
        url = build_database_url(settings)
        if (url.host, url.port or 5432, url.database, url.username) != (TARGET_HOST, 5432, "postgres", TARGET_USER):
            raise DatabaseVerificationError("Sasaran sambungan tidak sepadan dengan projek Supabase yang dibenarkan.")
        engine = create_database_engine(settings)
        if args.apply:
            report = migrate_safely(engine)
        else:
            with engine.connect() as connection:
                report = verify_postgis(connection)
            report["migration_action"] = "not_applied"
        if args.activate:
            set_key(str(BACKEND_ROOT / ".env"), "DATA_MODE", "postgis", quote_mode="always")
            report["data_mode_activated"] = "postgis"
        print(json.dumps({"status": "ok", **report}, ensure_ascii=True, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps(safe_error(exc), ensure_ascii=True))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
