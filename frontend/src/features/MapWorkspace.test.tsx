import type {LayerSpecification} from 'maplibre-gl'
import {validateStyleMin} from '@maplibre/maplibre-gl-style-spec'
import {comparisonFixture} from '../test/comparison-fixture'
import {makeOverlay,comparisonGeoJSON,routeKey} from '../services/comparisons'
import { result as routeResult } from '../test/route-fixture'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { MapWorkspace } from './MapWorkspace'
import { useWorkspace } from '../store/workspace'
import { categories, type SearchResult, type SpatialFeature } from '../types'
const mock=vi.hoisted(()=>({handlers:{} as Record<string,(event?:unknown)=>void>,sources:new Map<string,{setData:ReturnType<typeof vi.fn>}>(),layers:new Set<string>(),definitions:new Map<string,LayerSpecification>(),paint:vi.fn(),query:vi.fn()}))
vi.mock('maplibre-gl',()=>({
  Map:class {
    addControl(){return this}
    doubleClickZoom={disable:vi.fn()}
    on(event:string,callback:(event?:unknown)=>void){mock.handlers[event]=callback;return this}
    addSource(id:string){mock.sources.set(id,{setData:vi.fn()})}
    getSource(id:string){return mock.sources.get(id)}
    addLayer(layer:LayerSpecification){mock.layers.add(layer.id);mock.definitions.set(layer.id,layer)}
    getStyle(){return {glyphs:"test-font"}}
    getLayer(id:string){return mock.layers.has(id)}
    moveLayer(){}
    setPaintProperty=mock.paint
    setLayoutProperty(){}
    removeLayer(id:string){mock.layers.delete(id)}
    removeSource(id:string){mock.sources.delete(id)}
    getCanvas(){return {style:{setProperty:vi.fn()}}}
    getBounds(){return {getWest:()=>101,getSouth:()=>2,getEast:()=>102,getNorth:()=>4}}
    queryRenderedFeatures=mock.query
    resize(){} remove(){}
  },
  ScaleControl:class{},
  Popup:class{setLngLat(){return this}setDOMContent(){return this}addTo(){return this}remove(){}},
}))
const feature:SpatialFeature={type:'Feature',id:'stable-id',geometry:{type:'Point',coordinates:[101.5,3.1]},properties:{name:'TEST selection',categories:['warehouse'],source:'test',source_id:'source-id',dataset_id:'synthetic',imported_at:'2026-10-24T00:00:00Z',synthetic:true,boundary_status:'not_applicable',attributes:{}}}
const data:SearchResult={type:'FeatureCollection',features:[feature],meta:{mode:'fixture',crs:'EPSG:4326',total:1,returned:1,offset:0,limit:250,has_more:false,category_counts:{warehouse:1},missing_categories:[],failed_categories:[],warnings:[],attribution:'test'}}
beforeEach(()=>{
  mock.handlers={};mock.sources.clear();mock.layers.clear();mock.definitions.clear();mock.paint.mockClear();mock.query.mockReset()
  useWorkspace.setState({sketches:[],selected:null,tool:'select',visible:categories.map(c=>c.id),order:categories.map(c=>c.id)})
  vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}})
})
afterEach(()=>vi.unstubAllGlobals())
function mount(){
  const view=render(<MapWorkspace data={data} initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}}/>)
  act(()=>mock.handlers['style.load']())
  return view
}
describe('Map and backend interaction',()=>{
  it('selects stable feature identifiers even when renderer IDs differ',()=>{
    mount();mock.query.mockReturnValue([{id:123,properties:{__feature_id:'stable-id'}}])
    act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101.5,lat:3.1}}))
    expect(useWorkspace.getState().selected?.id).toBe('stable-id')
    expect(mock.sources.get('cat-warehouse')?.setData).toHaveBeenCalledWith(expect.objectContaining({features:[expect.objectContaining({properties:expect.objectContaining({__feature_id:'stable-id'})})]}))
  })
  it('submits drawn geometry and displays backend geodesic units',async()=>{
    const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({data:{length_km:111.319,area_sq_km:0}})})
    vi.stubGlobal('fetch',fetch);mount()
    await userEvent.click(screen.getByRole('button',{name:'Measure distance'}))
    act(()=>{mock.handlers.click({lngLat:{lng:0,lat:0}});mock.handlers.click({lngLat:{lng:1,lat:0}})})
    await userEvent.click(screen.getByRole('button',{name:'Finish'}))
    await waitFor(()=>expect(screen.getByText(/111.319 km/)).toBeInTheDocument())
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({geometry:{type:'LineString',coordinates:[[0,0],[1,0]]},crs:'EPSG:4326'})
    expect(fetch.mock.calls[0][0]).toContain('/api/spatial/measure')
    expect(useWorkspace.getState().tool).toBe('select')
  })
})


