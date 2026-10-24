import {newScenario,newVehicle,type OptimizationResult} from '../services/optimization'
import type {SavedComparison,ComparisonSolutions} from '../services/comparisons'
export function resultFixture():OptimizationResult{
 const scenario=newScenario();scenario.name='TEST hypothetical scenario';scenario.capacity_unit='TEST units'
 scenario.depots=[{id:'d',name:'TEST depot',coordinates:[101,3],window:[0,86400]}]
 scenario.stops=[{id:'s',name:'TEST candidate',coordinates:[101.01,3],window:[0,86400],demand:2,service_s:0,priority:1,mandatory:false,kind:'delivery',source_id:'TEST way/1'}]
 scenario.vehicles=[{...newVehicle('d',1),id:'same-vehicle'}]
 const schedule=[{id:'d',name:'TEST depot',sequence:0,coordinates:[101,3] as [number,number],kind:'depot',arrival_s:0,departure_s:0,load_before:2,load_after:2,demand:0},
 {id:'s',name:'TEST candidate',sequence:1,coordinates:[101.01,3] as [number,number],kind:'delivery',arrival_s:10,departure_s:10,load_before:2,load_after:0,demand:2,source_id:'TEST way/1'},
 {id:'d',name:'TEST depot',sequence:2,coordinates:[101,3] as [number,number],kind:'depot',arrival_s:25,departure_s:25,load_before:0,load_after:0,demand:0}]
 return {status:'best_found',solver_status:'success',solver_code:1,engine:'TEST OR-Tools',method:'TEST numeric fixture',objective:'distance',objective_value:250,objective_unit:'metres',proven_optimal:false,validated:true,elapsed_s:1,time_limit_s:1,
 routes:[{vehicle_id:'same-vehicle',vehicle_name:'Vehicle 1',capacity:10,stop_ids:['s'],schedule,distance_m:250,travel_duration_s:25,working_duration_s:25,peak_load:2,assigned_demand:2,capacity_utilization_pct:20,estimated_cost:1,cost_components:{distance_cost:1,fixed_cost:0,driver_cost:0,fuel_cost:0},geometry:{type:'MultiLineString',coordinates:[[[101,3],[101.01,3],[101,3]]]},geometry_status:'available',geometry_distance_m:250,geometry_duration_s:25,geometry_estimated_cost:1,road_geometry_constraints_verified:true,road_geometry_arrival_s:[0,10,25]}],
 unassigned:[],summary:{distance_m:250,travel_duration_s:25,estimated_cost:1,assigned_stops:1,unassigned_stops:0,vehicles_used:1,vehicles_available:1,total_demand:2,assigned_demand:2},
 routed_summary:{distance_m:250,travel_duration_s:25,estimated_cost:1},scenario,matrix:{id:'TEST matrix',nodes:2,pairs:4,unreachable_pairs:0,cached:true,upstream_requests:1,retrieved_at:'TEST',distances:[[0,100],[150,0]],durations:[[0,10],[15,0]],snapped:[],method:'TEST synthetic numeric data'},warnings:['TEST synthetic fixture only'],provider:'TEST provider',profile:'car',heavy_vehicle_verified:false,attribution:'TEST attribution',executed_at:'2026-10-24',geometry_complete:true,solution_id:'solution-1',policy_url:'https://example.test',fix_map_url:'https://example.test'}
}
export function comparisonFixture(){
 const a=resultFixture(),b=resultFixture();b.solution_id='solution-2'
 const items=[{scenario_id:'scenario-1',solution_id:'solution-1',name:'TEST one',result:a},{scenario_id:'scenario-2',solution_id:'solution-2',name:'TEST two',result:b}]
 const comparison:SavedComparison={id:'comparison-1',name:'TEST pinned comparison',created_at:'2026-10-24T11:00:00Z',schema_version:2,rows:items.map(s=>({scenario_id:s.scenario_id,solution_id:s.solution_id,name:s.name,objective:'distance',status:'best_found',proven_optimal:false,distance_m:250,travel_duration_s:25,estimated_cost:1,vehicles_used:1,vehicles_available:1,assigned_stops:1,unassigned_stops:0,total_demand:2,assigned_demand:2,final_road_summary:s.result.routed_summary})),warnings:['TEST hypothetical demand'],comparable_locations_and_demand:true}
 const response:ComparisonSolutions={comparison_id:comparison.id,items,warnings:[],profile:'car',heavy_vehicle_verified:false}
 return {comparison,response}
}
