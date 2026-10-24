import type { Bbox, CategoryId } from '../types'
import { request } from './api'
export interface PlaceMatch {name:string;center:[number,number];bbox:Bbox;source_id:string;type:string}
export interface DiscoveryScope {center?:[number,number];radius_km?:number;bbox?:Bbox;label:string;categories?:CategoryId[]}
export interface DiscoveryReport {
  inserted:number;updated:number;valid_features:number;category_counts:Record<string,number>;
  missing_categories:string[];failed_categories:string[];skipped:Record<string,number>;
  osm_base_timestamp?:string;provider_cached?:boolean;message?:string
}
export interface DiscoveryJob {id:string;status:string;created_at:string;parameters:DiscoveryScope;report:DiscoveryReport|null}
export const getStudyTargets=(signal?:AbortSignal)=>request<{areas:{id:string;name:string;query:string;note:string}[]}>('/api/discovery/study-areas',signal)
export const resolveLocation=(q:string,signal?:AbortSignal)=>request<{matches:PlaceMatch[];attribution:string;cached:boolean}>('/api/locations/search?q='+encodeURIComponent(q),signal)
export const getDiscoveryJobs=(signal?:AbortSignal)=>request<{jobs:DiscoveryJob[]}>('/api/discovery/jobs',signal)
export const discover=(payload:DiscoveryScope&{categories:CategoryId[]})=>request<{id:string;status:string}>('/api/discovery/jobs',undefined,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
