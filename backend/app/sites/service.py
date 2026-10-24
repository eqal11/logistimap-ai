"""Bounded PostGIS criterion extraction; road metrics reuse the existing provider abstraction."""
import json,hashlib,time
from datetime import datetime,timezone
from uuid import uuid4
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from shapely.geometry import shape
from shapely import get_num_coordinates
from app.db.session import get_engine
from app.core.config import get_settings
from app.routing.service import feature_anchor
from app.routing.providers import RoutingError
from app.optimization.matrix import road_matrix
from app.sites.mcda import SiteError,evaluate_mcda
from app.sites.catalog import CATALOG,WARNINGS
SQL="""
WITH input AS (
 SELECT x.id,x.feature_id,ST_SetSRID(ST_GeomFromGeoJSON(x.geometry::text),4326) g
 FROM jsonb_to_recordset(CAST(:items AS jsonb)) AS x(id text,feature_id text,geometry jsonb)
), i AS (SELECT *,ST_PointOnSurface(g) anchor FROM input)
SELECT i.id,ST_AsGeoJSON(i.anchor) anchor,
 CASE WHEN ST_Dimension(i.g)=2 THEN ST_Area(i.g::geography) ELSE NULL END area,
 ST_Area(ST_Buffer(i.anchor::geography,:radius)) / 1000000.0 catchment_area_km2,
 (SELECT COUNT(*) FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id
  WHERE NOT d.synthetic AND f.id IS DISTINCT FROM i.feature_id
  AND f.geometry && ST_Expand(i.anchor,0.3)
  AND EXISTS(SELECT 1 FROM feature_categories c WHERE c.feature_id=f.id AND c.category_id='industrial')
  AND ST_DWithin(f.geometry::geography,i.anchor::geography,:radius)) industrial_count,
 (SELECT CASE WHEN ST_Dimension(i.g)=0 THEN CASE WHEN ST_Intersects(i.g,ST_Union(f.geometry)) THEN 100.0 ELSE 0.0 END
  ELSE 100.0*ST_Area(ST_Intersection(i.g,ST_Union(f.geometry))::geography)/NULLIF(ST_Area(i.g::geography),0) END
  FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id WHERE NOT d.synthetic
  AND f.geometry && i.g AND ST_Intersects(f.geometry,i.g)
  AND EXISTS(SELECT 1 FROM feature_categories c WHERE c.feature_id=f.id AND c.category_id='industrial_park')) overlap,
 (SELECT jsonb_object_agg(cat.id,(
  SELECT jsonb_build_object('value',ST_Distance(f.geometry::geography,i.g::geography),'feature_id',f.id,'source_id',f.source_id,'name',f.name)
  FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id
  WHERE NOT d.synthetic AND f.id IS DISTINCT FROM i.feature_id AND f.geometry && ST_Expand(i.g,1.1)
  AND EXISTS(SELECT 1 FROM feature_categories c WHERE c.feature_id=f.id AND c.category_id=cat.id)
  AND ST_DWithin(f.geometry::geography,i.g::geography,100000)
  ORDER BY ST_Distance(f.geometry::geography,i.g::geography),f.id LIMIT 1))
 FROM (VALUES ('road'),('warehouse'),('logistics_hub')) cat(id)) nearest
FROM i ORDER BY i.id
"""
def resolve_candidates(s,db):
 refs=[str(c.feature_id) for c in s.candidates if c.feature_id];mapped={}
 if refs:
  rows=db.execute(text("""SELECT f.id,f.name,f.source_id,ST_AsGeoJSON(f.geometry) geometry,d.source,d.license,
   ARRAY(SELECT c.category_id FROM feature_categories c WHERE c.feature_id=f.id) categories
   FROM spatial_features f JOIN datasets d ON d.id=f.dataset_id WHERE f.id=ANY(:ids) AND NOT d.synthetic"""),{"ids":refs}).mappings()
  mapped={r["id"]:r for r in rows}
 out=[]
 for c in s.candidates:
  if c.feature_id:
   r=mapped.get(str(c.feature_id))
   if not r or not set(r["categories"])&{"industrial","industrial_park","warehouse"}:raise SiteError("Choose a real mapped warehouse or industrial candidate")
   geometry=json.loads(r["geometry"])
   if geometry["type"] not in ("Point","Polygon","MultiPolygon"):raise SiteError("Mapped candidate is not a point/polygon")
   source={"source":r["source"],"source_id":r["source_id"],"license":r["license"],"categories":r["categories"],"kind":"existing_warehouse" if "warehouse" in r["categories"] else "mapped_industrial"}
  else:
   geometry=c.geometry.model_dump();source={"source":"User supplied geometry; not independently verified","source_id":None,"kind":c.kind}
  g=shape(geometry)
  if not g.is_valid or g.is_empty or get_num_coordinates(g)>10000:raise SiteError("Invalid or overly complex candidate geometry")
  if not (99<=g.bounds[0]<=g.bounds[2]<=120 and 0<=g.bounds[1]<=g.bounds[3]<=8):raise SiteError("Candidate outside Malaysian study region")
  out.append({"id":c.id,"name":c.name,"feature_id":str(c.feature_id) if c.feature_id else None,"geometry":geometry,"provenance":source})
 if sum(get_num_coordinates(shape(c["geometry"])) for c in out)>25000:raise SiteError("Combined candidates exceed 25,000 vertices")
 return out
