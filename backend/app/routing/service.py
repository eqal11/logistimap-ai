"""Resolve real feature anchors, cache validated provider results, save selected routes."""
import hashlib
import json
import re
import time
from contextlib import nullcontext
from datetime import datetime,timezone
from uuid import NAMESPACE_URL,uuid5
from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy import cast,func,select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.entities import Category,Dataset,RoutingReference,SpatialFeature
from app.routing.providers import LIMITATIONS,RoutingError,get_provider,provider_info
from app.schemas.routing import GEOD,RouteRequest,SaveRouteRequest

def feature_anchor(feature_id,session=None):
    if get_settings().data_mode!="postgis":
        raise RoutingError("Imported GIS endpoints require PostGIS mode; fixture features cannot be presented as real facilities.",409)
    with (nullcontext(session) if session is not None else Session(get_engine())) as db:
        row=db.execute(select(SpatialFeature,func.ST_AsGeoJSON(func.ST_PointOnSurface(SpatialFeature.geometry)),
            func.GeometryType(SpatialFeature.geometry)).where(SpatialFeature.id==feature_id)).first()
        if row is None or row[0].dataset.synthetic:
            raise RoutingError("Real imported feature not found.",404)
        feature,geometry,kind=row
        point=json.loads(geometry)["coordinates"]
        return {"feature_id":feature.id,"label":feature.name[:160],"coordinates":point,
            "source_id":feature.source_id,"source":feature.dataset.source,"categories":[c.id for c in feature.categories],
            "anchor_method":"source_point" if kind=="POINT" else "ST_PointOnSurface representative point",
            "warning":"Representative map reference, not a verified driveway, gate or legal vehicle access."}

def nearest_warehouse(feature_id,session=None):
    with (nullcontext(session) if session is not None else Session(get_engine())) as db:
        origin=feature_anchor(feature_id,db)
        source_geometry=select(SpatialFeature.geometry).where(SpatialFeature.id==feature_id).scalar_subquery()
        distance=func.ST_Distance(cast(SpatialFeature.geometry,Geography),cast(source_geometry,Geography))
        row=db.execute(select(SpatialFeature.id,distance).join(Dataset,Dataset.id==SpatialFeature.dataset_id)
            .where(SpatialFeature.id!=feature_id,Dataset.synthetic.is_(False),
                   SpatialFeature.categories.any(Category.id=="warehouse"))
            .order_by(distance,SpatialFeature.id).limit(1)).first()
        if row is None: raise RoutingError("No imported warehouse is available in this dataset.",404)
        return {**feature_anchor(row[0],db),"geographic_distance_m":row[1],
            "method":"Nearest different mapped warehouse by geodesic geometry distance, not road distance.",
            "warning":"Overlapping mapped footprints can have zero geographic distance. This does not identify the closest warehouse by driving distance."}

def resolve_points(request,session=None):
    if session is None and any(p.feature_id for p in request.points):
        with Session(get_engine()) as db:
            return resolve_points(request,db)
    points=[]
    for index,point in enumerate(request.points):
        if point.feature_id:
            resolved=feature_anchor(point.feature_id,session)
        else:
            resolved={"coordinates":list(point.coordinates),"label":point.label or ("Origin" if index==0 else "Destination" if index==len(request.points)-1 else f"Stop {index}"),
                      "source":"User-selected coordinate / place reference","anchor_method":"user_reference"}
        if point.label: resolved["label"]=point.label
        points.append(resolved)
    total=0
    for a,b in zip(points,points[1:]):
        distance=GEOD.inv(*a["coordinates"],*b["coordinates"])[2]
        if distance<1: raise RoutingError("Consecutive stops must be at least 1 meter apart.",422)
        total+=distance
    if total>3_000_000: raise RoutingError("Requested stop chain exceeds 3,000 km geodesic length; reduce its extent.",422)
    return points

def cache_path(calculation_id):
    if re.fullmatch(r"[a-f0-9]{64}",calculation_id) is None: raise RoutingError("Invalid calculation identifier.",422)
    return get_settings().provider_cache_dir/("route-"+calculation_id+".json")

def read_cache(calculation_id):
    path=cache_path(calculation_id)
    if path.exists() and time.time()-path.stat().st_mtime<86400:
        try: return json.loads(path.read_text(encoding="utf-8"))
        except (OSError,ValueError): return None
    return None

def calculate(request:RouteRequest):
    points=resolve_points(request)
    settings=get_settings()
    if not settings.routing_enabled: raise RoutingError("Routing is disabled in this environment.",503)
    provider=get_provider()
    alternatives=request.alternatives and len(points)==2
    key=hashlib.sha256(json.dumps({"schema":1,"base":settings.routing_base_url,"provider":provider.name,
        "osrm_profile":settings.routing_osrm_profile,"label":settings.routing_provider_label,
        "points":points,"alternatives":alternatives,"max_snap_m":request.max_snap_m},sort_keys=True).encode()).hexdigest()
    cached=read_cache(key)
    if cached is not None:
        return {**cached,"cached":True}
    result=provider.route(points,alternatives,request.max_snap_m)
    now=datetime.now(timezone.utc).isoformat()
    warnings=list(LIMITATIONS)
    if request.alternatives and len(points)>2: warnings.append("Alternatives disabled for multi-stop request; stop order is preserved.")
    if request.alternatives and len(result["routes"])==1: warnings.append("The provider returned one route only; no alternatives were invented.")
    if any(w["snap_distance_m"]>100 for w in result["waypoints"]):
        warnings.append("At least one reference snapped more than 100 m to a road. Inspect road access and the snapping distances.")
    response={**result,"calculation_id":key,"provider":provider_info()["provider"],"profile":"car","heavy_vehicle_verified":False,
        "retrieved_at":now,"cached":False,"alternatives_requested":request.alternatives,
        "alternatives_queried":alternatives,"crs":"EPSG:4326","warnings":warnings,
        "attribution":provider_info()["attribution"],"policy_url":settings.routing_policy_url,
        "fix_map_url":"https://www.openstreetmap.org/fixthemap"}
    path=cache_path(key);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp");temp.write_text(json.dumps(response),encoding="utf-8");temp.replace(path)
    for stale in sorted(path.parent.glob("route-*.json"),key=lambda p:p.stat().st_mtime)[:-128]:
        stale.unlink(missing_ok=True)
    return response

def save_calculation(payload:SaveRouteRequest,session=None):
    result=read_cache(payload.calculation_id)
    if result is None: raise RoutingError("Calculation cache expired or unavailable. Calculate again before saving.",409)
    if payload.route_index>=len(result["routes"]): raise RoutingError("Alternative route index does not exist.",422)
    selected=result["routes"][payload.route_index]
    key=str(uuid5(NAMESPACE_URL,payload.calculation_id+result["retrieved_at"]+str(payload.route_index)))
    provenance={k:v for k,v in result.items() if k!="routes"}
    provenance["selected_route"]={k:v for k,v in selected.items() if k!="geometry"}
    with (nullcontext(session) if session is not None else Session(get_engine())) as db:
        db.execute(insert(RoutingReference).values(id=key,provider=result["provider"],profile="car",
            geometry=from_shape(shape(selected["geometry"]),srid=4326),provenance=provenance)
            .on_conflict_do_update(index_elements=[RoutingReference.id],set_={"provenance":provenance}))
        if session is None: db.commit()
    return {"id":key,"status":"saved","distance_m":selected["distance_m"],"duration_s":selected["duration_s"],
            "message":"Provider-computed LineString and provenance saved to routing_references."}
