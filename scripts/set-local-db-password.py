"""Local password entry: masked console input, no command-line secret arguments."""
import getpass
from pathlib import Path
import sys
import warnings

from dotenv import set_key

warnings.simplefilter("error", getpass.GetPassWarning)
try:
    password = getpass.getpass("Kata laluan pangkalan data (input tersembunyi): ")
except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
    print("Input tersembunyi tidak tersedia; tiada kata laluan disimpan.")
    raise SystemExit(1)
if not password:
    print("Kata laluan kosong; tiada perubahan dibuat.")
    raise SystemExit(1)
env_file = Path(__file__).resolve().parents[1] / "backend" / ".env"
set_key(str(env_file), "DATABASE_PASSWORD", password, quote_mode="always", encoding="utf-8")
password = None
print("Kata laluan disimpan dalam fail setempat yang diabaikan Git.")
