import json
from pathlib import Path
import httpx
from app.services.osm import ssl_context
from app.db.verification import safe_error
def main():
 names=["Tanjong Malim, Perak, Malaysia","Rawang, Selangor, Malaysia","Shah Alam, Selangor, Malaysia","Bukit Raja, Selangor, Malaysia","Klang, Selangor, Malaysia","Port Klang, Selangor, Malaysia"]
 with httpx.Client(base_url="http://127.0.0.1:8000",verify=ssl_context(),timeout=65) as c:
  points=[]
  for name in names:
   response=c.get("/api/locations/search",params={"q":name});response.raise_for_status();p=response.json()["matches"][0]
   points.append({"coordinates":p["center"],"label":p["name"][:160]})
  r=c.post("/api/analysis/regions",json={"origins":points,"radius_km":5,"categories":["industrial","industrial_park"]});r.raise_for_status()
  data=r.json();root=Path(__file__).resolve().parents[1]
  (root/"docs/phase4-region-comparison.geojson").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
  print(json.dumps({"status":"passed","regions":[{"name":r["name"],"count":r["mapped_objects"],"density_per_km2":r["objects_per_km2"]} for r in data["rows"]]},ensure_ascii=False))
 return 0
if __name__=="__main__":
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps(safe_error(e)));raise SystemExit(1)
