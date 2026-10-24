import {forwardRef,useImperativeHandle} from 'react'
import {render,screen,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {beforeEach,it,expect,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {AdvancedWorkspace} from './AdvancedWorkspace'
import {useAnalyses} from '../store/analytics'
import {analyze,getHistory,openSaved,saveAnalysis,archiveSaved,exportCSV,type AnalysisResult} from '../services/analytics'
import {downloadGeoJSON} from '../services/api'
vi.mock('./MapWorkspace',()=>({MapWorkspace:forwardRef(function Stub(_props,ref){useImperativeHandle(ref,()=>({fit:vi.fn()}));return <div>Test map stub</div>})}))
vi.mock('./AnalysisLayerPicker',()=>({AnalysisLayerPicker:({label}:{label:string})=><div>{label} input test stub</div>}))
vi.mock('recharts',()=>({BarChart:()=>null,Bar:()=>null,XAxis:()=>null,YAxis:()=>null,Tooltip:()=>null,ResponsiveContainer:()=>null}))
vi.mock('../services/analytics',async original=>({...await original<typeof import('../services/analytics')>(),analyze:vi.fn(),getHistory:vi.fn(),openSaved:vi.fn(),saveAnalysis:vi.fn(),archiveSaved:vi.fn(),exportCSV:vi.fn()}))
vi.mock('../services/api',async original=>({...await original<typeof import('../services/api')>(),downloadGeoJSON:vi.fn()}))
const result:AnalysisResult={type:'FeatureCollection',title:'TEST buffer',operation:'buffer',features:[{type:'Feature',id:'test',geometry:{type:'Point',coordinates:[101,3]},properties:{name:'TEST geometry'}}],rows:[{id:'test',count:2}],statistics:{output_features:1},parameters:{distance_m:1000},inputs:{source:'TEST ONLY'},status:'completed',executed_at:'2026-10-24T00:00:00Z',crs:'EPSG:4326',attribution:'TEST ONLY',warnings:['TEST ONLY'],calculation_id:'a'.repeat(64)}
beforeEach(()=>{vi.clearAllMocks();useAnalyses.setState({layers:[],activeId:null});vi.mocked(analyze).mockResolvedValue(result);vi.mocked(saveAnalysis).mockResolvedValue({id:'saved-test'});vi.mocked(getHistory).mockResolvedValue({items:[{id:'route-test',title:'TEST saved route',distance_m:1000,duration_s:120,created_at:'2026-10-24'}],total:1,limit:25,offset:0});vi.mocked(openSaved).mockResolvedValue({...result,operation:'saved_route',saved_id:'route-test'});vi.mocked(archiveSaved).mockResolvedValue({id:'route-test',status:'archived'})})
function mount(module='toolbox'){const q=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});return render(<QueryClientProvider client={q}><AdvancedWorkspace module={module} onLog={()=>{}}/></QueryClientProvider>)}
it('runs actual API adapter with meter conversion, exports and saves server ID',async()=>{
 mount();await userEvent.clear(screen.getByRole('spinbutton',{name:'Buffer distance'}));await userEvent.type(screen.getByRole('spinbutton',{name:'Buffer distance'}),'2')
 await userEvent.click(screen.getByRole('button',{name:'Run spatial analysis'}));await screen.findByRole('button',{name:'Export result GeoJSON'})
 expect(vi.mocked(analyze).mock.calls[0][0]).toMatchObject({operation:'buffer',distance_m:2000,crs:'EPSG:4326'})
 await userEvent.click(screen.getByRole('button',{name:'Export result GeoJSON'}));expect(downloadGeoJSON).toHaveBeenCalledWith(result,'logistimap-buffer.geojson')
 await userEvent.click(screen.getByRole('button',{name:'Download CSV statistics'}));expect(exportCSV).toHaveBeenCalledWith(result)
 await userEvent.click(screen.getByRole('button',{name:'Save analysis to PostGIS'}));expect(saveAnalysis).toHaveBeenCalledWith('a'.repeat(64))
 expect(await screen.findByRole('status')).toHaveTextContent('Saved analysis to PostGIS')
})
it('exposes empty results honestly and toggles actual result layers',async()=>{
 vi.mocked(analyze).mockResolvedValue({...result,features:[],rows:[]});mount()
 await userEvent.click(screen.getByRole('button',{name:'Run spatial analysis'}))
 expect(await screen.findByText(/No result geometry/)).toBeInTheDocument()
 const show=screen.getByRole('checkbox',{name:'Show TEST buffer'});await userEvent.click(show)
 expect(useAnalyses.getState().layers[0].visible).toBe(false)
})
it('handles API errors without adding a fake layer',async()=>{
 vi.mocked(analyze).mockRejectedValue(new Error('Invalid geometry'));mount()
 await userEvent.click(screen.getByRole('button',{name:'Run spatial analysis'}))
 expect(await screen.findByRole('alert')).toHaveTextContent('Invalid geometry')
 expect(useAnalyses.getState().layers).toHaveLength(0)
})
it('opens saved Phase 3 routes and requires explicit deletion confirmation',async()=>{
 mount('route-history');await userEvent.click(await screen.findByRole('button',{name:'Open saved route'}))
 await waitFor(()=>expect(openSaved).toHaveBeenCalledWith('routes','route-test',expect.any(AbortSignal)))
 await userEvent.click(screen.getByRole('button',{name:'Delete'}));expect(archiveSaved).not.toHaveBeenCalled()
 await userEvent.click(screen.getByRole('button',{name:'Cancel deletion'}));expect(archiveSaved).not.toHaveBeenCalled()
 await userEvent.click(screen.getByRole('button',{name:'Delete'}));await userEvent.click(screen.getByRole('button',{name:'Confirm delete'}))
 expect(archiveSaved).toHaveBeenCalledWith('routes','route-test')
})
it('marks isochrones unsupported and requires matrix references',()=>{
 mount('accessibility');expect(screen.getByText('Network isochrones unavailable')).toBeInTheDocument()
 expect(screen.getByRole('button',{name:'Calculate road matrix'})).toBeDisabled()
})
it('provides configurable DBSCAN without claiming statistical significance',()=>{
 mount('clusters');expect(screen.getByRole('spinbutton',{name:'DBSCAN epsilon meters'})).toHaveValue(1000)
 expect(screen.getByText(/DBSCAN is descriptive, not a significance test/)).toBeInTheDocument()
})
