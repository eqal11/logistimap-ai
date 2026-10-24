"""Prepare non-secret public OSM input CSV and API snapshot for acceptance."""
import csv,json
from app.core.config import PROJECT_ROOT
from app.main import app
from app.optimization.repository import get_scenario
data=json.loads((PROJECT_ROOT/"docs/phase5-live-results.json").read_text(encoding="utf-8"))
scenario=get_scenario(data["A"]["scenario_id"])["scenario"]
with (PROJECT_ROOT/"docs/phase5-browser-input.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["id","name","longitude","latitude","demand","service_s","source_id"])
    w.writeheader()
    for i,p in enumerate(scenario["stops"][:2]):
        w.writerow({"id":"browser-stop-"+str(i+1),"name":p["name"],"longitude":p["coordinates"][0],"latitude":p["coordinates"][1],"demand":2,"service_s":120,"source_id":p["source_id"]})
(PROJECT_ROOT/"docs/openapi.json").write_text(json.dumps(app.openapi(),indent=2),encoding="utf-8")
print("Prepared public OSM candidate input (2 rows, hypothetical demand) and OpenAPI contract.")
