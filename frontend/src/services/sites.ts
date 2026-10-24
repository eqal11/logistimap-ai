import type {FeatureCollection,Geometry,Feature} from 'geojson'
import {request} from './api'
import {csvText} from './analytics'
export interface SiteValue{value:number;note:string}
export interface SiteCandidate{id:string;name:string;feature_id?:string|null;geometry?:Geometry|null;kind:'hypothetical_site'|'reported_existing_facility';values:Record<string,SiteValue>}
export interface SiteCriterion{id:string;source:'gis'|'network'|'user';direction:'cost'|'benefit';weight:number}
export interface SiteReference{feature_id?:string;coordinates?:[number,number];label?:string}
export interface SiteScenario{name:string;candidates:SiteCandidate[];criteria:SiteCriterion[];method:'wlc'|'ahp';ahp_matrix:number[][]|null;allow_inconsistent:boolean;missing_policy:'reject'|'exclude_criterion'|'exclude_candidate';radius_m:number;targets:Partial<Record<'port'|'airport'|'network',SiteReference>>;max_snap_m:number;sensitivity_delta:number}
export interface SiteDefinition{id:string;label:string;unit:string;direction:'cost'|'benefit';availability:'gis'|'network'|'unavailable';description:string}
export interface Cell{value:number|null;status:string;source:string;unit:string;method:string;details:Record<string,unknown>}
export interface AHPResult{weights:number[];lambda_max:number;ci:number;ri:number;cr:number;consistent:boolean;threshold:number}
export interface Prepared{candidates:{id:string;name:string;feature_id:string|null;geometry:Geometry;anchor:[number,number];provenance:Record<string,unknown>}[];values:Record<string,Record<string,Cell>>;warnings:string[]}
export interface Ranking{candidate_id:string;score:number;rank:number;normalized:Record<string,number>;contributions:Record<string,number>}
export interface SiteResult extends FeatureCollection,Prepared{title:string;operation:string;scenario:SiteScenario;rankings:Ranking[];weights:Record<string,number>;ranges:Record<string,{min:number;max:number;constant:boolean;unit:string;direction:string}>;ahp:AHPResult|null;sensitivity:{delta:number;runs:{criterion:string;factor:number;weights:Record<string,number>;rank_changes:Record<string,number>;top_candidate_ids:string[]}[];summary:{candidate_id:string;min_score:number;max_score:number;min_rank:number;max_rank:number}[]};excluded_criteria:string[];excluded_candidates:string[];methodology:string;crs:string;executed_at:string;attribution:string;calculation_id:string;saved_id?:string;profile:string;heavy_vehicle_verified:boolean}
export const initialSites=():SiteScenario=>({name:'Warehouse candidate comparison',candidates:[],criteria:[{id:'road_distance_m',source:'gis',direction:'cost',weight:1},{id:'warehouse_distance_m',source:'gis',direction:'cost',weight:1},{id:'industrial_count',source:'gis',direction:'benefit',weight:1}],method:'wlc',ahp_matrix:null,allow_inconsistent:false,missing_policy:'reject',radius_m:5000,targets:{},max_snap_m:1000,sensitivity_delta:.2})
const post=<T,>(path:string,body:unknown)=>request<T>('/api/sites'+path,undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},120000)
export const siteCatalog=(signal?:AbortSignal)=>request<{criteria:SiteDefinition[]}>('/api/sites/catalog',signal)
export const prepareSites=(s:SiteScenario)=>post<Prepared>('/prepare',s)
export const evaluateSites=(s:SiteScenario)=>post<SiteResult>('/evaluate',s)
export const checkAHP=(matrix:number[][])=>post<AHPResult>('/ahp',{matrix})
export const importSites=(format:string,content:string)=>post<{candidates:SiteCandidate[];warnings:string[]}>('/import',{format,content})
export const saveSites=(id:string)=>post<{id:string;status:string}>('/saved',{calculation_id:id})
export const siteHistory=(offset=0,signal?:AbortSignal)=>request<{items:{id:string;name:string;method:string;created_at:string}[];total:number}>('/api/sites/saved?limit=25&offset='+offset,signal)
export const openSite=(id:string)=>request<SiteResult>('/api/sites/saved/'+encodeURIComponent(id))
export const equalMatrix=(n:number)=>Array.from({length:n},()=>Array(n).fill(1) as number[])
export function siteGeoJSON(r:SiteResult):FeatureCollection{
 return {type:'FeatureCollection',features:r.features,...{metadata:{calculation_id:r.calculation_id,saved_id:r.saved_id??null,title:r.title,methodology:r.methodology,weights:r.weights,ahp:r.ahp,scenario:r.scenario,sensitivity:r.sensitivity,excluded_criteria:r.excluded_criteria,excluded_candidates:r.excluded_candidates,crs:r.crs,executed_at:r.executed_at,attribution:r.attribution,warnings:r.warnings,profile:'car',heavy_vehicle_verified:false,candidate_based:true,raster:false}}}
}
export function siteDisplay(data:FeatureCollection):FeatureCollection{
 return {type:'FeatureCollection',features:data.features.flatMap(f=>{
  const result:Feature[]=[f];const xy=f.properties?.anchor
  if(f.geometry.type!=='Point'&&Array.isArray(xy))result.push({type:'Feature',id:String(f.id)+'-anchor',geometry:{type:'Point',coordinates:xy},properties:{...f.properties,display_anchor:true}})
  return result
 })}
}
export function siteCSVRows(r:SiteResult){
 return r.candidates.map(c=>{const rank=r.rankings.find(x=>x.candidate_id===c.id);return {candidate_id:c.id,name:c.name,classification:c.provenance.kind,rank:rank?.rank??null,score:rank?.score??null,excluded:!rank,source:c.provenance,values:r.values[c.id],normalized:rank?.normalized,contributions:rank?.contributions,weights:r.weights,criterion_definitions:r.scenario.criteria,normalization_ranges:r.ranges,ahp_matrix:r.scenario.ahp_matrix,missing_policy:r.scenario.missing_policy,calculation_id:r.calculation_id,saved_id:r.saved_id??null,ahp:r.ahp,sensitivity:r.sensitivity.summary.find(x=>x.candidate_id===c.id),scenario:r.scenario.name,method:r.scenario.method,executed_at:r.executed_at,attribution:r.attribution,warnings:r.warnings,profile:'car',heavy_vehicle_verified:false}}
 )}
export function exportSitesCSV(r:SiteResult){
 const url=URL.createObjectURL(new Blob(['\uFEFF'+csvText(siteCSVRows(r))],{type:'text/csv;charset=utf-8'}))
 const a=document.createElement('a');a.href=url;a.download='logistimap-site-suitability.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
