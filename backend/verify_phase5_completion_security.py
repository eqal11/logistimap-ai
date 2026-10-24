"""Local-only redacted credential scan. Prints counts, never secret values."""
import json,hashlib,urllib.parse,subprocess
from pathlib import Path
from dotenv import dotenv_values
from app.core.config import PROJECT_ROOT,BACKEND_ROOT
root=PROJECT_ROOT
values=dotenv_values(BACKEND_ROOT/".env")
password=values.get("DATABASE_PASSWORD") or ""
needles={password,urllib.parse.quote(password,safe=""),urllib.parse.quote_plus(password)}
if values.get("DATABASE_URL"):needles.add(values["DATABASE_URL"])
needles={n.encode() for n in needles if len(n)>=8}
assert needles
suffixes={".md",".py",".ts",".tsx",".json",".html",".css",".js",".mjs",".txt",".geojson",".csv",".toml",".yaml",".yml"}
skipped={".venv","node_modules",".git",".cache","__pycache__"}
files=[p for p in root.rglob("*") if p.is_file() and p.suffix in suffixes and not skipped.intersection(p.relative_to(root).parts) and p.name!=".env"]
hits=[]
for p in files:
 if any(needle in p.read_bytes() for needle in needles):hits.append(str(p.relative_to(root)))
ignored=subprocess.run(["git","check-ignore","backend/.env"],cwd=root,capture_output=True).returncode==0
tracked=subprocess.run(["git","ls-files","--error-unmatch","backend/.env"],cwd=root,capture_output=True).returncode==0
report={"status":"passed" if not hits and ignored and not tracked else "failed","files_scanned":len(files),"secret_matches":len(hits),"env_ignored":ignored,"env_tracked":tracked,"scope":"first-party source/docs and frontend production dist, excludes local caches/venv/node_modules/.env","env_sha256":hashlib.sha256((BACKEND_ROOT/".env").read_bytes()).hexdigest()}
(root/"docs"/"phase5-completion-secret-scan.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="env_sha256"}))
raise SystemExit(0 if report["status"]=="passed" else 1)
