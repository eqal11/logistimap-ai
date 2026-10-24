import { forwardRef, useImperativeHandle } from 'react'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { FreightRoutePlanner } from './FreightRoutePlanner'
import { useRouting } from '../store/routing'
import { calculateRoute, findRoutingFacilities, getFeatureAnchor, getNearestWarehouse, getRoutingProvider, saveRoute } from '../services/routing'
import { resolveLocation } from '../services/discovery'
import { downloadGeoJSON, searchFeatures } from '../services/api'
import { result } from '../test/route-fixture'
import type { Coordinate } from '../types/routing'
vi.mock('./MapWorkspace',()=>({MapWorkspace:forwardRef(function Stub(props:{onRoutePoint?:(c:Coordinate)=>void;pickingRoutePoint?:boolean},ref){
  useImperativeHandle(ref,()=>({fit:vi.fn()}))
  return <div aria-label="Routing map test stub"><button onClick={()=>props.onRoutePoint?.([101.5,3.1])}>Test map point</button><span>{props.pickingRoutePoint?'Map picking active':'Map picking inactive'}</span></div>
})}))
vi.mock('../services/routing',async original=>({...await original<typeof import('../services/routing')>(),calculateRoute:vi.fn(),getRoutingProvider:vi.fn(),findRoutingFacilities:vi.fn(),getFeatureAnchor:vi.fn(),getNearestWarehouse:vi.fn(),saveRoute:vi.fn()}))
vi.mock('../services/discovery',()=>({resolveLocation:vi.fn()}))
vi.mock('../services/api',async original=>({...await original<typeof import('../services/api')>(),searchFeatures:vi.fn(),downloadGeoJSON:vi.fn()}))
const empty={type:'FeatureCollection' as const,features:[],meta:{mode:'postgis' as const,crs:'EPSG:4326' as const,total:0,returned:0,limit:250,offset:0,has_more:false,category_counts:{},missing_categories:[],failed_categories:[],warnings:[],attribution:'TEST'}}
beforeEach(()=>{
  vi.clearAllMocks();useRouting.getState().reset()
  HTMLElement.prototype.scrollIntoView=vi.fn()
  vi.mocked(getRoutingProvider).mockResolvedValue({provider:'TEST OSRM',configured:true,profile:'car',heavy_vehicle_verified:false,last_success_at:null,last_failure:null,cooldown_seconds:0,limitations:[],policy_url:'https://routing.openstreetmap.de/about.html',fix_map_url:'https://www.openstreetmap.org/fixthemap'})
  vi.mocked(searchFeatures).mockResolvedValue(empty)
  vi.mocked(calculateRoute).mockResolvedValue(result)
  vi.mocked(saveRoute).mockResolvedValue({id:'saved-test-route',status:'saved'})
})
function mount(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  render(<QueryClientProvider client={client}><FreightRoutePlanner mode="postgis" onLog={()=>{}}/></QueryClientProvider>)
}
function points(){
  useRouting.getState().setPoint('origin',{coordinates:[101,3],label:'TEST origin'})
  useRouting.getState().setPoint('destination',{coordinates:[101.002,3],label:'TEST destination'})
}
it('requires every selected stop and labels car/truck limitations',async()=>{
  mount()
  await userEvent.click(screen.getByRole('button',{name:'Calculate road route'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Choose all stops')
  expect(calculateRoute).not.toHaveBeenCalled()
  expect(screen.getByText(/Truck restrictions, vehicle height/)).toBeInTheDocument()
  expect(screen.getByRole('combobox',{name:'Routing vehicle profile'})).toBeDisabled()
})
it('uses explicit place search and map clicks as route references',async()=>{
  vi.mocked(resolveLocation).mockResolvedValue({matches:[{name:'TEST town',center:[101,3],bbox:[100.9,2.9,101.1,3.1],source_id:'node/TEST',type:'town'}],cached:false,attribution:'TEST'})
  mount()
  await userEvent.type(screen.getByRole('textbox',{name:'Search origin name or coordinates'}),'TEST town')
  expect(resolveLocation).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button',{name:'Search origin'}))
  await userEvent.click(await screen.findByText('TEST town',{exact:true}))
  expect(useRouting.getState().stops[0].point?.coordinates).toEqual([101,3])
  await userEvent.click(screen.getByRole('button',{name:'Pick destination on map'}))
  expect(screen.getByText('Map picking active')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button',{name:'Test map point'}))
  expect(useRouting.getState().stops.at(-1)?.point?.coordinates).toEqual([101.5,3.1])
  expect(screen.getByText('Map picking inactive')).toBeInTheDocument()
})
it('calculates, compares, exports the chosen alternative and saves its server reference',async()=>{
  points();mount()
  await userEvent.click(screen.getByRole('button',{name:'Calculate road route'}))
  expect(await screen.findByRole('button',{name:'Select route 1'})).toHaveAttribute('aria-pressed','true')
  await userEvent.click(screen.getByRole('button',{name:'Select route 2'}))
  expect(useRouting.getState().activeRoute).toBe(1)
  await userEvent.click(screen.getByRole('button',{name:'Export selected route'}))
  expect(vi.mocked(downloadGeoJSON).mock.calls[0][0]).toMatchObject({features:[expect.objectContaining({geometry:result.routes[1].geometry,properties:expect.objectContaining({duration_s:150})}),expect.anything(),expect.anything(),expect.anything(),expect.anything()]})
  await userEvent.click(screen.getByRole('button',{name:'Save selected to PostGIS'}))
  await waitFor(()=>expect(saveRoute).toHaveBeenCalledWith(result,1))
  expect(await screen.findByText(/Saved to PostGIS/)).toBeInTheDocument()
})
it('keeps provider failures visible and never generates a substitute route',async()=>{
  vi.mocked(calculateRoute).mockRejectedValue(new Error('No road route found between these stops.'))
  points();mount()
  await userEvent.click(screen.getByRole('button',{name:'Calculate road route'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('No road route found')
  expect(screen.queryByRole('button',{name:'Export selected route'})).not.toBeInTheDocument()
  expect(useRouting.getState().result).toBeNull()
})
it('selects imported features through server-resolved anchors and finds a geographic warehouse',async()=>{
  const feature={type:'Feature' as const,id:'00000000-0000-0000-0000-000000000001',geometry:{type:'Point' as const,coordinates:[101,3]},properties:{name:'TEST imported facility',categories:['industrial' as const],source:'TEST',source_id:'node/TEST',dataset_id:'TEST',imported_at:'TEST',synthetic:false,boundary_status:'unverified',attributes:{}}}
  vi.mocked(findRoutingFacilities).mockResolvedValue({...empty,features:[feature],meta:{...empty.meta,total:1,returned:1}})
  vi.mocked(getFeatureAnchor).mockResolvedValue({feature_id:feature.id,coordinates:[101,3],label:feature.properties.name,source_id:'node/TEST',anchor_method:'source_point'})
  vi.mocked(getNearestWarehouse).mockResolvedValue({feature_id:'00000000-0000-0000-0000-000000000002',coordinates:[101.002,3],label:'TEST nearest warehouse',geographic_distance_m:500,method:'geographic'})
  mount()
  await userEvent.click(screen.getAllByRole('button',{name:'Imported GIS'})[0])
  await userEvent.type(screen.getByRole('textbox',{name:'Search origin name or coordinates'}),'TEST imported')
  await userEvent.click(screen.getByRole('button',{name:'Search origin'}))
  await userEvent.click(await screen.findByText('TEST imported facility',{exact:true}))
  expect(useRouting.getState().stops[0].point?.feature_id).toBe(feature.id)
  await userEvent.click(screen.getByRole('button',{name:/Closest mapped warehouse/}))
  await waitFor(()=>expect(useRouting.getState().stops.at(-1)?.point?.label).toBe('TEST nearest warehouse'))
  expect(screen.getByText(/Driving proximity has not been ranked/)).toBeInTheDocument()
})
it('ignores a stale response after a waypoint is edited',async()=>{
  let finish:(value:typeof result)=>void=()=>{}
  vi.mocked(calculateRoute).mockReturnValue(new Promise(resolve=>{finish=resolve}))
  points();mount()
  await userEvent.click(screen.getByRole('button',{name:'Calculate road route'}))
  act(()=>useRouting.getState().setPoint('origin',{coordinates:[101.01,3],label:'Changed origin'}))
  await act(async()=>{finish(result)})
  expect(useRouting.getState().result).toBeNull()
  expect(screen.queryByRole('button',{name:'Export selected route'})).not.toBeInTheDocument()
})

it('does not attach a save receipt to a different selected route',async()=>{
  let finish:(value:{id:string;status:string})=>void=()=>{}
  vi.mocked(saveRoute).mockReturnValue(new Promise(resolve=>{finish=resolve}))
  points();mount()
  await userEvent.click(screen.getByRole('button',{name:'Calculate road route'}))
  await screen.findByRole('button',{name:'Select route 1'})
  await userEvent.click(screen.getByRole('button',{name:'Save selected to PostGIS'}))
  await userEvent.click(screen.getByRole('button',{name:'Select route 2'}))
  await act(async()=>{finish({id:'saved-old-route',status:'saved'})})
  expect(screen.queryByText(/Saved to PostGIS/)).not.toBeInTheDocument()
})
it('ignores a nearest warehouse lookup after the origin changes',async()=>{
  let finish:(value:Awaited<ReturnType<typeof getNearestWarehouse>>)=>void=()=>{}
  vi.mocked(getNearestWarehouse).mockReturnValue(new Promise(resolve=>{finish=resolve}))
  points()
  useRouting.getState().setPoint('origin',{feature_id:'00000000-0000-0000-0000-000000000001',coordinates:[101,3],label:'TEST facility'})
  mount()
  await userEvent.click(screen.getByRole('button',{name:/Closest mapped warehouse/}))
  act(()=>useRouting.getState().setPoint('origin',{coordinates:[102,3],label:'Changed origin'}))
  await act(async()=>{finish({coordinates:[101.002,3],label:'Stale warehouse',geographic_distance_m:500,method:'geographic'})})
  expect(useRouting.getState().stops.at(-1)?.point?.label).toBe('TEST destination')
})
