"""Provider abstraction and OSRM implementation. No straight-line route fallback."""
import hashlib
import json
import math
import time
from collections import deque
from datetime import datetime,timezone
from pathlib import Path
from threading import Lock
from typing import Protocol
from urllib.parse import urlparse

import httpx
from shapely.geometry import LineString
from app.core.config import get_settings
from app.schemas.routing import GEOD,coordinate
from app.services.osm import ssl_context

LIMITATIONS=[
    "Standard car routing, not verified heavy-vehicle routing.",
    "No truck height, width, weight, axle, hazardous-goods or access restriction guarantees.",
    "Travel times are provider estimates; no live traffic, loading, breaks or customs time.",
    "Snapped road positions are not verified facility gates or legal vehicle access.",
    "Alternatives are offered only when the provider returns them; multi-stop alternatives are disabled.",
    "Public demo service: light local use only; no SLA or production capacity guarantee.",
]
class RoutingError(RuntimeError):
    def __init__(self,message,status=502):
        super().__init__(message);self.status=status

class RoutingProvider(Protocol):
    name: str
    def route(self,points:list[dict],alternatives:bool,max_snap_m:int)->dict: ...
    def table(self,points:list[dict],sources:list[int],destinations:list[int],max_snap_m:int)->dict: ...

def finite_number(value,positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (positive and value<=0):
        raise ValueError("Invalid provider metric")
    return float(value)

def normalize_osrm(raw,points,max_snap_m):
    code=raw.get("code") if isinstance(raw,dict) else None
    messages={"NoRoute":"No road route found between these stops.",
              "NoSegment":"A stop could not be snapped to a routable road within the selected radius.",
              "TooBig":"Routing request exceeds the provider limit.",
              "InvalidOptions":"The provider does not support the requested options."}
    if code!="Ok":
        raise RoutingError(messages.get(code,"Routing provider returned an unsuccessful response."),422 if code in ("NoRoute","NoSegment") else 502)
    try:
        waypoints=raw["waypoints"]
        if len(waypoints)!=len(points): raise ValueError("Waypoint mismatch")
        normalized=[]
        for index,(waypoint,point) in enumerate(zip(waypoints,points)):
            snapped=coordinate(waypoint["location"])
            distance=finite_number(waypoint["distance"])
            actual=GEOD.inv(*point["coordinates"],*snapped)[2]
            if distance>max_snap_m+5 or actual>max_snap_m+10: raise ValueError("Excessive snapping")
            normalized.append({**point,"snapped_coordinates":list(snapped),"snap_distance_m":distance,
                               "road_name":str(waypoint.get("name",""))[:240],"index":index})
        if not isinstance(raw["routes"],list) or not 1<=len(raw["routes"])<=3: raise ValueError("Route count")
        routes=[]
        for index,route in enumerate(raw["routes"]):
            distance=finite_number(route["distance"],True);duration=finite_number(route["duration"],True)
            geom=route["geometry"]
            if geom["type"]!="LineString" or not 2<=len(geom["coordinates"])<=50000: raise ValueError("LineString required")
            coords=[list(coordinate(p)) for p in geom["coordinates"]]
            line=LineString(coords)
            if not line.is_valid or line.is_empty: raise ValueError("Invalid route geometry")
            length=GEOD.geometry_length(line)
            if abs(length-distance)>max(100,distance*.15): raise ValueError("Geometry and distance disagree")
            if GEOD.inv(*coords[0],*normalized[0]["snapped_coordinates"])[2]>30 or GEOD.inv(*coords[-1],*normalized[-1]["snapped_coordinates"])[2]>30:
                raise ValueError("Route endpoints disagree")
            legs=[]
            if len(route["legs"])!=len(points)-1: raise ValueError("Leg mismatch")
            for leg in route["legs"]:
                legs.append({"distance_m":finite_number(leg["distance"]),
                    "duration_s":finite_number(leg["duration"]),"summary":str(leg.get("summary",""))[:400]})
            if abs(sum(l["distance_m"] for l in legs)-distance)>max(5,distance*.01) or abs(sum(l["duration_s"] for l in legs)-duration)>max(2,duration*.01):
                raise ValueError("Leg totals disagree")
            routes.append({"index":index,"distance_m":distance,"duration_s":duration,"geometry":{"type":"LineString","coordinates":coords},
                "legs":legs,"geometry_length_m":round(length,2)})
        return {"routes":routes,"waypoints":normalized,"data_version":raw.get("data_version")}
    except (KeyError,TypeError,ValueError,IndexError):
        raise RoutingError("Routing provider returned invalid geometry, metrics or road-snapping metadata; no substitute route generated.") from None

request_lock=Lock()
last_request=0.0
cooldown_until=0.0
request_times=deque()
last_success_at=None
last_failure=None

class OSRMProvider:
    name="osrm"
    def route(self,points,alternatives,max_snap_m):
        global last_request,cooldown_until,last_success_at,last_failure
        settings=get_settings()
        base=settings.routing_base_url.rstrip("/")
        parsed=urlparse(base)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise RoutingError("Routing endpoint must be configured HTTPS without embedded credentials.",503)
        coordinate_path=";".join(f"{p['coordinates'][0]:.7f},{p['coordinates'][1]:.7f}" for p in points)
        url=base+"/route/v1/"+settings.routing_osrm_profile+"/"+coordinate_path
        params={"overview":"full","geometries":"geojson","alternatives":"true" if alternatives else "false",
                "steps":"false","generate_hints":"false","radiuses":";".join(str(max_snap_m) for _ in points)}
        return normalize_osrm(provider_request(url,params),points,max_snap_m)

    def table(self,points,sources,destinations,max_snap_m):
        settings=get_settings()
        path=";".join(f"{p['coordinates'][0]:.7f},{p['coordinates'][1]:.7f}" for p in points)
        params={"annotations":"distance,duration","sources":";".join(map(str,sources)),"destinations":";".join(map(str,destinations)),"radiuses":";".join(str(max_snap_m) for _ in points)}
        return provider_request(settings.routing_base_url.rstrip("/")+"/table/v1/"+settings.routing_osrm_profile+"/"+path,params)

def provider_request(url,params):
    global last_request,cooldown_until,last_success_at,last_failure
    settings=get_settings()
    parsed=urlparse(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RoutingError("Routing endpoint must be configured HTTPS without embedded credentials.",503)
    if not request_lock.acquire(blocking=False):
        raise RoutingError("Routing provider busy. Try again after the current request.",429)
    try:
        now=time.monotonic()
        if now<cooldown_until: raise RoutingError("Routing provider cooling down; retry in "+str(int(cooldown_until-now)+1)+" seconds.",429)
        while request_times and request_times[0]<now-60: request_times.popleft()
        if len(request_times)>=12: raise RoutingError("Local routing quota reached (12 upstream requests/minute). Cached results remain available.",429)
        wait=1.1-(now-last_request)
        if wait>0: time.sleep(wait)
        last_request=time.monotonic();request_times.append(last_request)
        try:
            with httpx.Client(verify=ssl_context(),timeout=httpx.Timeout(20,connect=8),follow_redirects=False,
                    headers={"User-Agent":settings.osm_user_agent,"Accept":"application/json"}) as client:
                with client.stream("GET",url,params=params) as response:
                    if response.status_code in (429,503,504):
                        try: delay=max(60,min(3600,int(response.headers.get("Retry-After","60"))))
                        except ValueError: delay=60
                        cooldown_until=time.monotonic()+delay
                    if response.status_code not in (200,400):
                        raise RoutingError(f"Routing provider HTTP {response.status_code}; no route generated.",503)
                    size=0;chunks=[]
                    for chunk in response.iter_bytes():
                        size+=len(chunk)
                        if size>8_000_000: raise RoutingError("Routing response exceeds 8 MB. Reduce the number or separation of stops.")
                        chunks.append(chunk)
            raw=json.loads(b"".join(chunks))
        except httpx.TimeoutException:
            raise RoutingError("Routing provider timed out after 20 seconds. Retry later; no straight-line fallback.",504) from None
        except (httpx.HTTPError,OSError,ValueError):
            raise RoutingError("Routing provider is unavailable or returned invalid JSON. No straight-line fallback.",503) from None
        last_success_at=datetime.now(timezone.utc).isoformat();last_failure=None
        return raw
    except RoutingError as exc:
        last_failure=str(exc);raise
    finally: request_lock.release()

def get_provider()->RoutingProvider:
    if get_settings().routing_provider=="osrm": return OSRMProvider()
    raise RoutingError("Road routing is disabled. Configure an OSRM-compatible provider.",503)

def provider_info():
    settings=get_settings()
    return {"provider":"OSRM-compatible · "+settings.routing_provider_label,
        "configured":settings.routing_enabled and settings.routing_provider=="osrm",
        "profile":"car","heavy_vehicle_verified":False,"alternatives_supported":True,"matrix_supported":True,"isochrone_supported":False,
        "max_points":8,"max_snap_m":2000,"cache_hours":24,"upstream_requests_per_minute":12,
        "last_success_at":last_success_at,"last_failure":last_failure,
        "cooldown_seconds":max(0,int(cooldown_until-time.monotonic())),
        "limitations":LIMITATIONS,"policy_url":settings.routing_policy_url,
        "attribution":"Routing: OSRM / "+settings.routing_provider_label+" · © OpenStreetMap contributors (ODbL)",
        "fix_map_url":"https://www.openstreetmap.org/fixthemap"}
