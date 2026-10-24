import type { LineString } from 'geojson'
export type Coordinate=[number,number]
export interface RoutingPoint {
  label:string;coordinates?:Coordinate;feature_id?:string;source?:string;source_id?:string;
  anchor_method?:string;warning?:string;categories?:string[]
}
export interface RouteStop {id:string;point:RoutingPoint|null}
export interface RouteLeg {distance_m:number;duration_s:number;summary:string}
export interface RoadRoute {index:number;distance_m:number;duration_s:number;geometry:LineString;legs:RouteLeg[];geometry_length_m:number}
export interface RoadWaypoint extends RoutingPoint {coordinates:Coordinate;snapped_coordinates:Coordinate;snap_distance_m:number;road_name:string;index:number}
export interface RouteResult {
  calculation_id:string;provider:string;profile:'car';heavy_vehicle_verified:false;retrieved_at:string;
  cached:boolean;alternatives_requested:boolean;alternatives_queried:boolean;crs:'EPSG:4326';
  routes:RoadRoute[];waypoints:RoadWaypoint[];warnings:string[];attribution:string;data_version?:string|null;
  policy_url:string;fix_map_url:string
}
export interface RoutingProviderInfo {
  provider:string;configured:boolean;profile:string;heavy_vehicle_verified:boolean;
  last_success_at:string|null;last_failure:string|null;cooldown_seconds:number;
  limitations:string[];policy_url:string;fix_map_url:string
}
