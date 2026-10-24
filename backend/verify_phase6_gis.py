import json,httpx
from app.core.config import PROJECT_ROOT
from app.services.osm import ssl_context
from app.db.verification import safe_error
def main():
 try:
  a={"ids":["030efbe3-8d74-545d-90e0-15df09508265"]}
  query={"query":{"center":[101.5185278,3.0739429],"radius_km":5,"categories":["industrial"]}}
  cases={
   "buffer":{"operation":"buffer","a":a,"distance_m":5000},
   "intersection":{"operation":"intersection","a":a,"b":a},
   "spatial_join":{"operation":"spatial_join","a":query,"b":a,"predicate":"intersects"},
   "nearest":{"operation":"nearest","a":{"ids":["335bcf23-dccb-5eb4-b14a-737040e1e784"]},"b":{"ids":["91aff2dc-20f3-58c8-ae1a-6b4f6b2462e0"]}},
   "clusters":{"operation":"clusters","a":query,"eps_m":1000,"min_points":3},
   "grid":{"operation":"grid","a":query,"grid_m":1000}}
  output={}
  with httpx.Client(verify=ssl_context(),timeout=60) as c:
   for key,payload in cases.items():
    r=c.post("http://127.0.0.1:8000/api/spatial/analyze",json=payload)
    assert r.status_code==200
    raw=r.json();output[key]={"status":"passed","features":len(raw["features"]),"statistics":raw["statistics"]}
  (PROJECT_ROOT/"docs"/"phase6-gis-integration.json").write_text(json.dumps(output,indent=2),encoding="utf-8");print(json.dumps({k:{"status":v["status"],"features":v["features"]} for k,v in output.items()}));return 0
 except Exception as e:print(json.dumps(safe_error(e)));return 1
if __name__=="__main__":raise SystemExit(main())
