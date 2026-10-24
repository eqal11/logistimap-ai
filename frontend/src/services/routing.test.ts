import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { calculateRoute, routeGeoJSON } from './routing'
import { useRouting } from '../store/routing'
import { result } from '../test/route-fixture'

afterEach(()=>vi.unstubAllGlobals())
beforeEach(()=>useRouting.getState().reset())
it('sends feature IDs without substituting browser-generated anchor coordinates',async()=>{
  const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>result})
  vi.stubGlobal('fetch',fetch)
  await calculateRoute([{id:'a',point:{feature_id:'00000000-0000-0000-0000-000000000001',coordinates:[101,3],label:'TEST feature'}},
    {id:'b',point:{coordinates:[101.002,3],label:'TEST end'}}],true,1000)
  const body=JSON.parse(fetch.mock.calls[0][1].body)
  expect(body.points[0]).toEqual({feature_id:'00000000-0000-0000-0000-000000000001',label:'TEST feature'})
  expect(body.points[1].coordinates).toEqual([101.002,3])
  expect(body.profile).toBe('car')
  expect(fetch.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal)
})
it('exports selected provider geometry and metrics with honest provenance',()=>{
  const exported=routeGeoJSON(result,1)
  expect(exported.features[0].geometry).toEqual(result.routes[1].geometry)
  expect(exported.features[0].properties).toMatchObject({distance_m:1400,duration_s:150,profile:'car',heavy_vehicle_verified:false})
  expect(exported.meta.crs).toBe('EPSG:4326')
  expect(exported.features).toHaveLength(5)
  expect(routeGeoJSON(result,0,true).features).toHaveLength(6)
})
it('invalidates old results when inputs change and preserves via stop order',()=>{
  const state=useRouting.getState()
  state.setPoint('origin',{coordinates:[101,3],label:'A'})
  state.setPoint('destination',{coordinates:[102,3],label:'B'})
  state.addStop();state.addStop()
  const ids=useRouting.getState().stops.map(s=>s.id)
  useRouting.getState().setPoint(ids[1],{coordinates:[101.2,3],label:'via 1'})
  useRouting.getState().setPoint(ids[2],{coordinates:[101.4,3],label:'via 2'})
  useRouting.getState().setResult(result)
  useRouting.getState().moveStop(ids[2],-1)
  expect(useRouting.getState().stops.map(s=>s.point?.label)).toEqual(['A','via 2','via 1','B'])
  expect(useRouting.getState().result).toBeNull()
  useRouting.getState().reverse()
  expect(useRouting.getState().stops.map(s=>s.point?.label)).toEqual(['B','via 1','via 2','A'])
  useRouting.getState().removeStop(ids[1])
  expect(useRouting.getState().stops).toHaveLength(3)
})
