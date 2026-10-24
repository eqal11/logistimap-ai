"""Bounded genuine geometry algorithms. No source boundary fabrication."""
import math,time
from collections import Counter,defaultdict,deque
from pyproj import CRS,Transformer,Geod
from shapely.geometry import shape,mapping,box,MultiPoint
from shapely.ops import transform,unary_union,nearest_points
from shapely.strtree import STRtree
from shapely import get_num_coordinates,orient_polygons,transform as transform_coords

GEOD=Geod(ellps="WGS84")
class AnalysisError(ValueError):pass

def geodesic_area(g):
    return abs(GEOD.geometry_area_perimeter(orient_polygons(g,exterior_cw=False))[0])/1e6

def feature(geometry,properties,id):
    return {"type":"Feature","id":str(id),"geometry":mapping(geometry),"properties":properties}

def project_layers(a,b):
    geoms=[shape(f["geometry"]) for f in a+b]
    if not geoms:return (lambda g:g),(lambda g:g),"No geometries"
    extent=unary_union([g.envelope for g in geoms]).bounds
    lon,lat=(extent[0]+extent[2])/2,(extent[1]+extent[3])/2
    if not (99<=lon<=120 and 0<=lat<=8):raise AnalysisError("Analysis extent must be within the Malaysian study region")
    for g in geoms:
        if not g.is_valid or g.is_empty:raise AnalysisError("Input geometry is invalid or empty")
        for x,y in ((g.bounds[0],g.bounds[1]),(g.bounds[2],g.bounds[3])):
            if GEOD.inv(lon,lat,x,y)[2]>250000:raise AnalysisError("Combined analysis extent exceeds 250 km from local projection center; narrow the study area")
    crs=CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs")
    forward=Transformer.from_crs(4326,crs,always_xy=True).transform
    backward=Transformer.from_crs(crs,4326,always_xy=True).transform
    return lambda g:transform_coords(g,forward,interleaved=False),lambda g:transform_coords(g,backward,interleaved=False),crs.to_string()

def parts(g):
    if g.is_empty:return []
    if g.geom_type=="GeometryCollection":return [p for child in g.geoms for p in parts(child)]
    return [g]

def category_counts(features):
    return dict(Counter(c for f in features for c in set(f["properties"].get("categories",[]))))

def dbscan(points,eps,minimum,deadline=None):
    # Exact Euclidean epsilon neighborhoods on metric AEQD representative points.
    # Spatial hash avoids scanning every point outside neighboring cells.
    cells=defaultdict(list)
    for i,p in enumerate(points):cells[(math.floor(p.x/eps),math.floor(p.y/eps))].append(i)
    def near(i):
        p=points[i];x,y=math.floor(p.x/eps),math.floor(p.y/eps)
        return sorted(j for dx in (-1,0,1) for dy in (-1,0,1) for j in cells[(x+dx,y+dy)] if p.distance(points[j])<=eps)
    labels=[-2]*len(points);cluster=0
    for i in range(len(points)):
        if deadline and time.monotonic()>deadline:raise AnalysisError("DBSCAN time budget exceeded; narrow inputs")
        if labels[i]!=-2:continue
        neighbors=near(i)
        if len(neighbors)<minimum:labels[i]=-1;continue
        labels[i]=cluster;pending=deque(neighbors);queued=set(neighbors)
        while pending:
            if deadline and time.monotonic()>deadline:raise AnalysisError("DBSCAN time budget exceeded; narrow inputs")
            j=pending.popleft()
            if labels[j]==-1:labels[j]=cluster
            if labels[j]!=-2:continue
            labels[j]=cluster;expanded=near(j)
            if len(expanded)>=minimum:
                for k in expanded:
                    if k not in queued:queued.add(k);pending.append(k)
        cluster+=1
    return labels

