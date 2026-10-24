"""OR-Tools RoutingModel with signed on-board loads and independent result checks."""
import math,time
import ortools
from ortools.constraint_solver import pywrapcp,routing_enums_pb2 as enums
from app.schemas.optimization import Scenario

class OptimizationError(ValueError):pass

def cost_components(vehicle,distance,duration):
    fuel=distance/100000*vehicle.fuel_l_per_100km*vehicle.fuel_price_per_l
    return {"distance_cost":distance/1000*vehicle.cost_per_km,"fixed_cost":vehicle.fixed_cost,
            "driver_cost":duration/3600*vehicle.driver_cost_per_hour,"fuel_cost":fuel}

def solve(s:Scenario,matrix:dict)->dict:
    started=time.monotonic()
    nodes=s.depots+s.stops;n=len(nodes);vehicles=[v for v in s.vehicles if v.enabled]
    distance=matrix["distances"];duration=matrix["durations"]
    if len(distance)!=n or len(duration)!=n or any(len(r)!=n for r in distance+duration):
        raise OptimizationError("Matrix dimensions disagree with scenario")
    for i in range(n):
        for j in range(n):
            d,t=distance[i][j],duration[i][j]
            if (d is None)!=(t is None) or (d is not None and (not math.isfinite(d) or not math.isfinite(t) or d<0 or t<0 or d>10_000_000 or t>864000)):
                raise OptimizationError("Invalid matrix metrics")
    idx={p.id:i for i,p in enumerate(nodes)};nd=len(s.depots)
    starts=[idx[v.start_depot] for v in vehicles];ends=[idx[v.end_depot] for v in vehicles]
    manager=pywrapcp.RoutingIndexManager(n,len(vehicles),starts,ends)
    routing=pywrapcp.RoutingModel(manager)
    service=[0]*nd+[p.service_s for p in s.stops]
    # Unreachable arcs are forbidden by constraints, never estimated.
    BIG=100_000_000
    def metric(values,include_service=False):
        return lambda a,b: (BIG if values[manager.IndexToNode(a)][manager.IndexToNode(b)] is None else
            math.ceil(values[manager.IndexToNode(a)][manager.IndexToNode(b)]))+(service[manager.IndexToNode(a)] if include_service else 0)
    di=routing.RegisterTransitCallback(metric(distance));ti=routing.RegisterTransitCallback(metric(duration,True))
    routing.AddDimensionWithVehicleCapacity(di,0,[v.max_distance_m for v in vehicles],True,"Distance")
    routing.AddDimension(ti,86400,86400,False,"Time")
    dist_dim=routing.GetDimensionOrDie("Distance");time_dim=routing.GetDimensionOrDie("Time")
    demands=[0]*nd+[p.demand if p.kind=="pickup" else -p.demand for p in s.stops]
    demand_callback=routing.RegisterUnaryTransitCallback(lambda a:demands[manager.IndexToNode(a)])
    routing.AddDimensionWithVehicleCapacity(demand_callback,0,[v.capacity for v in vehicles],False,"Load")
    load=routing.GetDimensionOrDie("Load")
    hop=routing.RegisterTransitCallback(lambda a,b:1)
    routing.AddDimension(hop,0,n+1,True,"Order");order=routing.GetDimensionOrDie("Order")
    for k,v in enumerate(vehicles):
        start,end=routing.Start(k),routing.End(k)
        for ri,depot in ((start,nodes[starts[k]]),(end,nodes[ends[k]])):
            time_dim.CumulVar(ri).SetRange(max(v.window[0],depot.window[0]),min(v.window[1],depot.window[1]))
        time_dim.SetSpanUpperBoundForVehicle(v.max_duration_s,k)
        load.CumulVar(end).SetValue(0)
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(end))
        routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(start))
    for j in range(nd):
        if j not in starts and j not in ends:
            index=manager.NodeToIndex(j);routing.AddDisjunction([index],0);routing.ActiveVar(index).SetValue(0)
    for j,p in enumerate(s.stops,nd):
        time_dim.CumulVar(manager.NodeToIndex(j)).SetRange(*p.window)
    # Distinct depot nodes cannot be visited as ordinary deliveries.
    solver=routing.solver()
    for a in range(routing.Size()):
        for b in range(routing.Size()+len(vehicles)):
            if b>=manager.GetNumberOfIndices():continue
            if duration[manager.IndexToNode(a)][manager.IndexToNode(b)] is None:
                solver.Add(routing.NextVar(a)!=b)
    max_arc=0
    callbacks=[]
    for k,v in enumerate(vehicles):
        def node_arc(i,j,v=v):
            if distance[i][j] is None:return BIG
            if s.objective=="time":return math.ceil(duration[i][j])
            if s.objective=="cost":
                rate=v.cost_per_km+v.fuel_l_per_100km*v.fuel_price_per_l/100
                return round(distance[i][j]/1000*rate*10000)
            return math.ceil(distance[i][j])
        def arc(a,b,fn=node_arc):
            return fn(manager.IndexToNode(a),manager.IndexToNode(b))
        callbacks.append(arc)
        cb=routing.RegisterTransitCallback(arc);routing.SetArcCostEvaluatorOfVehicle(cb,k)
        if s.objective=="cost":
            routing.SetFixedCostOfVehicle(round(v.fixed_cost*10000),k)
            time_dim.SetSpanCostCoefficientForVehicle(round(v.driver_cost_per_hour/3600*10000),k)
        max_arc=max(max_arc,max(node_arc(i,j) for i in range(n) for j in range(n)))
    # Conservative upper bound makes optional service lexicographically preferred to travel cost.
    objective_bound=max(1,(n+len(vehicles))*max(BIG,max_arc)+sum(round(v.fixed_cost*10000) for v in vehicles)+86400*len(vehicles)*30000)
    if s.objective=="vehicles":
        for k in range(len(vehicles)):routing.SetFixedCostOfVehicle(objective_bound,k)
        objective_bound*=len(vehicles)+1
    if s.objective=="balance":
        dist_dim.SetGlobalSpanCostCoefficient(20);objective_bound*=21
    penalty=objective_bound+1
    for p in s.stops:
        if s.allow_unassigned and not p.mandatory:routing.AddDisjunction([manager.NodeToIndex(idx[p.id])],penalty*p.priority)
    for p in s.stops:
        if p.pickup_id:
            a,b=manager.NodeToIndex(idx[p.pickup_id]),manager.NodeToIndex(idx[p.id])
            routing.AddPickupAndDelivery(a,b)
            solver.Add(routing.VehicleVar(a)==routing.VehicleVar(b))
            solver.Add(order.CumulVar(a)<order.CumulVar(b))
            solver.Add(routing.ActiveVar(a)==routing.ActiveVar(b))
    params=pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy=enums.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    params.local_search_metaheuristic=enums.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds=s.solver_seconds;params.log_search=False
    solution=routing.SolveWithParameters(params)
    code=routing.status()
    names={0:"not_solved",1:"success",2:"partial_success_local_optimum_not_reached",3:"search_failed",
           4:"timeout",5:"invalid",6:"proven_infeasible",7:"proven_optimal"}
    status=names.get(code,"unknown")
    base={"engine":"Google OR-Tools "+ortools.__version__,"solver_code":code,"solver_status":status,
          "objective":s.objective,"elapsed_s":round(time.monotonic()-started,3),
          "time_limit_s":s.solver_seconds,"proven_optimal":code==7,
          "method":"RoutingModel · parallel cheapest insertion + guided local search",
          "objective_unit":"0.0001 MYR plus optional-service penalties" if s.objective=="cost" else "integer seconds" if s.objective=="time" else "integer metres plus configured span/vehicle/service penalties"}
    if solution is None:
        return {**base,"status":"infeasible" if code==6 else "timeout" if code==4 else "no_solution_found",
                "routes":[],"unassigned":[{"id":p.id,"name":p.name,"demand":p.demand,"reason":"No feasible assignment established within solver limits"} for p in s.stops],
                "summary":summary(s,[],s.stops),"objective_value":None,"validated":False}
    routes=[];assigned=set()
    for k,v in enumerate(vehicles):
        if not routing.IsVehicleUsed(solution,k):continue
        a=routing.Start(k);order_nodes=[];schedules=[];d=t=0
        while True:
            node=manager.IndexToNode(a);point=nodes[node];arrival=solution.Value(time_dim.CumulVar(a))
            schedules.append({"id":point.id,"name":point.name,"node_index":node,"sequence":len(schedules),
                "arrival_s":arrival,"departure_s":arrival+service[node],"load_before":solution.Value(load.CumulVar(a)),
                "load_after":solution.Value(load.CumulVar(a))+demands[node],"coordinates":list(point.coordinates),
                "kind":"depot" if node<nd else point.kind,"demand":0 if node<nd else point.demand,
                "feature_id":point.feature_id,"source_id":point.source_id})
            order_nodes.append(node)
            if routing.IsEnd(a):break
            b=solution.Value(routing.NextVar(a));nxt=manager.IndexToNode(b)
            if distance[node][nxt] is None:raise OptimizationError("Solver selected an unreachable arc")
            d+=distance[node][nxt];t+=duration[node][nxt];a=b
        stop_ids=[nodes[j].id for j in order_nodes[1:-1]]
        if any(x in assigned for x in stop_ids):raise OptimizationError("Duplicate delivery assignment")
        assigned.update(stop_ids)
        elapsed=schedules[-1]["arrival_s"]-schedules[0]["arrival_s"]
        components=cost_components(v,d,elapsed)
        routes.append({"vehicle_id":v.id,"vehicle_name":v.name,"capacity":v.capacity,"stop_ids":stop_ids,
            "node_indices":order_nodes,"schedule":schedules,"distance_m":d,"travel_duration_s":t,
            "working_duration_s":elapsed,"service_duration_s":sum(service[j] for j in order_nodes),
            "waiting_duration_s":elapsed-sum(math.ceil(duration[i][j])+service[i] for i,j in zip(order_nodes,order_nodes[1:])),
            "peak_load":max(max(x["load_before"],x["load_after"]) for x in schedules),
            "assigned_demand":sum(nodes[j].demand for j in order_nodes[1:-1] if nodes[j].kind=="delivery"),
            "capacity_utilization_pct":100*max(x["load_before"] for x in schedules)/v.capacity,
            "cost_components":components,"estimated_cost":round(sum(components.values()),2),"geometry":None,"geometry_status":"pending"})
    missing=[p for p in s.stops if p.id not in assigned]
    validate(s,routes,missing,distance,duration)
    return {**base,"status":"optimal" if code==7 else "best_found","routes":routes,
        "unassigned":[{"id":p.id,"name":p.name,"demand":p.demand,"kind":p.kind,"reason":"Excluded by constrained best solution; exact cause not proven"} for p in missing],
        "summary":summary(s,routes,missing),"objective_value":solution.ObjectiveValue(),"validated":True}