def prepare(s,db=None):
 own=db is None
 if own:
  with Session(get_engine()) as tx:return prepare(s,tx)
 db.execute(text("SET LOCAL statement_timeout='20000'"))
 candidates=resolve_candidates(s,db)
 raw=db.execute(text(SQL),{"items":json.dumps(candidates),"radius":s.radius_m}).mappings().all()
 by_id={r["id"]:r for r in raw};values={}
 for c in candidates:
  r=by_id[c["id"]];c["anchor"]=json.loads(r["anchor"])["coordinates"];values[c["id"]]={}
  for criterion in s.criteria:
   key=criterion.id;v=None;status="unavailable";source="Imported OSM; dataset coverage only";details={}
   if criterion.source=="user":
    supplied=next(p for p in s.candidates if p.id==c["id"]).values.get(key)
    if supplied:v=supplied.value;details={"note":supplied.note};status="user_supplied"
    source="User supplied, unverified"
   elif criterion.source=="gis":
    if key in ("road_distance_m","warehouse_distance_m","hub_distance_m"):
     category={"road_distance_m":"road","warehouse_distance_m":"warehouse","hub_distance_m":"logistics_hub"}[key]
     details=(r["nearest"] or {}).get(category) or {}
     v=details.get("value")
    elif key=="parcel_area_m2":v=r["area"]
    elif key=="industrial_count":v=r["industrial_count"];details={"radius_m":s.radius_m}
    elif key=="industrial_density_km2":v=r["industrial_count"]/r["catchment_area_km2"];details={"radius_m":s.radius_m,"catchment_area_km2":r["catchment_area_km2"]}
    elif key=="industrial_overlap_pct":v=min(100.,max(0.,r["overlap"] or 0.))
    if v is not None:status="calculated"
   values[c["id"]][key]={"value":float(v) if v is not None else None,"status":status,"source":source,"unit":CATALOG[key][1],"method":CATALOG[key][4],"details":details}
 targets={};routing=None;network=[k for k in s.criteria if k.source=="network"]
 if network:
  try:
   if not get_settings().routing_enabled:raise RoutingError("Road provider disabled",503)
   for key in sorted({k.id.split("_")[0] for k in network}):
    ref=s.targets[key]
    targets[key]=feature_anchor(str(ref.feature_id),db) if ref.feature_id else {"coordinates":list(ref.coordinates),"label":ref.label or key+" user reference","source":"User coordinate / named reference, entrance unverified"}
   points=[{"coordinates":c["anchor"],"label":c["name"]} for c in candidates]+list(targets.values())
   routing=road_matrix(points,s.max_snap_m)
   for cindex,c in enumerate(candidates):
    for k in network:
     dest=len(candidates)+list(targets).index(k.id.split("_")[0]);value=routing["durations"][cindex][dest]
     values[c["id"]][k.id]={"value":value,"status":"calculated" if value is not None else "unreachable","source":routing["provider"],"unit":"s","method":CATALOG[k.id][4],
      "details":{"matrix_id":routing["id"],"distance_m":routing["distances"][cindex][dest],"target":targets[k.id.split("_")[0]],"retrieved_at":routing["retrieved_at"],"profile":"car","heavy_vehicle_verified":False}}
  except RoutingError as exc:
   routing={"status":"unavailable","message":str(exc)}
   for c in candidates:
    for k in network:values[c["id"]][k.id].update({"status":"provider_unavailable","details":{"message":str(exc)}})
 return {"candidates":candidates,"values":values,"targets":targets,"routing":routing,"warnings":WARNINGS}
def cache_path(key):
 return get_settings().provider_cache_dir/("site-evaluation-"+key+".json")
def evaluate(s,db=None):
 data=prepare(s,db);scored=evaluate_mcda(s,data["values"])
 colors=["#bd5b43","#bf873a","#a5a548","#4a9990","#087f80"]
 scores={r["candidate_id"]:r for r in scored["rankings"]}
 features=[]
 for c in data["candidates"]:
  row=scores.get(c["id"])
  features.append({"type":"Feature","id":c["id"],"geometry":c["geometry"],"properties":{
   "candidate_id":c["id"],"name":c["name"],"score":row["score"] if row else None,"rank":row["rank"] if row else None,
   "color":colors[min(4,int(row["score"]/20))] if row else "#89949b","anchor":c["anchor"],"provenance":c["provenance"],
   "feature_id":c["feature_id"],"criteria":data["values"][c["id"]],"contributions":row["contributions"] if row else {},
   "role":"candidate suitability, not verified development land"}})
 result={"type":"FeatureCollection","title":s.name,"operation":"site_suitability","features":features,"scenario":s.model_dump(mode="json"),
   **data,**scored,"warnings":WARNINGS+scored["warnings"],"crs":"EPSG:4326","executed_at":datetime.now(timezone.utc).isoformat(),
   "status":"completed","attribution":"© OpenStreetMap contributors (ODbL); user-supplied data retains its stated provenance.","profile":"car","heavy_vehicle_verified":False}
 key=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();result["calculation_id"]=key
 body=json.dumps(result)
 if len(body.encode())>4_000_000:raise SiteError("Result exceeds 4 MB; simplify candidates")
 path=cache_path(key);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body,encoding="utf-8")
 for old in sorted(path.parent.glob("site-evaluation-*.json"),key=lambda p:p.stat().st_mtime)[:-32]:old.unlink(missing_ok=True)
 return result