def execute(payload,a,b):
    started=time.monotonic()
    if sum(len(str(f["geometry"])) for f in a+b)>5_000_000:raise AnalysisError("Input geometry exceeds 5 MB")
    fwd,back,crs=project_layers(a,b)
    ga=[fwd(shape(f["geometry"])) for f in a];gb=[fwd(shape(f["geometry"])) for f in b]
    out=[];rows=[];statistics={"input_a":len(a),"input_b":len(b),"category_counts_a":category_counts(a)}
    warnings=["Mapped OSM objects are not a complete facility census or measure of industrial economic activity.",
        "User geometries and computed cluster/grid shapes are analysis references, not verified industrial boundaries.",
        "Metric calculations use local WGS84 azimuthal equidistant projection; bounded to 250 km from its center."]
    def emit(g,props):
        if time.monotonic()-started>20:raise AnalysisError("Analysis time budget exceeded; narrow input")
        for part in parts(g):
            if not part.is_valid:raise AnalysisError("Operation produced invalid geometry")
            wgs=back(part)
            if not wgs.is_valid:raise AnalysisError("Transformation produced invalid geometry")
            out.append(feature(wgs,props,len(out)))
            if len(out)>4000:raise AnalysisError("Result exceeds 4,000 geometries; narrow the inputs")
    op=payload.operation
    mask=unary_union(gb) if gb else None
    if op=="buffer":
        for f,g in zip(a,ga):emit(g.buffer(payload.distance_m,quad_segs=32),{**f["properties"],"input_id":f["id"],"role":"buffer","distance_m":payload.distance_m})
        coverage=unary_union([g.buffer(payload.distance_m,quad_segs=32) for g in ga])
        hits=[f for f,g in zip(b,gb) if coverage.intersects(g)]
        for f in hits:out.append({**f,"id":"match-"+str(f["id"]),"properties":{**f["properties"],"role":"buffer_match"}})
        statistics.update({"matched_count":len(hits),"matched_category_counts":category_counts(hits)})
        rows=[{"id":f["id"],"name":f["properties"].get("name"),"categories":f["properties"].get("categories")} for f in hits]
        warnings.append("Buffer matching uses intersects on supplied input B; this is not a network service area. Selected input features can count themselves if they belong to a B category; overlapping categories are counted separately.")
    elif op in ("intersection","clip","difference"):
        if op=="clip" and any(g.geom_type not in ("Polygon","MultiPolygon") for g in gb):raise AnalysisError("Clip boundary B must contain polygons only")
        tree=STRtree(gb) if gb else None
        for f,g in zip(a,ga):
            if not gb:
                if op=="difference":emit(g,{**f["properties"],"input_id":f["id"],"operation":op})
                continue
            if op=="difference":emit(g.difference(mask),{**f["properties"],"input_id":f["id"],"operation":op})
            elif op=="clip":emit(g.intersection(mask),{**f["properties"],"input_id":f["id"],"operation":op})
            else:
                for j in tree.query(g,predicate="intersects"):
                    emit(g.intersection(gb[j]),{**f["properties"],"input_id":f["id"],"join_id":b[j]["id"],"join_source":b[j]["properties"].get("source"),"operation":op})
    elif op in ("union","dissolve"):
        groups=defaultdict(list)
        for f,g in zip(a+b,ga+gb):
            key=";".join(sorted(f["properties"].get("categories",[]))) if payload.dissolve_by=="category" else "all"
            groups[key].append(g)
        for key,geoms in groups.items():emit(unary_union(geoms),{"name":op+" "+key,"group":key,"input_count":len(geoms),"source":"Derived from input sources; see metadata"})
    elif op in ("nearest","spatial_join","aggregate"):
        if not gb and a:raise AnalysisError("Input B has no candidates")
        tree=STRtree(gb) if gb else None;counts=Counter()
        if op=="aggregate" and any(g.geom_type not in ("Polygon","MultiPolygon") for g in gb):raise AnalysisError("Aggregation B must contain polygon areas")
        for f,g in zip(a,ga):
            if op=="nearest" or payload.predicate=="nearest":
                indices=[int(tree.nearest(g))] if tree is not None else []
            else:
                # query predicate is A relative to B; contains/within boundary semantics are explicit.
                indices=tree.query(g,predicate=payload.predicate).tolist() if tree is not None else []
            for j in indices:
                counts[j]+=1
                pa,pb=nearest_points(g,gb[j]);wa,wb=back(pa),back(pb)
                distance=abs(GEOD.inv(wa.x,wa.y,wb.x,wb.y)[2])
                row={"input_id":f["id"],"input_name":f["properties"].get("name"),"join_id":b[j]["id"],"join_name":b[j]["properties"].get("name"),
                     "distance_m":distance,"source":f["properties"].get("source"),"join_source":b[j]["properties"].get("source")}
                rows.append(row)
                if len(rows)>10000:raise AnalysisError("Join exceeds 10,000 pairs; narrow input")
                if op!="aggregate":emit(g,{**f["properties"],**row,"distance_method":"Geodesic between projected nearest footprint points; not road distance"})
        if op=="aggregate":
            for j,(f,g) in enumerate(zip(b,gb)):
                area=geodesic_area(shape(f["geometry"]))
                emit(g,{**f["properties"],"matched_count":counts[j],"area_km2":area,"density_per_km2":counts[j]/area if area else None})
        statistics.update({"join_pairs":len(rows),"matched_input_count":len({r["input_id"] for r in rows})})
        warnings.append("Nearest ranking uses metric footprint distance with geodesic reported separation; not driving distance. Within excludes boundary-only contacts; intersects includes them.")
    elif op in ("clusters","grid"):
        points=[g.representative_point() for g in ga]
        warnings.append("Each mapped geometry contributes one representative point, including lines/polygons. Category memberships overlap; this is descriptive concentration, not significance testing.")
        statistics["category_counts"]=category_counts(a)
        if op=="clusters":
            labels=dbscan(points,payload.eps_m,payload.min_points,started+20)
            for f,p,label in zip(a,points,labels):emit(p,{**f["properties"],"input_id":f["id"],"cluster_id":label,"role":"cluster_point"})
            for label in sorted(set(labels)-{-1}):
                members=[i for i,c in enumerate(labels) if c==label];hull=MultiPoint([points[i] for i in members]).convex_hull
                if hull.geom_type=="Polygon" and hull.area>1:emit(hull,{"name":"Cluster "+str(label),"cluster_id":label,"count":len(members),"role":"cluster_hull","source":"Computed convex hull; not industrial boundary"})
                rows.append({"cluster_id":label,"count":len(members),"categories":category_counts([a[i] for i in members])})
            statistics.update({"clusters":len(set(labels)-{-1}),"noise":labels.count(-1),"clustered":len(labels)-labels.count(-1)})
        else:
            for f,p in zip(a,points):emit(p,{**f["properties"],"input_id":f["id"],"role":"density_point","weight":1})
            groups=defaultdict(list)
            for i,p in enumerate(points):groups[(math.floor(p.x/payload.grid_m),math.floor(p.y/payload.grid_m))].append(i)
            for (x,y),members in sorted(groups.items()):
                cell=box(x*payload.grid_m,y*payload.grid_m,(x+1)*payload.grid_m,(y+1)*payload.grid_m)
                wgs=back(cell);area=geodesic_area(wgs)
                props={"name":f"Cell {x},{y}","count":len(members),"area_km2":area,"density_per_km2":len(members)/area,"role":"density_grid","source":"Calculated local metric grid"}
                emit(cell,props);rows.append(props)
            statistics.update({"occupied_cells":len(groups),"mapped_objects":len(points),"grid_m":payload.grid_m})
    if time.monotonic()-started>20:raise AnalysisError("Analysis time budget exceeded; narrow input")
    statistics["output_features"]=len(out)
    if sum(get_num_coordinates(shape(f["geometry"])) for f in out)>200000:raise AnalysisError("Output exceeds 200,000 vertices; narrow inputs")
    statistics["summed_output_area_km2"]=sum(geodesic_area(shape(f["geometry"])) for f in out if shape(f["geometry"]).geom_type in ("Polygon","MultiPolygon") and f["properties"].get("role")!="buffer_match")
    return out,rows,statistics,warnings,crs
