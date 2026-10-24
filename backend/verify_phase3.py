"""Explicit live routing acceptance. Saves genuine provider routes, never test facilities."""
import json
from datetime import datetime,timezone
import httpx
from shapely.geometry import shape
from sqlalchemy import text
from app.core.config import PROJECT_ROOT
from app.db.session import get_engine
from app.db.verification import safe_error
from app.services.osm import ssl_context
from app.schemas.routing import GEOD

def main():
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"scenarios":[],
            "note":"Car-profile road estimates, not verified truck routes. Geocoder references are not facility gates."}
    output=PROJECT_ROOT/"docs"/"phase3-routing-scenarios.json"
    exports=PROJECT_ROOT/"data"/"exports"/"routes";exports.mkdir(parents=True,exist_ok=True)
    with httpx.Client(base_url="http://127.0.0.1:8000",verify=ssl_context(),timeout=60) as client:
        def get(path,params=None):
            r=client.get(path,params=params)
            if r.status_code!=200: raise RuntimeError("Local routing acceptance GET failed.")
            return r.json()
        refs={}
        for name,query in [
            ("tanjong","Tanjong Malim, Perak, Malaysia"),("rawang","Rawang, Selangor, Malaysia"),
            ("shah","Shah Alam, Selangor, Malaysia"),("port","Port Klang, Selangor, Malaysia"),
            ("klia","KLIA Terminal 1, Malaysia")]:
            found=get("/api/locations/search",{"q":query})["matches"]
            if not found: raise RuntimeError("Required geographic reference unresolved.")
            refs[name]=found[0]
        industrial=get("/api/industrial/features",{"q":"Canpac","categories":"industrial","limit":25})["features"]
        facility=next(f for f in industrial if f["properties"]["name"]=="Canpac Sdn. Bhd.")
        nearest=get("/api/routing/features/"+facility["id"]+"/nearest-warehouse")
        report["geographic_references"]=refs
        report["nearest_warehouse"]={"origin":facility["properties"]["name"],**nearest}
        def place(name):
            return {"coordinates":refs[name]["center"],"label":refs[name]["name"][:160]}
        scenarios=[
            ("tanjong-port","AHTV / Tanjong Malim town → Port Klang town",[place("tanjong"),place("port")]),
            ("rawang-shah","Rawang → Shah Alam",[place("rawang"),place("shah")]),
            ("shah-klia","Shah Alam → KLIA Terminal 1 main building",[place("shah"),place("klia")]),
            ("facility-warehouse","Canpac → nearest mapped warehouse by geographic distance",[{"feature_id":facility["id"]},{"feature_id":nearest["feature_id"]}]),
            ("warehouse-port","Jun Hong Trading warehouse → Port Klang town",[{"feature_id":nearest["feature_id"]},place("port")]),
            ("multi-stop","Tanjong Malim → Rawang → Shah Alam → Port Klang",[place("tanjong"),place("rawang"),place("shah"),place("port")]),
        ]
        ports=get("/api/industrial/features",{"categories":"port","limit":25})["features"]
        if ports: scenarios.append(("warehouse-port-feature","Warehouse → imported OSM port feature",[{"feature_id":nearest["feature_id"]},{"feature_id":ports[0]["id"]}]))
        for key,label,points in scenarios:
            request={"points":points,"profile":"car","alternatives":True,"max_snap_m":1000}
            response=client.post("/api/routing/route",json=request)
            if response.status_code!=200:
                item={"id":key,"label":label,"status":"failed","http_status":response.status_code,
                      "message":response.json().get("error",{}).get("message","API unavailable"),"request":request}
            else:
                result=response.json();route=result["routes"][0]
                line=shape(route["geometry"])
                checks={"valid_linestring":line.geom_type=="LineString" and line.is_valid,
                    "detailed_network_geometry":len(route["geometry"]["coordinates"])>2,
                    "positive_provider_metrics":route["distance_m"]>0 and route["duration_s"]>0,
                    "leg_count":len(route["legs"])==len(points)-1,
                    "geometry_length_consistent":abs(GEOD.geometry_length(line)-route["distance_m"])<max(100,route["distance_m"]*.15),
                    "snap_within_limit":all(w["snap_distance_m"]<=1005 for w in result["waypoints"]),
                    "car_profile_honest":result["profile"]=="car" and not result["heavy_vehicle_verified"]}
                receipt=client.post("/api/routing/saved",json={"calculation_id":result["calculation_id"],"route_index":0})
                checks["saved_to_postgis"]=receipt.status_code==200
                saved_id=receipt.json().get("id")
                exported={"type":"FeatureCollection","features":[
                    {"type":"Feature","id":"route-"+str(r["index"]),"geometry":r["geometry"],"properties":{
                        "distance_m":r["distance_m"],"duration_s":r["duration_s"],"provider":result["provider"],
                        "profile":"car","heavy_vehicle_verified":False,"route_index":r["index"]}} for r in result["routes"]],
                    "meta":{k:v for k,v in result.items() if k!="routes"}}
                path=exports/(key+".geojson");path.write_text(json.dumps(exported,ensure_ascii=False),encoding="utf-8")
                item={"id":key,"label":label,"status":"passed" if all(checks.values()) else "failed",
                    "distance_m":route["distance_m"],"duration_s":route["duration_s"],"vertices":len(route["geometry"]["coordinates"]),
                    "alternatives_returned":len(result["routes"])-1,"routes":[{"distance_m":r["distance_m"],"duration_s":r["duration_s"],"vertices":len(r["geometry"]["coordinates"])} for r in result["routes"]],
                    "waypoints":result["waypoints"],"checks":checks,"saved_id":saved_id,
                    "provider":result["provider"],"retrieved_at":result["retrieved_at"],"cached":result["cached"],
                    "warnings":result["warnings"],"request":request,"export":str(path.relative_to(PROJECT_ROOT))}
            report["scenarios"].append(item)
            output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
            print(json.dumps({k:item.get(k) for k in ("id","status","distance_m","duration_s","vertices","alternatives_returned","message")}),flush=True)
        successful=next((s for s in report["scenarios"] if s["status"]=="passed"),None)
        if successful:
            again=client.post("/api/routing/route",json=successful["request"]).json()
            report["cache_verified"]=again.get("cached") is True
            saved=client.post("/api/routing/saved",json={"calculation_id":again["calculation_id"],"route_index":0}).json()
            report["save_idempotency_verified"]=saved.get("id")==successful["saved_id"]
        with get_engine().connect() as c:
            report["feature_count_unchanged"]=c.execute(text("SELECT count(*) FROM spatial_features")).scalar_one()==5234
            report["synthetic_features"]=c.execute(text("SELECT count(*) FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id WHERE d.synthetic")).scalar_one()
            ids=[s["saved_id"] for s in report["scenarios"] if s.get("saved_id")]
            rows=c.execute(text("SELECT id,ST_IsValid(geometry),ST_SRID(geometry),GeometryType(geometry),provenance->'selected_route'->>'distance_m' FROM routing_references WHERE id=ANY(:ids)"),{"ids":ids}).all()
            report["saved_routes_verified"]=len(rows)==len(ids) and all(r[1] and r[2]==4326 and r[3]=="LINESTRING" and float(r[4])>0 for r in rows)
        report["provider_info"]=get("/api/routing/provider")
        (PROJECT_ROOT/"docs"/"openapi.json").write_text(json.dumps(get("/openapi.json"),indent=2),encoding="utf-8")
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return 0 if all(s["status"]=="passed" for s in report["scenarios"]) and report["feature_count_unchanged"] and report.get("saved_routes_verified") else 1

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps(safe_error(exc)));raise SystemExit(1)
