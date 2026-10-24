import type {Geometry,Feature,FeatureCollection} from 'geojson'
import {request} from './api'
import {csvText} from './analytics'
export interface LogisticsLocation {id:string;name:string;coordinates:[number,number];feature_id?:string|null;source_id?:string|null;window:[number,number]}
export interface Delivery extends LogisticsLocation {demand:number;service_s:number;priority:number;mandatory:boolean;kind:'delivery'|'pickup';pickup_id?:string|null}
export interface FleetVehicle {id:string;name:string;vehicle_type:string;enabled:boolean;capacity:number;start_depot:string;end_depot:string;window:[number,number];max_distance_m:number;max_duration_s:number;cost_per_km:number;fixed_cost:number;driver_cost_per_hour:number;fuel_l_per_100km:number;fuel_price_per_l:number}
export interface Scenario {name:string;capacity_unit:string;demand_context:'hypothetical'|'user_supplied';notes:string;depots:LogisticsLocation[];vehicles:FleetVehicle[];stops:Delivery[];objective:'distance'|'time'|'cost'|'vehicles'|'balance';allow_unassigned:boolean;solver_seconds:number;max_snap_m:number}
export interface Schedule {id:string;name:string;sequence:number;coordinates:[number,number];kind:string;arrival_s:number;departure_s:number;load_before:number;load_after:number;demand:number;feature_id?:string;source_id?:string}
export interface VehicleRoute {vehicle_id:string;vehicle_name:string;capacity:number;stop_ids:string[];schedule:Schedule[];distance_m:number;travel_duration_s:number;working_duration_s:number;peak_load:number;assigned_demand:number;capacity_utilization_pct:number;estimated_cost:number;cost_components:Record<string,number>;geometry:Geometry|null;geometry_status:string;geometry_error?:string;geometry_distance_m?:number;geometry_duration_s?:number;geometry_matrix_difference_m?:number;road_geometry_constraints_verified?:boolean;road_geometry_arrival_s?:number[]|null;geometry_working_duration_s?:number|null;geometry_cost_components?:Record<string,number>|null;geometry_estimated_cost?:number|null}
export interface OptimizationResult {status:string;solver_status:string;solver_code:number;engine:string;method:string;objective:string;objective_value:number|null;objective_unit:string;proven_optimal:boolean;validated:boolean;elapsed_s:number;time_limit_s:number;routes:VehicleRoute[];unassigned:{id:string;name:string;demand:number;reason:string}[];summary:Record<string,number>;routed_summary?:Record<string,number>|null;scenario:Scenario;matrix:{id:string;nodes:number;pairs:number;unreachable_pairs:number;cached:boolean;upstream_requests:number;retrieved_at:string;distances:(number|null)[][];durations:(number|null)[][];snapped:{coordinates:[number,number];snap_distance_m:number}[];method:string};warnings:string[];provider:string;profile:string;heavy_vehicle_verified:boolean;attribution:string;executed_at:string;geometry_complete:boolean;solution_id?:string;policy_url:string;fix_map_url:string}
export interface SavedScenario {id:string;name:string;created_at:string;archived:boolean;scenario:Scenario}
export interface ScenarioItem {id:string;name:string;created_at:string;archived:boolean;objective:string;stops:number;summary:Record<string,number>|null;status:string}
export interface Job {id:string;scenario_id:string;status:string;stage:string}
export const post=<T,>(path:string,body:unknown={})=>request<T>('/api/optimization'+path,undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
export const saveScenario=(s:Scenario)=>post<{id:string;scenario:Scenario}>('/scenarios',s)
export const listScenarios=(offset=0,archived=false,signal?:AbortSignal)=>request<{items:ScenarioItem[];total:number}>('/api/optimization/scenarios?limit=25&offset='+offset+'&archived='+archived,signal)
export const openScenario=(id:string)=>request<SavedScenario>('/api/optimization/scenarios/'+id)
export const getResults=(id:string)=>request<OptimizationResult>('/api/optimization/scenarios/'+id+'/results')
export const startSolve=(id:string)=>post<{job_id:string}>('/scenarios/'+id+'/solve')
export const getJob=(id:string,signal?:AbortSignal)=>request<Job>('/api/optimization/jobs/'+id,signal)
export const importLocations=(format:string,content:string,context:string)=>post<{stops:Delivery[];count:number;warnings:string[]}>('/import',{format,content,demand_context:context})
export const vehicleColors=['#087f80','#5c60d0','#d07a25','#c84e79','#347ec8','#6c9142']
export const newScenario=():Scenario=>({name:'Untitled logistics scenario',capacity_unit:'units',demand_context:'hypothetical',notes:'',depots:[],vehicles:[],stops:[],objective:'distance',allow_unassigned:true,solver_seconds:3,max_snap_m:1000})
export const newVehicle=(depot:string,index:number):FleetVehicle=>({id:crypto.randomUUID(),name:'Vehicle '+index,vehicle_type:'User-defined vehicle',enabled:true,capacity:10,start_depot:depot,end_depot:depot,window:[0,86400],max_distance_m:1000000,max_duration_s:43200,cost_per_km:0,fixed_cost:0,driver_cost_per_hour:0,fuel_l_per_100km:0,fuel_price_per_l:0})
export function optimizationGeoJSON(r:OptimizationResult):FeatureCollection {
 const features:Feature[]=[]
 r.routes.forEach((route,i)=>{
 if(route.geometry)features.push({type:'Feature',id:route.vehicle_id,geometry:route.geometry,properties:{vehicle_id:route.vehicle_id,vehicle:route.vehicle_name,color:vehicleColors[i%6],distance_m:route.geometry_distance_m??route.distance_m,travel_duration_s:route.geometry_duration_s??route.travel_duration_s,matrix_distance_m:route.distance_m,matrix_travel_duration_s:route.travel_duration_s,matrix_working_duration_s:route.working_duration_s,matrix_estimated_cost_myr:route.estimated_cost,estimated_cost_myr:route.geometry_estimated_cost??null,geometry_distance_m:route.geometry_distance_m,geometry_duration_s:route.geometry_duration_s,geometry_estimated_cost_myr:route.geometry_estimated_cost,road_geometry_constraints_verified:route.road_geometry_constraints_verified,solver_status:r.solver_status,objective:r.objective,provider:r.provider,heavy_vehicle_verified:false,attribution:r.attribution}})
 route.schedule.forEach((p,j)=>features.push({type:'Feature',id:route.vehicle_id+'-'+j,geometry:{type:'Point',coordinates:p.coordinates},properties:{...p,vehicle_id:route.vehicle_id,vehicle:route.vehicle_name,color:vehicleColors[i%6],label:p.kind==='depot'?'D':String(j),role:p.kind==='depot'?'depot':'delivery',attribution:r.attribution,demand_context:r.scenario.demand_context}}))
 })
 return {type:'FeatureCollection',features,...{metadata:{scenario:r.scenario,solver_status:r.solver_status,proven_optimal:r.proven_optimal,provider:r.provider,matrix_id:r.matrix.id,crs:'EPSG:4326',warnings:r.warnings,unassigned:r.unassigned,geometry_complete:r.geometry_complete,attribution:r.attribution,executed_at:r.executed_at}}}
}
export function optimizationCSVRows(r:OptimizationResult,kind:'assignments'|'schedules'|'summary'){
 const rows:Record<string,unknown>[]=kind==='assignments'?r.routes.map(v=>({...Object.fromEntries(Object.entries(v).filter(([k])=>!['geometry','schedule'].includes(k))),cost_components:v.cost_components})):
 kind==='schedules'?r.routes.flatMap(v=>v.schedule.map((p,i)=>({...p,vehicle:v.vehicle_name,final_road_arrival_s:v.road_geometry_arrival_s?.[i]??null,final_road_departure_s:v.road_geometry_arrival_s? v.road_geometry_arrival_s[i]+p.departure_s-p.arrival_s:null})).concat([])):[{...r.summary,final_road_summary:r.routed_summary??null,unassigned:r.unassigned,scenario_assumptions:r.scenario}]
 if(!rows.length)rows.push({record_type:"no_vehicle_routes",status:r.status,unassigned:r.unassigned,scenario_assumptions:r.scenario})
 return rows.map(row=>({...row,metric_basis:"OSRM Table matrix; geometry_* and final_road_* identify final via-point route metrics",scenario:r.scenario.name,demand_context:r.scenario.demand_context,capacity_unit:r.scenario.capacity_unit,solver_status:r.solver_status,proven_optimal:r.proven_optimal,provider:r.provider,attribution:r.attribution,executed_at:r.executed_at}))
}
export function exportOptimizationCSV(r:OptimizationResult,kind:'assignments'|'schedules'|'summary'){
 const data=optimizationCSVRows(r,kind)
 const url=URL.createObjectURL(new Blob(['\uFEFF'+csvText(data)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='logistimap-'+kind+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
export const clockLabel=(s:number)=>String(Math.floor(s/3600)).padStart(2,'0')+':'+String(Math.floor(s%3600/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')


export function optimizationBounds(data:FeatureCollection):[number,number,number,number]|undefined{
 let west=Infinity,south=Infinity,east=-Infinity,north=-Infinity
 function scan(value:unknown){
 if(!Array.isArray(value))return
 if(typeof value[0]==='number'){west=Math.min(west,value[0]);south=Math.min(south,value[1]);east=Math.max(east,value[0]);north=Math.max(north,value[1])}
 else value.forEach(scan)
 }
 data.features.forEach(f=>{if('coordinates' in f.geometry)scan(f.geometry.coordinates)})
 return Number.isFinite(west)?[west,south,east,north]:undefined
}
