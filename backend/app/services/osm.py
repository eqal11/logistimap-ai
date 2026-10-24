"""Read-only public providers, cached and serialized. Geometry comes only from OSM."""
import hashlib
import json
import ssl
import time
from collections import Counter
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping, shape
from shapely.ops import linemerge, polygonize, unary_union

from app.core.config import get_settings
from app.schemas.discovery import DiscoveryRequest
from app.schemas.spatial import Geometry

ATTRIBUTION = "© OpenStreetMap contributors · ODbL 1.0 · https://www.openstreetmap.org/copyright"
# Includes major roads only. No vehicle restrictions, cargo status, or ownership inferred.
SELECTORS = {
    "industrial": ['["man_made"="works"]','["industrial"]'],
    "industrial_park": ['["landuse"="industrial"]','["industrial"="industrial_park"]'],
    "warehouse": ['["building"="warehouse"]','["industrial"="warehouse"]','["warehouse"="yes"]'],
    "logistics_hub": ['["industrial"~"^(logistics|distribution)$"]','["landuse"="logistics"]','["office"="logistics"]','["building"="logistics"]'],
    "port": ['["landuse"="port"]','["industrial"="port"]','["harbour"="yes"]','["seamark:type"="harbour"]'],
    "airport": ['["aeroway"="aerodrome"]'],
    "road": ['["highway"~"^(motorway|trunk|primary|secondary)(_link)?$"]'],
    "rail": ['["railway"~"^(rail|narrow_gauge|light_rail|station)$"]'],
}
locks = {"geocode": Lock(), "overpass": Lock()}
last_request = {"geocode": 0.0, "overpass": 0.0}
blocked_until = {"geocode": 0.0, "overpass": 0.0}

class ProviderError(RuntimeError):
    pass

def ssl_context():
    # Windows certificate store; do not enable environment-driven TLS key logging.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_default_certs()
    return context

def public_json(kind, url, key, *, params=None, data=None):
    settings = get_settings()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ProviderError("Provider must use a configured HTTPS endpoint without embedded credentials.")
    digest = hashlib.sha256((url + key).encode()).hexdigest()
    cache = settings.provider_cache_dir / (kind + "-" + digest + ".json")
    ttl = 7*86400 if kind == "geocode" else 86400
    with locks[kind]:
        if cache.exists() and time.time()-cache.stat().st_mtime < ttl:
            try:
                return json.loads(cache.read_text(encoding="utf-8")), True
            except (OSError,ValueError):
                pass
        if time.monotonic() < blocked_until[kind]:
            raise ProviderError(f"{kind} provider cooldown; retry after {int(blocked_until[kind]-time.monotonic())+1} seconds.")
        interval = 1.1 if kind == "geocode" else 12.0
        wait = interval - (time.monotonic()-last_request[kind])
        if wait > 0:
            time.sleep(wait)
        last_request[kind] = time.monotonic()
        # No automatic retries: a user may retry after the cooldown; no endpoint rotation.
        try:
            with httpx.Client(verify=ssl_context(), timeout=httpx.Timeout(85,connect=15),
                              headers={"User-Agent":settings.osm_user_agent,"Accept":"application/json"},
                              follow_redirects=False) as client:
                with client.stream("POST" if data else "GET",url,params=params,data=data) as response:
                    if response.status_code in (429,503,504):
                        try: delay=max(60,min(3600,int(response.headers.get("Retry-After","60"))))
                        except ValueError: delay=60
                        blocked_until[kind]=time.monotonic()+delay
                    if response.status_code != 200:
                        raise ProviderError(f"{kind} provider returned HTTP {response.status_code}; wait before retrying.")
                    chunks=[]; size=0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 25_000_000:
                            raise ProviderError("Provider response exceeds the 25 MB safety limit; reduce the study area.")
                        chunks.append(chunk)
            result = json.loads(b"".join(chunks))
        except (httpx.HTTPError,ValueError,OSError):
            raise ProviderError(f"{kind} provider unavailable or returned invalid JSON; no synthetic fallback.") from None
        if isinstance(result,dict) and result.get("remark"):
            # Overpass timeout responses can contain partial data. Never mark them complete.
            raise ProviderError("Overpass reported an incomplete query (timeout/resource limit); reduce the area and retry.")
        cache.parent.mkdir(parents=True,exist_ok=True)
        temp = cache.with_suffix(".tmp")
        temp.write_text(json.dumps(result),encoding="utf-8");temp.replace(cache)
        # Bound disk cache. Files contain public OSM responses only, never credentials.
        for stale in sorted(settings.provider_cache_dir.glob(kind+"-*.json"),key=lambda p:p.stat().st_mtime)[:-100]:
            stale.unlink(missing_ok=True)
        return result,False

