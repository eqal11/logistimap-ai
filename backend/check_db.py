"""Read-only connection, PostGIS, table/index check; never prints connection secrets."""
import argparse
import json

from app.db.session import get_engine
from app.db.verification import safe_error, verify_connection, verify_postgis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection-only", action="store_true")
    args = parser.parse_args()
    try:
        with get_engine().connect() as connection:
            report = verify_postgis(connection) if args.connection_only else verify_connection(connection)
    except Exception as exc:
        print(json.dumps(safe_error(exc), ensure_ascii=True))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
