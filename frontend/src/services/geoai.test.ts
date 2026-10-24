import {describe,it,expect} from 'vitest'
import {geoExport,geoCSV,geoLayers,type GeoResult} from './geoai'
const feature={type:'Feature' as const,id:'original',geometry:{type:'Point' as const,coordinates:[101.5,3.1]},properties:{name:'=untrusted CSV cell'}}
export const r:GeoResult={id:'run1',tool:'search_industrial_features',status:'completed',data:{},features:[feature],rows:[{id:'original',name:'=untrusted CSV cell',duration_s:120}],summary:{returned:1},warnings:['Coverage limited'],attribution:'OSM ODbL',crs:'EPSG:4326',executed_at:'2026-10-24T00:00:00Z',measurement_method:'OSRM fastest car path'}
describe('GeoAI exports and map layers',()=>{
 it('preserves exact original geometry and provenance in GeoJSON',()=>{const x=geoExport(r);expect(x.features).toEqual([feature]);expect(x.metadata).toMatchObject({profile:'car',heavy_vehicle_verified:false,attribution:'OSM ODbL',result_id:'run1'})})
 it('namespaces display IDs only and obeys layer visibility',()=>{const layers=geoLayers([r],[]);expect(layers[0].result.features[0].id).toBe('run1::original');expect(r.features[0].id).toBe('original');expect(geoLayers([r],['run1'])).toHaveLength(0)})
 it('includes real metrics and mitigates CSV formula injection',()=>{const csv=geoCSV(r);expect(csv).toContain("'=untrusted CSV cell");expect(csv).toContain('120');expect(csv).toContain('OSM ODbL');expect(csv).toContain('car')})
})
