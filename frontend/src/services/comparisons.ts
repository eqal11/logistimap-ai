import type {FeatureCollection,Feature,Geometry} from 'geojson'
import {request} from './api'
import {post,optimizationGeoJSON,type OptimizationResult} from './optimization'
import {csvText} from './analytics'
export interface ComparisonRow extends Record<string,unknown>{
 scenario_id:string;solution_id?:string;name:string;objective:string;status:string;proven_optimal:boolean;
 distance_m:number;travel_duration_s:number;estimated_cost:number;vehicles_used:number;vehicles_available:number;
 assigned_stops:number;unassigned_stops:number;total_demand:number;assigned_demand:number;
 final_road_summary?:Record<string,number>|null;capacity_unit?:string;demand_context?:string
}
export interface SavedComparison {id:string;name:string;created_at:string;schema_version?:number;rows:ComparisonRow[];warnings:string[];metric_basis?:string;comparable_locations_and_demand:boolean}
export interface ComparisonHistory {items:{id:string;name:string;created_at:string;scenario_count:number;schema_version:number}[];total:number;offset:number;limit:number}
export interface ComparisonSolution {scenario_id:string;solution_id:string;name:string;result:OptimizationResult}
export interface ComparisonSolutions {comparison_id:string;items:ComparisonSolution[];warnings:string[];profile:string;heavy_vehicle_verified:boolean}
export interface ComparisonOverlay {comparison:SavedComparison;items:ComparisonSolution[];hiddenScenarios:string[];hiddenRoutes:string[];selectedRoute:string|null;warnings:string[]}
export const scenarioColors=['#087f80','#7955c7','#ce721d','#2876bf']
export const routePatterns=[[1,0],[4,2],[1,2],[6,2,1,2],[8,3],[3,2,1,2]]
export const routeKey=(s:ComparisonSolution,vehicle:string)=>s.scenario_id+':'+s.solution_id+':'+vehicle
export const listComparisons=(offset=0,signal?:AbortSignal)=>request<ComparisonHistory>('/api/optimization/comparisons?limit=10&offset='+offset,signal)
export const getComparison=(id:string,signal?:AbortSignal)=>request<SavedComparison>('/api/optimization/comparisons/'+encodeURIComponent(id),signal)
export const getComparisonSolutions=(id:string,signal?:AbortSignal)=>request<ComparisonSolutions>('/api/optimization/comparisons/'+encodeURIComponent(id)+'/solutions',signal,{},60000)
export const createComparison=(ids:string[],name:string)=>post<SavedComparison>('/compare',{ids,name})
export function makeOverlay(comparison:SavedComparison,response:ComparisonSolutions):ComparisonOverlay{
 if(response.comparison_id!==comparison.id||response.items.length!==comparison.rows.length)throw new Error('Comparison solution references do not match snapshot.')
 const seen=new Set<string>()
 for(const [i,item] of response.items.entries()){
  const row=comparison.rows[i]
  if(seen.has(item.scenario_id)||row.scenario_id!==item.scenario_id||(row.solution_id&&row.solution_id!==item.solution_id))throw new Error('Comparison solution identity mismatch.')
  seen.add(item.scenario_id)
 }
 const state:ComparisonOverlay={comparison,items:response.items,hiddenScenarios:[],hiddenRoutes:[],selectedRoute:null,warnings:response.warnings}
 state.selectedRoute=response.items.flatMap(item=>item.result.routes.map(r=>routeKey(item,r.vehicle_id)))[0]??null
 comparisonGeoJSON(state) // Validate complexity before placing the response on the map.
 return state
}
function vertices(g:Geometry):number{
 if(g.type==='GeometryCollection')return g.geometries.reduce((n,p)=>n+vertices(p),0)
 const count=(x:unknown):number=>Array.isArray(x)?typeof x[0]==='number'?1:x.reduce<number>((n,p)=>n+count(p),0):0
 return count(g.coordinates)
}
export function comparisonGeoJSON(state:ComparisonOverlay):FeatureCollection{
 const features:Feature[]=[];let complexity=0
 state.items.forEach((item,si)=>{
  if(state.hiddenScenarios.includes(item.scenario_id))return
  optimizationGeoJSON(item.result).features.forEach(f=>{
   const vi=item.result.routes.findIndex(r=>r.vehicle_id===f.properties?.vehicle_id)
   const key=routeKey(item,String(f.properties?.vehicle_id))
   if(state.hiddenRoutes.includes(key))return
   complexity+=vertices(f.geometry)
   if(complexity>300000)throw new Error('Comparison exceeds 300,000 visible vertices. Open fewer or smaller solutions.')
   const label=String.fromCharCode(65+si)+(vi+1)
   features.push({...f,id:key+':'+f.id,properties:{...f.properties,
    original_vehicle_id:f.properties?.vehicle_id,vehicle_id:key,route_key:key,
    scenario_id:item.scenario_id,solution_id:item.solution_id,scenario_name:item.name,scenario_label:String.fromCharCode(65+si),
    color:scenarioColors[si],line_dash:routePatterns[vi%6],dash_index:vi%6,line_offset:si*5,
    label:label+'.'+String(f.properties?.label??''),attribution:item.result.attribution,
    profile:'car',heavy_vehicle_verified:false}})
  })
 })
 return {type:'FeatureCollection',features,...{metadata:{comparison_id:state.comparison.id,name:state.comparison.name,created_at:state.comparison.created_at,
  crs:'EPSG:4326',profile:'car',heavy_vehicle_verified:false,visible_only:true,hidden_scenarios:state.hiddenScenarios,hidden_routes:state.hiddenRoutes,
  visual_offsets:'Line offsets are display pixels only; original road geometry is unchanged.',
  warnings:[...state.comparison.warnings,...state.warnings],solutions:state.items.map(s=>({scenario_id:s.scenario_id,solution_id:s.solution_id,name:s.name,scenario_assumptions:s.result.scenario,attribution:s.result.attribution,unassigned:s.result.unassigned,geometry_complete:s.result.geometry_complete}))}}}
}
export function comparisonCSVRows(c:SavedComparison){
 return c.rows.map(row=>({...row,comparison_id:c.id,comparison_name:c.name,comparison_created_at:c.created_at,
  metric_basis:c.metric_basis??'Stored matrix metrics; legacy comparison',profile:'car',heavy_vehicle_verified:false,
  warnings:c.warnings,attribution:'© OpenStreetMap contributors (ODbL); OSRM routing'}))
}
export function exportComparisonCSV(c:SavedComparison){
 const url=URL.createObjectURL(new Blob(['\uFEFF'+csvText(comparisonCSVRows(c))],{type:'text/csv;charset=utf-8'}))
 const a=document.createElement('a');a.href=url;a.download='logistimap-comparison.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