it('renders provider LineStrings and routes map picks separately from feature selection',()=>{
  const point=vi.fn(),select=vi.fn()
  const view=render(<MapWorkspace data={data} initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}}
    routingResult={routeResult} activeRoute={0} routeStops={[{coordinates:[101,3],label:'A',name:'TEST origin'}]}
    pickingRoutePoint onRoutePoint={point} onRouteSelect={select}/>)
  act(()=>mock.handlers['style.load']())
  expect(mock.sources.get('road-routes')?.setData).toHaveBeenCalledWith(expect.objectContaining({features:[
    expect.objectContaining({geometry:routeResult.routes[0].geometry,properties:{route_index:0,active:true}}),
    expect.objectContaining({geometry:routeResult.routes[1].geometry,properties:{route_index:1,active:false}}),
  ]}))
  act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101.5,lat:3.1}}))
  expect(point).toHaveBeenCalledWith([101.5,3.1])
  expect(useWorkspace.getState().selected).toBeNull()
  view.rerender(<MapWorkspace data={data} initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}}
    routingResult={routeResult} onRouteSelect={select}/>)
  mock.query.mockReturnValue([{properties:{route_index:1}}])
  act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101.5,lat:3.1}}))
  expect(select).toHaveBeenCalledWith(1)
})


it('preserves completed user sketches when switching between GIS and routing maps',()=>{
  const sketch={type:'Feature' as const,id:'test-user-sketch',geometry:{type:'LineString' as const,coordinates:[[101,3],[101.001,3]]},properties:{name:'TEST user sketch',length_km:.111,area_sq_km:0}}
  useWorkspace.getState().setSketches([sketch])
  const first=mount()
  expect(screen.getByRole('button',{name:'Export user sketches'})).toBeEnabled()
  first.unmount()
  mount()
  expect(mock.sources.get('sketch')?.setData).toHaveBeenCalledWith({type:'FeatureCollection',features:[sketch]})
  expect(screen.getByText(/0.111 km/)).toBeInTheDocument()
})

it('renders, selects and removes actual analysis overlay layers',()=>{
 const selected=vi.fn()
 const analysis={id:'analysis-test',color:'#119988',visible:true,result:{type:'FeatureCollection',title:'TEST analysis',features:[{type:'Feature',id:'test-result',geometry:{type:'Point',coordinates:[101.5,3.1]},properties:{name:'TEST result'}}]}} as never
 const view=render(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} analysisLayers={[analysis]} onAnalysisSelect={selected}/>)
 act(()=>mock.handlers['style.load']())
 expect(mock.layers.has('analysis-analysis-test-point')).toBe(true)
 mock.query.mockReturnValue([{id:'test-result',geometry:{type:'Point',coordinates:[101.5,3.1]},properties:{name:'TEST result'}}])
 act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101.5,lat:3.1}}))
 expect(selected).toHaveBeenCalledWith(expect.objectContaining({id:'test-result',properties:{name:'TEST result'}}))
 view.rerender(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} analysisLayers={[]}/>)
 expect(mock.sources.has('analysis-analysis-test')).toBe(false)
})

it('renders optimization road geometry, stop labels and stable vehicle selection',()=>{
  const select=vi.fn()
  const fc={type:'FeatureCollection' as const,features:[{type:'Feature' as const,id:'v1',geometry:{type:'MultiLineString' as const,coordinates:[[[101,3],[101.02,3.01],[101.1,3.02]]]},properties:{vehicle_id:'v1',vehicle:'TEST vehicle',color:'#087f80'}}]}
  const view=render(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} optimizationData={fc} onOptimizationSelect={select}/>)
  act(()=>mock.handlers['style.load']())
  expect(mock.sources.get('optimization')?.setData).toHaveBeenCalledWith(fc)
  expect(mock.layers.has('optimization-arrows')).toBe(true)
  expect(mock.layers.has('optimization-labels')).toBe(true)
  mock.query.mockReturnValue([fc.features[0]])
  act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101,lat:3}}))
  expect(select).toHaveBeenCalledWith(expect.objectContaining({properties:expect.objectContaining({vehicle_id:'v1'})}))
  view.rerender(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} optimizationData={{type:'FeatureCollection',features:[]}}/>)
  expect(mock.sources.get('optimization')?.setData).toHaveBeenLastCalledWith({type:'FeatureCollection',features:[]})
})


