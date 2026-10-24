import type {Feature,Geometry} from 'geojson'
import type {CategoryId,Bbox} from '../types'
import type {RoutingPoint} from '../types/routing'
import {request} from './api'
export type Operation='buffer'|'intersection'|'clip'|'union'|'dissolve'|'difference'|'spatial_join'|'nearest'|'aggregate'|'clusters'|'grid'
export interface LayerInput {ids?:string[];query?:{categories:CategoryId[];bbox?:Bbox;center?:[number,number];radius_km?:number};features?:{id:string;geometry:Geometry;name:string}[];saved_id?:string}
export interface AnalysisResult {
 type:'FeatureCollection';title:string;operation:string;features:Feature<Geometry,Record<string,unknown>>[];
 input_features?:Feature<Geometry,Record<string,unknown>>[];rows:Record<string,unknown>[];statistics:Record<string,unknown>;parameters:Record<string,unknown>;inputs:Record<string,unknown>;
 status:string;executed_at:string;crs:string;calculation_crs?:string;attribution:string;warnings:string[];
 calculation_id?:string;saved_id?:string;cached?:boolean;provider?:string
}
export interface HistoryItem {id:string;title:string;operation?:string;count?:number;created_at:string;distance_m?:number;duration_s?:number;provider?:string}
export interface HistoryPage {items:HistoryItem[];total:number;limit:number;offset:number}
export const analyze=(body:object,signal?:AbortSignal)=>request<AnalysisResult>('/api/spatial/analyze',signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},60000)
export const matrix=(origins:RoutingPoint[],destinations:RoutingPoint[],reference:number,signal?:AbortSignal)=>request<AnalysisResult>('/api/routing/matrix',signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({origins:origins.map(pointBody),destinations:destinations.map(pointBody),score_reference_minutes:reference})},60000)
function pointBody(p:RoutingPoint){return p.feature_id?{feature_id:p.feature_id,label:p.label.slice(0,160)}:{coordinates:p.coordinates,label:p.label.slice(0,160)}}
export const compareRegions=(origins:RoutingPoint[],radius:number,categories:CategoryId[],signal?:AbortSignal)=>request<AnalysisResult>('/api/analysis/regions',signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({origins:origins.map(pointBody),radius_km:radius,categories})},60000)
export const getHistory=(kind:string,offset=0,signal?:AbortSignal)=>request<HistoryPage>('/api/history/'+kind+'?limit=25&offset='+offset,signal)
export const openSaved=(kind:string,id:string,signal?:AbortSignal)=>request<AnalysisResult>('/api/history/'+kind+'/'+encodeURIComponent(id),signal)
export const saveAnalysis=(id:string)=>request<{id:string}>('/api/analysis/saved',undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({calculation_id:id})})
export const archiveSaved=(kind:string,id:string)=>request<{id:string;status:string}>('/api/history/'+kind+'/'+encodeURIComponent(id)+'/archive',undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true})})
export const restoreSaved=(kind:string,id:string)=>request<{id:string;status:string}>('/api/history/'+kind+'/'+encodeURIComponent(id)+'/restore',undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmed:true})})
export function csvText(rows:Record<string,unknown>[]){
 const columns=[...new Set(rows.flatMap(r=>Object.keys(r)))];const cell=(value:unknown)=>{
 let s=value==null?'':typeof value==='object'?JSON.stringify(value):String(value)
 if(/^[=+\-@\t\r]/.test(s))s="'"+s
 return '"'+s.replace(/"/g,'""')+'"'
 }
 return [columns.map(cell).join(','),...rows.map(r=>columns.map(c=>cell(r[c])).join(','))].join('\r\n')
}
export function exportCSV(result:AnalysisResult){
 const rows=result.rows.length?result.rows:result.features.map(f=>({id:f.id,...f.properties}))
 const attributed=rows.map(row=>({...row,analysis_title:result.title,analysis_type:result.operation,executed_at:result.executed_at,crs:result.crs,attribution:result.attribution}))
 const url=URL.createObjectURL(new Blob(['\uFEFF'+csvText(attributed)],{type:'text/csv;charset=utf-8'}))
 const a=document.createElement('a');a.href=url;a.download='logistimap-'+result.operation+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
export const operationLabels:Record<Operation,string>={buffer:'Buffer & nearby counts',intersection:'Spatial intersection',clip:'Clip to polygon',union:'Union',dissolve:'Dissolve',difference:'Difference A − B',spatial_join:'Spatial join',nearest:'Nearest facility · geographic',aggregate:'Aggregate by polygon',clusters:'DBSCAN clusters',grid:'Density grid'}
