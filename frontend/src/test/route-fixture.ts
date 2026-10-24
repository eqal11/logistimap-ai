import type { RouteResult } from '../types/routing'
export const result:RouteResult={
  calculation_id:'a'.repeat(64),provider:'TEST OSRM contract',profile:'car',heavy_vehicle_verified:false,
  retrieved_at:'2026-10-24T04:00:00Z',cached:false,alternatives_requested:true,alternatives_queried:true,crs:'EPSG:4326',
  routes:[{index:0,distance_m:1200,duration_s:120,geometry:{type:'LineString',coordinates:[[101,3],[101.001,3.001],[101.002,3]]},legs:[{distance_m:1200,duration_s:120,summary:'TEST road'}],geometry_length_m:1200},
          {index:1,distance_m:1400,duration_s:150,geometry:{type:'LineString',coordinates:[[101,3],[101.001,3.002],[101.002,3]]},legs:[{distance_m:1400,duration_s:150,summary:'TEST alternative'}],geometry_length_m:1400}],
  waypoints:[{index:0,label:'TEST origin',coordinates:[101,3],snapped_coordinates:[101,3],snap_distance_m:0,road_name:'TEST road'},
             {index:1,label:'TEST destination',coordinates:[101.002,3],snapped_coordinates:[101.002,3],snap_distance_m:0,road_name:'TEST road'}],
  warnings:['Standard car only; no verified truck restrictions'],attribution:'TEST OSM',policy_url:'https://routing.openstreetmap.de/about.html',fix_map_url:'https://www.openstreetmap.org/fixthemap',
}