def geocode(query):
    query = " ".join(query.split())
    if not 2 <= len(query) <= 200:
        raise ProviderError("Place name must contain 2–200 characters.")
    raw,cached = public_json("geocode",get_settings().geocoding_url,query.casefold(),
        params={"q":query,"format":"jsonv2","countrycodes":"my","limit":5})
    if not isinstance(raw,list):
        raise ProviderError("Geocoder response has an unexpected structure.")
    matches=[]
    raw.sort(key=lambda item: item.get("category",item.get("class")) not in ("place","boundary"))
    for item in raw:
        try:
            center=[float(item["lon"]),float(item["lat"])]
            south,north,west,east=map(float,item["boundingbox"])
            if not (99 <= center[0] <= 120 and 0 <= center[1] <= 8):
                continue
            Geometry(type="Point",coordinates=center)
            matches.append({"name":item["display_name"],"center":center,"bbox":[west,south,east,north],
                            "source_id":str(item["osm_type"])+"/"+str(item["osm_id"]),"type":item.get("type","unknown")})
        except (KeyError,ValueError,TypeError,ValidationError):
            continue
    return {"matches":matches,"cached":cached,"attribution":ATTRIBUTION,
            "warning":"Place search references are not verified industrial boundaries."}

def build_query(request: DiscoveryRequest):
    if request.bbox:
        west,south,east,north=request.bbox
        scope=f"({south},{west},{north},{east})"
    else:
        lon,lat=request.center
        scope=f"(around:{request.radius_km*1000},{lat},{lon})"
    selectors = dict.fromkeys(s for c in request.categories for s in SELECTORS[c.value])
    return '[out:json][timeout:60][maxsize:33554432];(' + "".join("nwr"+s+scope+";" for s in selectors) + ");out meta geom;"

def memberships(tags):
    result=[]
    if tags.get("man_made")=="works" or "industrial" in tags: result.append("industrial")
    if tags.get("landuse")=="industrial" or tags.get("industrial")=="industrial_park": result.append("industrial_park")
    if tags.get("building")=="warehouse" or tags.get("industrial")=="warehouse" or tags.get("warehouse")=="yes": result.append("warehouse")
    if tags.get("industrial") in ("logistics","distribution") or tags.get("landuse")=="logistics" or tags.get("office")=="logistics" or tags.get("building")=="logistics": result.append("logistics_hub")
    if tags.get("landuse")=="port" or tags.get("industrial")=="port" or tags.get("harbour")=="yes" or tags.get("seamark:type")=="harbour": result.append("port")
    if tags.get("aeroway")=="aerodrome": result.append("airport")
    if tags.get("highway") in {a+b for a in ("motorway","trunk","primary","secondary") for b in ("","_link")}: result.append("road")
    if tags.get("railway") in ("rail","narrow_gauge","light_rail","station"): result.append("rail")
    return result

def coordinates(raw):
    if not isinstance(raw,list) or not raw or any(not isinstance(p,dict) or "lon" not in p or "lat" not in p for p in raw):
        raise ValueError("missing_geometry")
    return [(p["lon"],p["lat"]) for p in raw]

def rings(lines):
    if not lines: return []
    # polygonize joins split outer/inner members using their actual endpoints.
    merged=unary_union([LineString(line) for line in lines])
    polygons=list(polygonize(merged))
    # Every segment must belong to a closed ring; reject incomplete relations.
    if not polygons or not merged.difference(unary_union([p.boundary for p in polygons])).is_empty:
        raise ValueError("incomplete_relation")
    return polygons

