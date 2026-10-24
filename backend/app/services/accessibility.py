import hashlib,json,math,time
from datetime import datetime,timezone
from sqlalchemy import select,func,cast,text
from sqlalchemy.orm import Session
from geoalchemy2 import Geography
from shapely.geometry import Point,mapping
from app.core.config import get_settings
from app.db.session import get_engine
from app.routing.service import feature_anchor
from app.routing.providers import get_provider,provider_info,RoutingError,LIMITATIONS,finite_number
from app.gis.analytics import GEOD,project_layers
from app.models.entities import SpatialFeature,Dataset,Category
from app.services.features import postgis_search
from app.schemas.spatial import SearchParams
from app.schemas.routing import coordinate
from app.services.analytics import prune_cache

def resolve(points,db):
    return [feature_anchor(str(p.feature_id),db) if p.feature_id else {"coordinates":list(p.coordinates),"label":p.label or "Coordinate reference","anchor_method":"user_reference"} for p in points]
def matrix(payload):
    provider=get_provider()
    with Session(get_engine()) as db:
        origins=resolve(payload.origins,db);destinations=resolve(payload.destinations,db)
    points=origins+destinations
    if any(GEOD.inv(*a["coordinates"],*b["coordinates"])[2]>3_000_000 for a in points for b in points):raise RoutingError("Matrix extent exceeds 3,000 km",422)
    key=hashlib.sha256(json.dumps({"schema":2,"profile":get_settings().routing_osrm_profile,"label":get_settings().routing_provider_label,"base":get_settings().routing_base_url,"points":points,"snap":payload.max_snap_m,"score":payload.score_reference_minutes},sort_keys=True).encode()).hexdigest()
    path=get_settings().provider_cache_dir/("matrix-"+key+".json")
    if path.exists() and time.time()-path.stat().st_mtime<86400:
        cached=json.loads(path.read_text(encoding="utf-8"))
        (path.parent/("analysis-"+key+".json")).write_text(json.dumps(cached),encoding="utf-8");prune_cache()
        return {**cached,"cached":True}
    raw=provider.table(points,list(range(len(origins))),list(range(len(origins),len(points))),payload.max_snap_m)
    if not isinstance(raw,dict) or raw.get("code")!="Ok":raise RoutingError("Road matrix provider could not calculate these references; no geodesic fallback.",422)
    try:
        if raw.get("fallback_speed_cells"):raise ValueError()
        durations=raw["durations"];distances=raw["distances"]
        if len(durations)!=len(origins) or len(distances)!=len(origins):raise ValueError()
        for name,expected in (("sources",origins),("destinations",destinations)):
            if len(raw[name])!=len(expected):raise ValueError()
            for wp,p in zip(raw[name],expected):
                snap=coordinate(wp["location"])
                if finite_number(wp["distance"])>payload.max_snap_m+5:raise ValueError()
                if len(snap)!=2 or GEOD.inv(*p["coordinates"],*snap)[2]>payload.max_snap_m+10:raise ValueError()
        rows=[]
        for i,origin in enumerate(origins):
            if len(durations[i])!=len(destinations) or len(distances[i])!=len(destinations):raise ValueError()
            for j,destination in enumerate(destinations):
                d,t=distances[i][j],durations[i][j]
                if (d is None)!=(t is None):raise ValueError()
                if d is not None:d,t=finite_number(d),finite_number(t)
                rows.append({"origin_index":i,"destination_index":j,"origin":origin["label"],"destination":destination["label"],
                    "distance_m":d,"duration_s":t,"reachable":d is not None,
                    "accessibility_score":round(100/(1+t/(payload.score_reference_minutes*60)),2) if t is not None else 0})
    except (KeyError,TypeError,ValueError,IndexError):raise RoutingError("Invalid road matrix dimensions, metrics or snap metadata.",502) from None
    nearest=[]
    for i in range(len(origins)):
        eligible=[r for r in rows if r["origin_index"]==i and r["reachable"]]
        if eligible:nearest.append(min(eligible,key=lambda r:(r["duration_s"],r["distance_m"],r["destination_index"])))
    features=[{"type":"Feature","id":str(i),"geometry":{"type":"Point","coordinates":p["coordinates"]},"properties":{"name":p["label"],"role":"origin" if i<len(origins) else "destination","source":"Input reference; entrance unverified"}} for i,p in enumerate(points)]
    result={"type":"FeatureCollection","title":"Road-network accessibility","operation":"matrix","features":features,"rows":rows,
        "statistics":{"pairs":len(rows),"reachable_pairs":sum(r["reachable"] for r in rows),"nearest_by_time":nearest},
        "inputs":{"origins":origins,"destinations":destinations,"snapped_sources":raw["sources"],"snapped_destinations":raw["destinations"]},
        "parameters":payload.model_dump(mode="json"),"crs":"EPSG:4326","status":"completed","executed_at":datetime.now(timezone.utc).isoformat(),
        "provider":provider_info()["provider"],"profile":"car","heavy_vehicle_verified":False,"cached":False,
        "attribution":provider_info()["attribution"],"warnings":LIMITATIONS+[
            "OSRM Table returns road metrics without route geometry. Only reference points are displayed; use the route planner to inspect a pair.",
            "Nearest means fastest among the supplied candidates, not all facilities nationally. Matrix distance follows the fastest path, not necessarily the shortest-distance path.",
            f"Score = 100 / (1 + travel minutes / {payload.score_reference_minutes:g}); heuristic travel-time score, not validated investment suitability. Unreachable = 0."]}
    # Store matrices in the same validated server-only analysis cache for save/reload.
    result["calculation_id"]=key
    path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(result),encoding="utf-8")
    (path.parent/("analysis-"+key+".json")).write_text(json.dumps(result),encoding="utf-8")
    for stale in sorted(path.parent.glob("matrix-*.json"),key=lambda p:p.stat().st_mtime)[:-64]:stale.unlink(missing_ok=True)
    prune_cache()
    return result

