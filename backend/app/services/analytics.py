import hashlib,json,time
from datetime import datetime,timezone
from uuid import uuid5,NAMESPACE_URL
from threading import Lock
from contextlib import nullcontext
from pathlib import Path
from geoalchemy2.shape import from_shape
from shapely.geometry import shape,GeometryCollection
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.core.config import get_settings
from app.db.session import get_engine
from app.models.entities import SpatialFeature,Dataset,AnalysisJob,AnalysisResult,RoutingReference
from app.schemas.spatial import SearchParams
from app.services.features import postgis_search
from app.gis.analytics import execute,AnalysisError

lock=Lock()
def cache_path(key):
    import re
    if not re.fullmatch("[a-f0-9]{64}",key):raise AnalysisError("Invalid analysis calculation ID")
    return get_settings().provider_cache_dir/("analysis-"+key+".json")
def load_result(key):
    p=cache_path(key)
    if not p.exists() or time.time()-p.stat().st_mtime>86400:raise AnalysisError("Analysis cache expired; run it again")
    return json.loads(p.read_text(encoding="utf-8"))
def saved_analysis(id,db):
    row=db.get(AnalysisResult,id)
    if row is None or row.summary.get("kind")!="phase4" or row.summary.get("archived_at"):raise AnalysisError("Saved analysis not found")
    return {**row.summary["result"],"saved_id":row.id}
def prune_cache():
    folder=get_settings().provider_cache_dir
    for stale in sorted(folder.glob("analysis-*.json"),key=lambda p:p.stat().st_mtime)[:-64]:stale.unlink(missing_ok=True)
def load_layer(spec,db):
    if spec is None:return [],{"source":"none","count":0}
    if spec.saved_id:
        result=saved_analysis(str(spec.saved_id),db);features=result["features"]
        if len(features)>2000:raise AnalysisError("Saved input exceeds 2,000 objects; narrow the analysis")
        return features,{"source":"saved analysis","id":str(spec.saved_id),"count":len(features)}
    if spec.features:
        features=[{"type":"Feature","id":f.id,"geometry":f.geometry.model_dump(),"properties":{"name":f.name,"source":"User-provided geometry; unverified","categories":[]}} for f in spec.features]
        return features,{"source":"user geometry","count":len(features)}
    if spec.ids:
        rows=db.execute(select(SpatialFeature,func.ST_AsGeoJSON(SpatialFeature.geometry)).where(SpatialFeature.id.in_([str(i) for i in spec.ids]))).all()
        if len(rows)!=len(set(spec.ids)):raise AnalysisError("One or more selected features are missing")
        if any(r.dataset.synthetic for r,g in rows):raise AnalysisError("Synthetic features cannot be used as live industrial analysis")
        features=[{"type":"Feature","id":r.id,"geometry":json.loads(g),"properties":{"name":r.name,"source":r.dataset.source,"source_id":r.source_id,"license":r.dataset.license,"dataset_id":r.dataset_id,"imported_at":r.attributes.get("last_imported_at",r.created_at.isoformat()),"categories":[c.id for c in r.categories],"boundary_status":r.boundary_status}} for r,g in rows]
        return features,{"source":"PostGIS selected IDs","ids":[str(i) for i in spec.ids],"count":len(features)}
    query=spec.query.model_copy(update={"limit":1000,"offset":0})
    features,total,counts=postgis_search(query,db)
    if total>2000:raise AnalysisError("Input query exceeds 2,000 objects. Narrow bbox/radius/categories; no partial analysis was performed")
    if total>1000:features+=postgis_search(query.model_copy(update={"offset":1000}),db)[0]
    features=[f.model_dump(mode="json") for f in features]
    if any(f["properties"]["synthetic"] for f in features):raise AnalysisError("Synthetic input rejected")
    return features,{"source":"PostGIS bounded query","query":spec.query.model_dump(mode="json"),"count":total,"category_counts":counts}
def run_analysis(payload,session=None):
    if not lock.acquire(blocking=False):raise AnalysisError("Another spatial analysis is processing; retry after it finishes")
    try:
        with (nullcontext(session) if session else Session(get_engine())) as db:
            db.execute(text("SET LOCAL statement_timeout='20000'"))
            a,ma=load_layer(payload.a,db);b,mb=load_layer(payload.b,db)
        started=time.monotonic()
        out,rows,stats,warnings,crs=execute(payload,a,b)
        response={"type":"FeatureCollection","title":payload.title,"operation":payload.operation,"features":out,
            "statistics":stats,"rows":rows,"inputs":{"a":ma,"b":mb},"parameters":payload.model_dump(mode="json"),
            "status":"completed","executed_at":datetime.now(timezone.utc).isoformat(),"processing_ms":round((time.monotonic()-started)*1000),
            "input_features":[{**f,"id":"input-"+str(i),"properties":{**f["properties"],"input_role":"A" if i<len(a) else "B"}} for i,f in enumerate(a+b)],
            "crs":"EPSG:4326","calculation_crs":crs,"attribution":"© OpenStreetMap contributors · ODbL 1.0; user geometry retains its source",
            "warnings":warnings}
        raw=json.dumps(response,ensure_ascii=False)
        if len(raw.encode())>8_000_000:raise AnalysisError("Result exceeds 8 MB; narrow the inputs")
        response=json.loads(raw)
        key=hashlib.sha256(raw.encode()).hexdigest();response["calculation_id"]=key
        path=cache_path(key);path.parent.mkdir(exist_ok=True,parents=True)
        path.write_text(json.dumps(response,ensure_ascii=False),encoding="utf-8")
        prune_cache()
        return response
    finally:lock.release()