it('validates comparison dash/offset styles against installed MapLibre spec and selects namespaced routes',()=>{
 const fixture=comparisonFixture(),state=makeOverlay(fixture.comparison,fixture.response),fc=comparisonGeoJSON(state),select=vi.fn()
 const key=routeKey(fixture.response.items[1],'same-vehicle')
 render(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} optimizationData={fc} selectedOptimizationVehicle={key} onOptimizationSelect={select}/>)
 act(()=>mock.handlers['style.load']())
 const layers=[...mock.definitions.values()].filter(x=>'source' in x&&x.source==='optimization')
 expect(validateStyleMin({version:8,glyphs:'https://example.test/{fontstack}/{range}.pbf',sources:{optimization:{type:'geojson',data:fc}},layers})).toEqual([])
 expect(mock.paint).toHaveBeenCalledWith('optimization-lines','line-width',['case',['==',['get','vehicle_id'],key],6,3])
 mock.query.mockReturnValue([fc.features[4]])
 act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101,lat:3}}))
 expect(select).toHaveBeenCalledWith(expect.objectContaining({properties:expect.objectContaining({vehicle_id:key,scenario_id:'scenario-2'})}))
})


it('renders candidate point/polygon scores with valid MapLibre styles and selects original candidate IDs',async()=>{
 const {siteFixture}=await import('../test/site-fixture');const {siteDisplay}=await import('../services/sites');const fc=siteDisplay(siteFixture()),select=vi.fn()
 const view=render(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} siteData={fc} selectedSite="test-polygon" onSiteSelect={select}/>)
 act(()=>mock.handlers['style.load']())
 const layers=[...mock.definitions.values()].filter(x=>'source' in x&&x.source==='site-suitability')
 expect(validateStyleMin({version:8,glyphs:'https://example.test/{fontstack}/{range}.pbf',sources:{'site-suitability':{type:'geojson',data:fc}},layers})).toEqual([])
 expect(mock.sources.get('site-suitability')?.setData).toHaveBeenCalledWith(fc)
 mock.query.mockReturnValue([fc.features[2]])
 act(()=>mock.handlers.click({point:{x:100,y:100},lngLat:{lng:101.505,lat:3.105}}))
 expect(select).toHaveBeenCalledWith(expect.objectContaining({properties:expect.objectContaining({candidate_id:'test-polygon'})}))
 view.rerender(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} siteData={{type:'FeatureCollection',features:[]}}/>)
 expect(mock.sources.get('site-suitability')?.setData).toHaveBeenLastCalledWith({type:'FeatureCollection',features:[]})
})


it('renders GeoAI measured top features and selected geometry with valid highlight styles',()=>{
 const fc={type:'FeatureCollection' as const,features:[{type:'Feature' as const,id:'geo-result::source',geometry:{type:'Point' as const,coordinates:[101.5,3.1]},properties:{name:'Mapped warehouse',__original_id:'source',top_accessible:true}}]}
 const view=render(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}} geoaiSelection={fc.features[0]} geoaiTop={fc}/>)
 act(()=>mock.handlers['style.load']())
 for(const source of ['geoai-highlight','geoai-top']){
  const layers=[...mock.definitions.values()].filter(x=>'source' in x&&x.source===source)
  expect(validateStyleMin({version:8,sources:{[source]:{type:'geojson',data:fc}},layers})).toEqual([])
  expect(mock.sources.get(source)?.setData).toHaveBeenCalledWith(fc)
 }
 view.rerender(<MapWorkspace initialBbox={[101,2,102,4]} onViewport={()=>{}} onLog={()=>{}}/>)
 expect(mock.sources.get('geoai-highlight')?.setData).toHaveBeenLastCalledWith({type:'FeatureCollection',features:[]})
})
