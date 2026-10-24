"""Validated road-network matrices. No fallback speed or straight-line cells."""
import hashlib,json,time
from datetime import datetime,timezone
from app.core.config import get_settings
from app.routing.providers import get_provider,provider_info,RoutingError,finite_number
from app.schemas.routing import GEOD,coordinate

def road_matrix(points,max_snap_m=1000,provider=None,progress=lambda x:None):
    if not 2<=len(points)<=24:raise RoutingError("Road matrix requires 2–24 nodes.",422)
    if any(GEOD.inv(*a["coordinates"],*b["coordinates"])[2]>3_000_000 for a in points for b in points):
        raise RoutingError("Matrix extent exceeds 3,000 km.",422)
    settings=get_settings();provider=provider or get_provider()
    key=hashlib.sha256(json.dumps({"schema":1,"base":settings.routing_base_url,"profile":settings.routing_osrm_profile,
        "coordinates":[p["coordinates"] for p in points],"snap":max_snap_m},sort_keys=True).encode()).hexdigest()
    path=settings.provider_cache_dir/("vrp-matrix-"+key+".json")
    if path.exists() and time.time()-path.stat().st_mtime<86400:
        result=json.loads(path.read_text(encoding="utf-8"));return {**result,"cached":True}
    n=len(points);distances=[[None]*n for _ in points];durations=[[None]*n for _ in points]
    snapped=[None]*n
    # Up to 16 coordinates per light table request. Larger scenarios use bounded 8×8 blocks.
    groups=[list(range(n))] if n<=16 else [list(range(i,min(i+8,n))) for i in range(0,n,8)]
    requests=0
    for sources in groups:
        for destinations in groups:
            progress(f"Road matrix block {requests+1}/{len(groups)**2}")
            unique=list(dict.fromkeys(sources+destinations));local={v:i for i,v in enumerate(unique)}
            raw=provider.table([points[i] for i in unique],[local[i] for i in sources],[local[i] for i in destinations],max_snap_m)
            if not isinstance(raw,dict) or raw.get("code")!="Ok":
                raise RoutingError("OSRM table failed; provider size, snapping or availability limit. No fallback matrix.",422)
            try:
                if raw.get("fallback_speed_cells"):raise ValueError()
                for name,indices in (("sources",sources),("destinations",destinations)):
                    if len(raw[name])!=len(indices):raise ValueError()
                    for wp,j in zip(raw[name],indices):
                        xy=list(coordinate(wp["location"]));d=finite_number(wp["distance"])
                        if d>max_snap_m+5 or GEOD.inv(*points[j]["coordinates"],*xy)[2]>max_snap_m+10:raise ValueError()
                        if snapped[j] and GEOD.inv(*snapped[j]["coordinates"],*xy)[2]>5:raise ValueError()
                        snapped[j]={"coordinates":xy,"snap_distance_m":d,"road_name":str(wp.get("name",""))[:240]}
                if len(raw["distances"])!=len(sources) or len(raw["durations"])!=len(sources):raise ValueError()
                for a,i in enumerate(sources):
                    if len(raw["distances"][a])!=len(destinations) or len(raw["durations"][a])!=len(destinations):raise ValueError()
                    for b,j in enumerate(destinations):
                        d,t=raw["distances"][a][b],raw["durations"][a][b]
                        if (d is None)!=(t is None):raise ValueError()
                        if d is not None:
                            d,t=finite_number(d),finite_number(t)
                            if d>10_000_000 or t>864000:raise ValueError()
                        distances[i][j]=d;durations[i][j]=t
            except (ValueError,KeyError,TypeError,IndexError):
                raise RoutingError("Invalid matrix dimensions, metrics or inconsistent road snaps.",502) from None
            requests+=1
    result={"id":key,"distances":distances,"durations":durations,"snapped":snapped,"nodes":n,"pairs":n*n,
        "unreachable_pairs":sum(x is None for row in distances for x in row),"provider":provider_info()["provider"],
        "profile":"car","heavy_vehicle_verified":False,"retrieved_at":datetime.now(timezone.utc).isoformat(),
        "cached":False,"upstream_requests":requests,"attribution":provider_info()["attribution"],
        "method":"OSRM Table fastest-path road distance (metres) and duration (seconds); asymmetric; no fallback_speed."}
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(".tmp");temp.write_text(json.dumps(result),encoding="utf-8");temp.replace(path)
    for stale in sorted(path.parent.glob("vrp-matrix-*.json"),key=lambda p:p.stat().st_mtime)[:-64]:stale.unlink(missing_ok=True)
    return result
