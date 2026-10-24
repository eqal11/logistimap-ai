"""Strict coordinate imports; no paths, URLs, formulas or arbitrary file execution."""
import csv,io,json,math
from app.schemas.optimization import ImportLocations,Stop
from app.optimization.solver import OptimizationError

def import_locations(payload:ImportLocations):
    try:
        rows=[]
        if payload.format=="csv":
            reader=csv.DictReader(io.StringIO(payload.content.lstrip("\ufeff")))
            allowed={"id","name","longitude","latitude","demand","service_s","window_start_s","window_end_s","priority","mandatory","kind","pickup_id","source_id"}
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or set(reader.fieldnames)-allowed:raise ValueError()
            if not {"longitude","latitude","demand"}<=set(reader.fieldnames):raise ValueError()
            for index,row in enumerate(reader):
                if index>=20 or None in row or any(v is None for v in row.values()):raise ValueError()
                if (row.get("mandatory") or "").lower() not in ("","true","false","0","1"):raise ValueError()
                rows.append({"id":row.get("id") or "import-"+str(index+1),"name":row.get("name") or "Imported candidate "+str(index+1),
                    "coordinates":[float(row["longitude"]),float(row["latitude"])],"demand":int(row["demand"]),
                    "service_s":int(row.get("service_s") or 0),"window":[int(row.get("window_start_s") or 0),int(row.get("window_end_s") or 86400)],
                    "priority":int(row.get("priority") or 1),"mandatory":(row.get("mandatory") or "").lower() in ("true","1"),
                    "kind":row.get("kind") or "delivery","pickup_id":row.get("pickup_id") or None,"source_id":row.get("source_id") or None})
        else:
            raw=json.loads(payload.content)
            if not isinstance(raw,dict) or raw.get("type")!="FeatureCollection" or raw.get("crs") or not isinstance(raw.get("features"),list) or not 1<=len(raw["features"])<=20:raise ValueError()
            for i,f in enumerate(raw["features"]):
                if not isinstance(f,dict) or f.get("type")!="Feature" or not isinstance(f.get("geometry"),dict) or f["geometry"].get("type")!="Point":raise ValueError()
                p=f.get("properties") or {}
                if not isinstance(p,dict):raise ValueError()
                rows.append({"id":str(f.get("id") or p.get("id") or "import-"+str(i+1)),"name":p.get("name") or "Imported candidate",
                    "coordinates":f["geometry"]["coordinates"],"demand":p["demand"],"service_s":p.get("service_s",0),
                    "window":p.get("window",[0,86400]),"priority":p.get("priority",1),"mandatory":p.get("mandatory",False),
                    "kind":p.get("kind","delivery"),"pickup_id":p.get("pickup_id"),"source_id":p.get("source_id")})
        stops=[Stop.model_validate(row).model_dump(mode="json") for row in rows]
        if not stops or len({p["id"] for p in stops})!=len(stops):raise ValueError()
        return {"stops":stops,"count":len(stops),"demand_context":payload.demand_context,
            "warnings":["Imported coordinates and shipment demand supplied by user; not verified customers. GeoJSON must use EPSG:4326 2D points."]}
    except (ValueError,KeyError,TypeError,csv.Error,OverflowError):
        raise OptimizationError("Invalid CSV/GeoJSON. Supply 1–20 unique 2D coordinate points, positive integer demand and valid optional windows; CSV headers longitude,latitude,demand are required.") from None
