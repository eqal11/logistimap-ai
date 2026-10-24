import type { SearchResult } from '../types'
import type { RouteResult, RouteStop, RoutingPoint, RoutingProviderInfo } from '../types/routing'
import { request } from './api'
export const getRoutingProvider=(signal?:AbortSignal)=>request<RoutingProviderInfo>('/api/routing/provider',signal)
export const getFeatureAnchor=(id:string,signal?:AbortSignal)=>request<RoutingPoint>('/api/routing/features/'+encodeURIComponent(id)+'/anchor',signal)
export const getNearestWarehouse=(id:string)=>request<RoutingPoint&{geographic_distance_m:number;method:string}>('/api/routing/features/'+encodeURIComponent(id)+'/nearest-warehouse')
export function findRoutingFacilities(q:string,signal?:AbortSignal){
  const params=new URLSearchParams({q,limit:'25'})
  ;['industrial','warehouse','logistics_hub','port','airport'].forEach(c=>params.append('categories',c))
  return request<SearchResult>('/api/industrial/features?'+params,signal)
}
export function calculateRoute(stops:RouteStop[],alternatives:boolean,maxSnap:number,signal?:AbortSignal){
  const points=stops.map(s=>{
    if(!s.point)throw new Error('Choose an origin, destination and every intermediate stop.')
    return s.point.feature_id?{feature_id:s.point.feature_id,label:s.point.label.slice(0,160)}:
      {coordinates:s.point.coordinates,label:s.point.label.slice(0,160)}
  })
  return request<RouteResult>('/api/routing/route',signal,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({points,profile:'car',alternatives,max_snap_m:maxSnap})},60000)
}
export const saveRoute=(result:RouteResult,index:number)=>request<{id:string;status:string}>('/api/routing/saved',undefined,{
  method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({calculation_id:result.calculation_id,route_index:index})})
export function routeGeoJSON(result:RouteResult,selected:number,all=false){
  const routes=all?result.routes:[result.routes[selected]]
  return {type:'FeatureCollection',features:[
    ...routes.map(route=>({type:'Feature',id:'road-route-'+route.index,geometry:route.geometry,properties:{
      name:route.index===0?'Provider recommended route':'Alternative '+route.index,route_index:route.index,
      distance_m:route.distance_m,duration_s:route.duration_s,legs:route.legs,provider:result.provider,profile:result.profile,
      heavy_vehicle_verified:false,retrieved_at:result.retrieved_at,data_version:result.data_version??null,
      calculation_id:result.calculation_id,attribution:result.attribution,
    }})),
    ...result.waypoints.map((point,index)=>({type:'Feature',id:'input-stop-'+index,
      geometry:{type:'Point',coordinates:point.coordinates},properties:{...point,name:point.label,role:'Requested reference; not a verified entrance'}})),
    ...result.waypoints.map((point,index)=>({type:'Feature',id:'road-snap-'+index,
      geometry:{type:'Point',coordinates:point.snapped_coordinates},properties:{name:point.road_name,role:'Provider road snap',snap_distance_m:point.snap_distance_m}})),
  ],meta:{crs:'EPSG:4326',attribution:result.attribution,profile:result.profile,heavy_vehicle_verified:false,
    retrieved_at:result.retrieved_at,policy_url:result.policy_url,fix_map_url:result.fix_map_url,warnings:result.warnings}}
}
export const distanceLabel=(meters:number)=>(meters/1000).toLocaleString('en-MY',{minimumFractionDigits:2,maximumFractionDigits:2})+' km'
export const durationLabel=(seconds:number)=>{
  const minutes=Math.round(seconds/60)
  return minutes>=60?Math.floor(minutes/60)+' h '+minutes%60+' min':minutes<1?'<1 min':minutes+' min'
}

export function anchorLabel(method?:string){
  if(method==='source_point')return 'Mapped source point; entrance unverified'
  if(method==='geocoder_reference')return 'Place reference; entrance unverified'
  if(method==='user_reference')return 'Selected place or coordinate reference'
  return method?'Representative point from mapped geometry; entrance unverified':'Reference point'
}