def summary(s,routes,missing):
    demand=sum(p.demand for p in s.stops if p.kind=="delivery")
    unassigned=sum(p.demand for p in missing if p.kind=="delivery")
    return {"vehicles_available":sum(v.enabled for v in s.vehicles),"vehicles_used":len(routes),
        "available_capacity":sum(v.capacity for v in s.vehicles if v.enabled),"total_demand":demand,
        "assigned_demand":demand-unassigned,"unassigned_demand":unassigned,
        "assigned_stops":sum(len(r["stop_ids"]) for r in routes),"unassigned_stops":len(missing),
        "cost_per_delivery":round(sum(r["estimated_cost"] for r in routes)/max(1,len([p for p in s.stops if p.kind=="delivery"])-len([p for p in missing if p.kind=="delivery"])),2),
        "cost_per_km":round(sum(r["estimated_cost"] for r in routes)/max(.001,sum(r["distance_m"] for r in routes)/1000),2),
        "fleet_peak_capacity_utilization_pct":round(100*sum(r["peak_load"] for r in routes)/sum(v.capacity for v in s.vehicles if v.enabled),2),
        "distance_m":sum(r["distance_m"] for r in routes),"travel_duration_s":sum(r["travel_duration_s"] for r in routes),
        "working_duration_s":sum(r["working_duration_s"] for r in routes),"estimated_cost":round(sum(r["estimated_cost"] for r in routes),2)}