def save_analysis(key,session=None):
    result=load_result(key);id=str(uuid5(NAMESPACE_URL,"phase4:"+key))
    with (nullcontext(session) if session else Session(get_engine())) as db:
        db.execute(insert(AnalysisJob).values(id=id,operation="phase4:"+result["operation"],status="completed",parameters=result["parameters"]).on_conflict_do_nothing(index_elements=[AnalysisJob.id]))
        # Preserve the complete FeatureCollection with provenance, plus a spatially indexed collect.
        geom=GeometryCollection([shape(f["geometry"]) for f in result["features"]])
        db.execute(insert(AnalysisResult).values(id=id,job_id=id,geometry=from_shape(geom,srid=4326) if not geom.is_empty else None,
            summary={"kind":"phase4","title":result["title"],"result":result}).on_conflict_do_update(index_elements=[AnalysisResult.id],set_={"summary":{"kind":"phase4","title":result["title"],"result":result}}))
        if session is None:db.commit()
    return {"id":id,"status":"saved"}
def history(kind,limit=25,offset=0,session=None):
    model=AnalysisResult if kind=="analyses" else RoutingReference
    column=model.summary if kind=="analyses" else model.provenance
    with (nullcontext(session) if session else Session(get_engine())) as db:
        # Extract only history metadata in SQL: never deserialize saved geometry JSON here.
        if kind=="analyses":
            q=select(model.id,model.created_at,column["title"].astext.label("title"),
                column["result"]["operation"].astext.label("operation"),
                func.jsonb_array_length(column["result"]["features"]).label("count")).where(column["kind"].astext=="phase4")
        else:
            q=select(model.id,model.created_at,column["provider"].astext.label("provider"),
                column["selected_route"]["distance_m"].astext.label("distance_m"),
                column["selected_route"]["duration_s"].astext.label("duration_s"),
                column["waypoints"].label("waypoints"))
        q=q.where(column["archived_at"].astext.is_(None))
        total=db.scalar(select(func.count()).select_from(q.subquery()))
        data=db.execute(q.order_by(model.created_at.desc(),model.id).limit(limit).offset(offset)).mappings().all()
        items=[]
        for row in data:
            item={"id":row["id"],"created_at":row["created_at"].isoformat()}
            if kind=="analyses":item.update({k:row[k] for k in ("title","operation","count")})
            else:item.update({"title":" → ".join(w.get("label","Reference") for w in row["waypoints"] or []),
                "provider":row["provider"],"profile":"car",
                "distance_m":float(row["distance_m"]) if row["distance_m"] is not None else None,
                "duration_s":float(row["duration_s"]) if row["duration_s"] is not None else None})
            items.append(item)
        return {"items":items,"total":total,"limit":limit,"offset":offset}
def saved_route(id,db):
    row=db.get(RoutingReference,id)
    if row is None or row.provenance.get("archived_at"):raise AnalysisError("Saved route not found")
    geometry=db.scalar(select(func.ST_AsGeoJSON(RoutingReference.geometry)).where(RoutingReference.id==id))
    p=row.provenance;r=p.get("selected_route",{})
    return {"type":"FeatureCollection","title":" → ".join(w.get("label","Reference") for w in p.get("waypoints",[])),
        "operation":"saved_route","features":[{"type":"Feature","id":id,"geometry":json.loads(geometry),"properties":{**r,"name":"Saved road route","provider":row.provider,"profile":row.profile,"heavy_vehicle_verified":False}}],
        "statistics":{"distance_m":r.get("distance_m"),"duration_s":r.get("duration_s")},"rows":[{"id":id,**{k:v for k,v in r.items() if k!="legs"}}],
        "inputs":{"waypoints":p.get("waypoints",[])},"parameters":{},"status":"completed","executed_at":p.get("retrieved_at"),"crs":"EPSG:4326",
        "warnings":p.get("warnings",[]),"attribution":p.get("attribution"),"saved_id":id}
def get_saved(kind,id,session=None):
    with (nullcontext(session) if session else Session(get_engine())) as db:
        return saved_analysis(id,db) if kind=="analyses" else saved_route(id,db)
def archive(kind,id,session=None):
    model=AnalysisResult if kind=="analyses" else RoutingReference;attr="summary" if kind=="analyses" else "provenance"
    with (nullcontext(session) if session else Session(get_engine())) as db:
        row=db.get(model,id)
        if row is None or (kind=="analyses" and row.summary.get("kind")!="phase4"):raise AnalysisError("Saved result not found")
        value=dict(getattr(row,attr));value["archived_at"]=datetime.now(timezone.utc).isoformat();setattr(row,attr,value)
        if session is None:db.commit()
        return {"id":id,"status":"archived","message":"Hidden from active history; original geometry and provenance retained."}

def restore(kind,id,session=None):
    model=AnalysisResult if kind=="analyses" else RoutingReference;attr="summary" if kind=="analyses" else "provenance"
    with (nullcontext(session) if session else Session(get_engine())) as db:
        row=db.get(model,id)
        if row is None or (kind=="analyses" and row.summary.get("kind")!="phase4"):raise AnalysisError("Saved result not found")
        value=dict(getattr(row,attr));value.pop("archived_at",None);setattr(row,attr,value)
        if session is None:db.commit()
        return {"id":id,"status":"restored"}
