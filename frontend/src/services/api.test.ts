import { describe, expect, it, vi, afterEach } from 'vitest'
import { parseCoordinates, request, searchFeatures, searchMapFeatures } from './api'
afterEach(()=>vi.unstubAllGlobals())
describe('Coordinate search',()=>{
  it('requires explicit longitude,latitude order and valid bounds',()=>{
    expect(parseCoordinates('101.55, 3.12')).toEqual([101.55,3.12])
    expect(parseCoordinates('101.55 3.12')).toEqual([101.55,3.12])
    for(const text of ['Klang','181,3','101,91','nan,3','101,','',',3','1,2,3'])expect(parseCoordinates(text)).toBeNull()
  })
})
describe('API contract',()=>{
  it('sends every selected category and spatial query to backend',async()=>{
    const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({features:[]})})
    vi.stubGlobal('fetch',fetch)
    await searchFeatures({q:'warehouse',categories:['warehouse','industrial','port'],bbox:[101,2,102,4],offset:250})
    const url=new URL(fetch.mock.calls[0][0],'http://localhost')
    expect(url.searchParams.getAll('categories')).toEqual(['warehouse','industrial','port'])
    expect(url.searchParams.get('bbox')).toBe('101,2,102,4')
    expect(url.searchParams.get('offset')).toBe('250')
    expect(fetch.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal)
  })
  it('surfaces actionable API failures instead of fixture fallback',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:503,json:async()=>({error:{message:'Provider unavailable. No fixture fallback.'}})}))
    await expect(request('/api/industrial/features')).rejects.toThrow('No fixture fallback')
  })
  it('handles non-JSON gateway failures',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:502,json:async()=>{throw new Error('not json')}}))
    await expect(request('/health')).rejects.toThrow('502')
  })
})


it('loads every query page for map and export while retaining all categories',async()=>{
  const meta={mode:'postgis',crs:'EPSG:4326',total:1002,returned:1000,offset:0,limit:1000,has_more:true,
    category_counts:{warehouse:1,port:1},missing_categories:[],failed_categories:[],warnings:['Results are paginated'],attribution:'OSM'}
  const fetch=vi.fn().mockImplementation(async(url:string)=>{
    const offset=Number(new URL(url,'http://localhost').searchParams.get('offset'))
    return {ok:true,json:async()=>({type:'FeatureCollection',features:Array.from({length:offset?2:1000},(_,i)=>({id:String(offset+i)})),meta:{...meta,offset}})}
  })
  vi.stubGlobal('fetch',fetch)
  const result=await searchMapFeatures({q:'',categories:['warehouse','port'],offset:250})
  expect(result.features).toHaveLength(1002)
  expect(result.meta.has_more).toBe(false)
  expect(result.meta.warnings).toEqual([])
  expect(fetch).toHaveBeenCalledTimes(2)
  expect(new URL(fetch.mock.calls[1][0],'http://localhost').searchParams.getAll('categories')).toEqual(['warehouse','port'])
})