def validate(s,routes,missing,distance,duration):
    """Do not trust an extracted solution without checking all supported hard constraints."""
    stops={p.id:p for p in s.stops};depots={p.id:p for p in s.depots};vehicles={v.id:v for v in s.vehicles}
    seen=set();owners={};used_vehicles=set()
    node_lookup={p.id:i for i,p in enumerate(s.depots+s.stops)}
    for r in routes:
        v=vehicles[r["vehicle_id"]];schedule=r["schedule"]
        if v.id in used_vehicles or r["stop_ids"]!=[row["id"] for row in schedule if row["kind"]!="depot"]:raise OptimizationError("Vehicle or stop sequence mismatch")
        used_vehicles.add(v.id)
        if not v.enabled or schedule[0]["id"]!=v.start_depot or schedule[-1]["id"]!=v.end_depot:raise OptimizationError("Invalid vehicle/depot assignment")
        actual_d=actual_t=0
        for i,row in enumerate(schedule):
            p=depots.get(row["id"]) or stops.get(row["id"])
            if p is None or row["node_index"]!=node_lookup.get(row["id"]):raise OptimizationError("Schedule node identity mismatch")
            expected_service=0 if row["id"] in depots else p.service_s
            if row["departure_s"]!=row["arrival_s"]+expected_service:raise OptimizationError("Service duration violated")
            if row["id"] in depots and i not in (0,len(schedule)-1):raise OptimizationError("Unexpected intermediate depot")
            if not p.window[0]<=row["arrival_s"]<=p.window[1] or not v.window[0]<=row["arrival_s"]<=v.window[1]:raise OptimizationError("Time window violated")
            if not 0<=row["load_before"]<=v.capacity or not 0<=row["load_after"]<=v.capacity:raise OptimizationError("Capacity violated")
            if i:
                prev=schedule[i-1];a,b=prev["node_index"],row["node_index"]
                if distance[a][b] is None or row["arrival_s"]<prev["departure_s"]+math.ceil(duration[a][b]):raise OptimizationError("Invalid road schedule")
                if row["load_before"]!=prev["load_after"]:raise OptimizationError("Load continuity violated")
                actual_d+=distance[a][b];actual_t+=duration[a][b]
            if row["kind"]!="depot":
                if row["id"] in seen:raise OptimizationError("Duplicate stop")
                seen.add(row["id"]);owners[row["id"]]=(v.id,i)
                expected=p.demand if p.kind=="pickup" else -p.demand
                if row["load_after"]-row["load_before"]!=expected:raise OptimizationError("Invalid load transition")
        if schedule[-1]["load_after"]!=0:raise OptimizationError("Undelivered load")
        if actual_d>v.max_distance_m or schedule[-1]["arrival_s"]-schedule[0]["arrival_s"]>v.max_duration_s:raise OptimizationError("Route limit exceeded")
        if abs(actual_d-r["distance_m"])>.01 or abs(actual_t-r["travel_duration_s"])>.01:raise OptimizationError("Metric mismatch")
    if seen & {p.id for p in missing} or seen|{p.id for p in missing}!=set(stops):raise OptimizationError("Assignment partition violated")
    if any(p.mandatory or not s.allow_unassigned for p in missing):raise OptimizationError("Mandatory delivery omitted")
    for p in s.stops:
        if p.pickup_id:
            a,b=owners.get(p.pickup_id),owners.get(p.id)
            if bool(a)!=bool(b) or (a and (a[0]!=b[0] or a[1]>=b[1])):raise OptimizationError("Pickup/delivery precedence violated")
    return True