def geometry_from_element(element):
    tags=element.get("tags",{})
    if element["type"]=="node":
        return {"type":"Point","coordinates":[element["lon"],element["lat"]]}
    if element["type"]=="way":
        pts=coordinates(element.get("geometry"))
        if len(pts)<2: raise ValueError("short_way")
        linear=tags.get("area")=="no" or "highway" in tags or tags.get("railway") not in (None,"station")
        area=tags.get("area")=="yes" or any(k in tags for k in ("building","landuse","industrial")) or tags.get("aeroway")=="aerodrome" or tags.get("man_made")=="works"
        if len(pts)>=4 and pts[0]==pts[-1] and area and not linear:
            return {"type":"Polygon","coordinates":[pts]}
        return {"type":"LineString","coordinates":pts}
    if element["type"]=="relation" and tags.get("type")=="multipolygon":
        members=[m for m in element.get("members",[]) if m.get("type")=="way"]
        outer=rings([coordinates(m.get("geometry")) for m in members if m.get("role","") in ("outer","")])
        inner=rings([coordinates(m.get("geometry")) for m in members if m.get("role")=="inner"])
        if not outer or any(not any(o.covers(p) for o in outer) for p in inner): raise ValueError("invalid_relation")
        parts=[o.difference(unary_union([p for p in inner if o.covers(p)])) for o in outer]
        result=unary_union(parts)
        if result.geom_type not in ("Polygon","MultiPolygon"): raise ValueError("invalid_relation")
        return mapping(result)
    raise ValueError("unsupported_relation")

def normalize(raw,request):
    if not isinstance(raw,dict) or not isinstance(raw.get("elements"),list):
        raise ProviderError("Overpass response has an unexpected structure.")
    if len(raw["elements"])>12000:
        raise ProviderError("Query exceeds 12,000 objects; reduce area or categories. Nothing imported.")
    features={}; skipped=Counter(); examples=[]; requested={c.value for c in request.categories}
    for element in raw["elements"]:
        source_id=str(element.get("type"))+"/"+str(element.get("id"))
        tags=element.get("tags",{})
        cats=memberships(tags)
        if not requested.intersection(cats):
            continue
        try:
            geom=Geometry.model_validate_json(json.dumps(geometry_from_element(element))).model_dump()
            name=tags.get("name") or tags.get("name:en") or tags.get("name:ms") or f"Unnamed OSM {cats[0]} ({source_id})"
            attrs={"osm_tags":tags,"osm_type":element["type"],"osm_id":element["id"],
                   "osm_version":element.get("version"),"osm_timestamp":element.get("timestamp"),
                   "source_url":"https://www.openstreetmap.org/"+source_id,
                   "classification":"OSM tags; industrial land-use is not a verified park boundary.",
                   "capacity":None,"rental_price":None,"available_space":None}
            features[source_id]={"source_id":source_id,"name":name[:240],"categories":cats,"geometry":geom,
                "boundary_status":"unverified" if geom["type"] in ("Polygon","MultiPolygon") else "not_applicable",
                "attributes":attrs}
        except (ValueError,KeyError,TypeError,ValidationError):
            reason="invalid_or_incomplete_geometry"
            skipped[reason]+=1
            if len(examples)<20: examples.append({"source_id":source_id,"reason":reason})
    counts=Counter(c for feature in features.values() for c in feature["categories"])
    return list(features.values()), {"raw_elements":len(raw["elements"]),"valid_features":len(features),
        "duplicates_in_response":len(raw["elements"])-len({str(e.get("type"))+"/"+str(e.get("id")) for e in raw["elements"]}),
        "category_counts":{c:counts.get(c,0) for c in requested},"missing_categories":[c for c in requested if not counts.get(c)],
        "failed_categories":[],"skipped":dict(skipped),"failed_record_examples":examples,
        "osm_base_timestamp":raw.get("osm3s",{}).get("timestamp_osm_base"),
        "attribution":ATTRIBUTION,"warnings":[
            "OSM coverage is incomplete; zero results do not prove real-world absence.",
            "Industrial land-use polygons are community mapped, not authoritative park/zoning boundaries.",
            "Roads include motorway, trunk, primary, secondary and links only. Lines are source infrastructure, not computed routes.",
            "Airports do not imply verified cargo capability. Unknown commercial attributes remain unknown.",
            "OSM ways/relations with distinct IDs are preserved even when spatially overlapping."
        ]}