def compare_regions(payload):
    rows=[];features=[]
    with Session(get_engine()) as db:
        db.execute(text("SET LOCAL statement_timeout='20000'"))
        refs=resolve(payload.origins,db)
        for i,p in enumerate(refs):
            center=p["coordinates"]
            _,total,counts=postgis_search(SearchParams(center=center,radius_km=payload.radius_km,categories=payload.categories,limit=1),db)
            _,road_count,_=postgis_search(SearchParams(center=center,radius_km=payload.radius_km,categories=["road"],limit=1),db)
            dummy={"geometry":mapping(Point(center))};fwd,back,crs=project_layers([dummy],[])
            circle=back(fwd(Point(center)).buffer(payload.radius_km*1000,quad_segs=64))
            area=abs(GEOD.geometry_area_perimeter(circle)[0])/1e6
            row={"name":p["label"],"mapped_objects":total,"area_km2":area,"objects_per_km2":total/area,"mapped_road_segments":road_count,"category_counts":counts}
            origin=func.ST_SetSRID(func.ST_MakePoint(*center),4326)
            for cat in ("warehouse","port","airport","logistics_hub"):
                distance=func.ST_Distance(cast(SpatialFeature.geometry,Geography),cast(origin,Geography))
                nearest=db.execute(select(SpatialFeature.name,distance).join(Dataset,Dataset.id==SpatialFeature.dataset_id)
                    .where(Dataset.synthetic.is_(False),SpatialFeature.categories.any(Category.id==cat)).order_by(distance,SpatialFeature.id).limit(1)).first()
                row[cat+"_nearest_m"]=nearest[1] if nearest else None;row[cat+"_nearest_name"]=nearest[0] if nearest else None
            rows.append(row);features.append({"type":"Feature","id":str(i),"geometry":mapping(circle),"properties":{**row,"source":"Calculated query circle; not industrial boundary"}})
    result={"type":"FeatureCollection","title":"Industrial area concentration comparison","operation":"region_comparison","features":features,"rows":rows,
        "statistics":{"regions":len(rows)},"inputs":{"origins":refs},"parameters":payload.model_dump(mode="json"),"crs":"EPSG:4326","status":"completed",
        "executed_at":datetime.now(timezone.utc).isoformat(),"attribution":"© OpenStreetMap contributors · ODbL 1.0",
        "warnings":["Geography ST_DWithin selects any footprint intersecting the radius. Counts are mapped objects, not a facility census or economic output.",
        "Road segment count describes source mapping; it does not verify graph connectivity or facility access.",
        "Nearest proximity is PostGIS geography distance to mapped footprints, not road travel.",
        "Reference circles are study areas, not network isochrones, industrial park boundaries or verified gates.",
        "Coverage differs by area. No records returned is not proof of absence. Use Network Accessibility for explicit road distance/time comparisons."]}
    key=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();result["calculation_id"]=key
    path=get_settings().provider_cache_dir/("analysis-"+key+".json");path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(result),encoding="utf-8")
    prune_cache()
    return result
