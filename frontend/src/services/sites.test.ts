import {it,expect,vi,afterEach} from 'vitest'
import {initialSites,equalMatrix,siteGeoJSON,siteDisplay,siteCSVRows,exportSitesCSV} from './sites'
import {siteFixture} from '../test/site-fixture'
afterEach(()=>vi.unstubAllGlobals())
it('starts empty with no invented warehouse sites and explicit strict missing policy',()=>{const s=initialSites();expect(s.candidates).toEqual([]);expect(s.missing_policy).toBe('reject');expect(equalMatrix(3)).toEqual([[1,1,1],[1,1,1],[1,1,1]])})
it('preserves polygon export geometry and attaches full method/weights/limitations',()=>{
 const r=siteFixture(),g=siteGeoJSON(r);expect(g.features[1].geometry).toEqual(r.features[1].geometry)
 expect((g as any).metadata).toMatchObject({candidate_based:true,raster:false,heavy_vehicle_verified:false,weights:r.weights})
 expect(siteDisplay(r).features).toHaveLength(3);expect(siteDisplay(r).features[2].properties?.candidate_id).toBe('test-polygon')
})
it('exports criterion provenance, sensitivity, assumptions and attributed CSV through a download',()=>{
 const r=siteFixture();expect(siteCSVRows(r)[0]).toMatchObject({score:50,attribution:'TEST attribution',profile:'car',heavy_vehicle_verified:false,values:r.values['test-point']})
 const create=vi.fn(()=> 'blob:test');vi.stubGlobal('URL',{createObjectURL:create,revokeObjectURL:vi.fn()});const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
 exportSitesCSV(r);expect(create).toHaveBeenCalled();expect(click).toHaveBeenCalled();click.mockRestore()
})
