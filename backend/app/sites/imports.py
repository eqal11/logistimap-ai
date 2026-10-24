import json,csv,io
from app.schemas.sites import SiteCandidate
from app.sites.mcda import SiteError
def import_candidates(payload):
 try:
  rows=[]
  if payload.format=="geojson":
   raw=json.loads(payload.content)
   if not isinstance(raw,dict) or raw.get("type")!="FeatureCollection" or raw.get("crs") or not isinstance(raw.get("features"),list) or not 1<=len(raw["features"])<=12:raise ValueError()
   for i,f in enumerate(raw["features"]):
    if not isinstance(f,dict) or f.get("type")!="Feature":raise ValueError()
    prop=f.get("properties") or {}
    if not isinstance(prop,dict):raise ValueError()
    rows.append(SiteCandidate(id=str(f.get("id") or prop.get("id") or "import-"+str(i+1)),name=prop.get("name") or "Imported candidate "+str(i+1),geometry=f["geometry"],kind=prop.get("kind","hypothetical_site"),values=prop.get("values",{})))
  else:
   reader=csv.DictReader(io.StringIO(payload.content.lstrip("\ufeff")))
   allowed={"id","name","longitude","latitude","kind"}
   if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or not {"longitude","latitude"}<=set(reader.fieldnames) or set(reader.fieldnames)-allowed:raise ValueError()
   for i,r in enumerate(reader):
    if i>=12 or None in r or any(v is None for v in r.values()):raise ValueError()
    rows.append(SiteCandidate(id=r.get("id") or "import-"+str(i+1),name=r.get("name") or "Imported candidate "+str(i+1),geometry={"type":"Point","coordinates":[float(r["longitude"]),float(r["latitude"])]},kind=r.get("kind") or "hypothetical_site"))
  if not rows or len({r.id for r in rows})!=len(rows):raise ValueError()
  return {"candidates":[r.model_dump(mode="json") for r in rows],"warnings":["User imported candidates; geometry and reported facility/development status are unverified. No land availability implied."]}
 except (ValueError,TypeError,KeyError,csv.Error,RecursionError,OverflowError):
  raise SiteError("Invalid candidate import. Supply 1–12 unique Malaysian EPSG:4326 points/polygons; CSV needs longitude,latitude. No paths, URLs or legacy CRS.") from None
