import {describe,it,expect} from 'vitest'
import {makeOverlay,comparisonGeoJSON,routeKey,comparisonCSVRows} from './comparisons'
import {comparisonFixture} from '../test/comparison-fixture'
describe('historical comparison map and export',()=>{
 it('namespaces repeated vehicle IDs without changing road geometry or source IDs',()=>{
  const {comparison,response}=comparisonFixture(),state=makeOverlay(comparison,response),geo=comparisonGeoJSON(state)
  expect(geo.features).toHaveLength(8)
  expect(new Set(geo.features.map(f=>f.id)).size).toBe(8)
  expect(geo.features[0].geometry).toEqual(response.items[0].result.routes[0].geometry)
  expect(geo.features[0].properties).toMatchObject({scenario_id:'scenario-1',solution_id:'solution-1',profile:'car',heavy_vehicle_verified:false,color:'#087f80'})
  expect(geo.features[2].properties?.source_id).toBe('TEST way/1')
  expect(geo.features[4].properties?.vehicle_id).not.toBe(geo.features[0].properties?.vehicle_id)
 })
 it('hides scenarios/routes independently while preserving other scenario styling',()=>{
  const f=comparisonFixture(),state=makeOverlay(f.comparison,f.response)
  state.hiddenScenarios=['scenario-1'];let geo=comparisonGeoJSON(state)
  expect(geo.features).toHaveLength(4);expect(geo.features[0].properties).toMatchObject({scenario_id:'scenario-2',color:'#7955c7',line_offset:5})
  state.hiddenRoutes=[routeKey(f.response.items[1],'same-vehicle')];expect(comparisonGeoJSON(state).features).toHaveLength(0)
 })
 it('rejects mismatched exact solution references',()=>{
  const f=comparisonFixture();f.response.items[0].solution_id='wrong'
  expect(()=>makeOverlay(f.comparison,f.response)).toThrow('identity mismatch')
 })
 it('limits geometry complexity instead of silently truncating comparison',()=>{
  const f=comparisonFixture()
  f.response.items.forEach(s=>s.result.routes[0].geometry={type:'LineString',coordinates:Array.from({length:150001},(_,i)=>[101+i/100000,3])})
  expect(()=>makeOverlay(f.comparison,f.response)).toThrow('300,000')
 })
 it('never invents a route for missing geometry and retains unassigned/export assumptions',()=>{
  const f=comparisonFixture();f.response.items[0].result.routes[0].geometry=null
  const geo=comparisonGeoJSON(makeOverlay(f.comparison,f.response))
  expect(geo.features.filter(x=>x.geometry.type==='MultiLineString')).toHaveLength(1)
  const rows=comparisonCSVRows(f.comparison)
  expect(rows[0]).toMatchObject({comparison_id:'comparison-1',profile:'car',heavy_vehicle_verified:false,final_road_summary:{distance_m:250,travel_duration_s:25,estimated_cost:1}})
 })
})
