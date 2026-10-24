import type {Feature,FeatureCollection} from 'geojson'
import {request,downloadGeoJSON} from './api'
import {csvText} from './analytics'
import type {AnalysisLayer} from '../store/analytics'
export interface GeoResult {id:string;tool:string;status:'completed'|'failed'|'pending_confirmation'|'cancelled';data:Record<string,unknown>;features:Feature[];rows:Record<string,unknown>[];summary:Record<string,unknown>;warnings:string[];attribution:string;crs:string;executed_at:string;measurement_method:string}
export interface GeoSession {id:string;created_at:string;messages:{id:string;role:string;text:string;created_at:string;partial?:boolean;clarification?:boolean;mode?:string;result_ids?:string[]}[];results:GeoResult[];context:Record<string,unknown>;pending:null|{token:string;call:{tool:string;arguments:object};preview:Record<string,unknown>;expires_at:number}}
export interface GeoResponse {session:GeoSession;results?:GeoResult[];text?:string;partial?:boolean;clarification?:boolean;mode?:string}
export interface GeoHealth {enabled:boolean;provider:{provider:string;configured:boolean;model:string|null;live_verified:boolean;fallback:string};deterministic:string;authentication:string}
export interface GeoTool {name:string;description:string;requires_confirmation:boolean;input_schema:Record<string,unknown>}
export interface GeoHistory {items:{id:string;created_at:string;expires_at:string;messages:number;results:number}[];total:number;limit:number;offset:number}
export const geoHealth=()=>request<GeoHealth>('/api/geoai/health')
export const geoTools=()=>request<{tools:GeoTool[]}>('/api/geoai/tools')
export const geoHistory=(offset=0)=>request<GeoHistory>('/api/geoai/sessions?limit=25&offset='+offset)
export const geoContext=(id:string)=>request<GeoResponse>('/api/geoai/context/'+encodeURIComponent(id))
export const geoRestore=(id:string)=>request<GeoResponse>('/api/geoai/sessions/'+encodeURIComponent(id))
const post=(path:string,body:object,signal?:AbortSignal)=>request<GeoResponse>('/api/geoai/'+path,signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},180000)
export const geoNew=()=>post('sessions',{})
export const geoChat=(body:object,signal?:AbortSignal)=>post('chat',body,signal)
export const geoExecute=(body:object,signal?:AbortSignal)=>post('execute',body,signal)
export const geoConfirm=(session_id:string,token:string)=>post('confirm',{session_id,token,confirmed:true})
export const geoSave=(session_id:string)=>post('save',{session_id})
export const geoCancel=(id:string)=>post('sessions/'+encodeURIComponent(id)+'/cancel',{})
const colors=['#138e83','#586ac7','#bf7c26','#ad547a','#268cb1','#8b6db0']
export function geoLayers(results:GeoResult[],hidden:string[],selected?:string):AnalysisLayer[]{
 return results.filter(r=>r.features.length&&!hidden.includes(r.id)).map((r,i)=>({id:r.id,visible:true,color:colors[i%colors.length],result:{type:'FeatureCollection',title:r.tool,operation:r.tool,features:r.features.map(f=>({...f,id:r.id+'::'+String(f.id),properties:{...f.properties,__result_id:r.id,__original_id:String(f.id)}})),rows:r.rows,statistics:r.summary,parameters:{selected},inputs:{},status:r.status,executed_at:r.executed_at,crs:r.crs,attribution:r.attribution,warnings:r.warnings}}))
}
export function geoExport(r:GeoResult):FeatureCollection&Record<string,unknown>{return {type:'FeatureCollection',features:r.features,metadata:{tool:r.tool,result_id:r.id,executed_at:r.executed_at,summary:r.summary,measurement_method:r.measurement_method,crs:'EPSG:4326',attribution:r.attribution,warnings:r.warnings,profile:'car',heavy_vehicle_verified:false,verification:'Calculated GIS or explicitly saved/user-supplied snapshot; not verified legal/investment advice'}}}
export function geoDownload(r:GeoResult){downloadGeoJSON(geoExport(r),'logistimap-geoai-'+r.tool+'.geojson')}
export function geoCSV(r:GeoResult){return csvText((r.rows.length?r.rows:r.features.map(f=>({id:f.id,...f.properties}))).map(row=>({...row,tool:r.tool,result_id:r.id,executed_at:r.executed_at,attribution:r.attribution,crs:r.crs,measurement_method:r.measurement_method,warnings:r.warnings,profile:'car',heavy_vehicle_verified:false})))}
export function downloadGeoCSV(r:GeoResult){const u=URL.createObjectURL(new Blob(['\uFEFF'+geoCSV(r)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='logistimap-geoai-'+r.tool+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
export {colors as geoColors}
