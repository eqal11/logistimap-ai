import {render,screen,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {SiteSelection} from './SiteSelection'
import {siteFixture} from '../test/site-fixture'
import type {FeatureCollection} from 'geojson'
const api=vi.hoisted(()=>({catalog:vi.fn(),prepare:vi.fn(),evaluate:vi.fn(),ahp:vi.fn(),history:vi.fn(),open:vi.fn(),save:vi.fn()}))
vi.mock('../services/sites',async original=>({...await original<typeof import('../services/sites')>(),siteCatalog:api.catalog,prepareSites:api.prepare,evaluateSites:api.evaluate,checkAHP:api.ahp,siteHistory:api.history,openSite:api.open,saveSites:api.save}))
vi.mock('./MapWorkspace',()=>({MapWorkspace:({siteData,pickingRoutePoint,onRoutePoint}:{siteData:FeatureCollection;pickingRoutePoint:boolean;onRoutePoint:(p:[number,number])=>void})=><div aria-label="TEST site map"><output data-testid="site-map-data">{JSON.stringify(siteData)}</output>{pickingRoutePoint&&<button onClick={()=>onRoutePoint([101.5,3.1])}>TEST click coordinate</button>}</div>}))
vi.mock('./LogisticsLocationPicker',()=>({LogisticsLocationPicker:()=> <div>TEST target picker</div>}))
beforeEach(()=>{
 vi.clearAllMocks();vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}})
 api.catalog.mockResolvedValue({criteria:[...['road_distance_m','warehouse_distance_m','industrial_count'].map(id=>({id,label:id,unit:'TEST units',direction:id==='industrial_count'?'benefit':'cost',availability:'gis',description:'TEST mapped proxy'})),{id:'flood_risk',label:'Flood hazard',unit:'user score',direction:'cost',availability:'unavailable',description:'No official dataset'}]})
 api.prepare.mockImplementation(async s=>siteFixture(s));api.evaluate.mockImplementation(async s=>siteFixture(s))
 api.ahp.mockResolvedValue({weights:[1/3,1/3,1/3],lambda_max:3,ci:0,ri:.58,cr:0,consistent:true,threshold:.1})
 api.history.mockResolvedValue({items:[],total:0});api.save.mockResolvedValue({id:'saved-eval',status:'saved'})
})
afterEach(()=>vi.unstubAllGlobals())
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><SiteSelection onLog={()=>{}}/></QueryClientProvider>)}
async function addPoint(){await userEvent.click(screen.getByRole('button',{name:'Add point on map'}));await userEvent.click(screen.getByRole('button',{name:'TEST click coordinate'}))}
it('starts empty and requires actual user/GIS candidate input',()=>{mount();expect(screen.getByRole('button',{name:'Evaluate candidates'})).toBeDisabled();expect(screen.getByText(/No candidate sites yet/)).toBeInTheDocument()})
it('evaluates a user-selected point and invalidates old ranking after a weight edit',async()=>{
 mount();await addPoint();await userEvent.click(screen.getByRole('button',{name:'Evaluate candidates'}))
 expect(await screen.findByRole('heading',{name:'Weight sensitivity ±20%'})).toBeInTheDocument()
 expect(api.evaluate.mock.calls[0][0].candidates[0].kind).toBe('hypothetical_site')
 await userEvent.click(screen.getByRole('button',{name:'Criteria & AHP'}));await userEvent.clear(await screen.findByRole('spinbutton',{name:'Weight road_distance_m'}));await userEvent.type(screen.getByRole('spinbutton',{name:'Weight road_distance_m'}),'3')
 expect(screen.queryByRole('heading',{name:'Weight sensitivity ±20%'})).not.toBeInTheDocument()
 await userEvent.click(screen.getByRole('button',{name:'Evaluate candidates'}));await screen.findByRole('heading',{name:'Weight sensitivity ±20%'})
 expect(api.evaluate.mock.calls.at(-1)![0].criteria[0].weight).toBe(3)
})
it('creates reciprocal pairwise judgments and requests CR without generating spatial results',async()=>{
 mount();await userEvent.click(screen.getByRole('button',{name:'Criteria & AHP'}))
 await userEvent.selectOptions(screen.getByRole('combobox',{name:'Site weighting method'}),'ahp')
 await userEvent.selectOptions(await screen.findByRole('combobox',{name:'Compare road_distance_m to warehouse_distance_m'}),'3')
 await userEvent.click(screen.getByRole('button',{name:'Check AHP consistency'}))
 await waitFor(()=>expect(api.ahp).toHaveBeenCalledWith([[1,3,1],[1/3,1,1],[1,1,1]]))
 expect(screen.getByText(/CR 0.0000/)).toBeInTheDocument();expect(api.evaluate).not.toHaveBeenCalled()
})
it('marks missing official flood data user-supplied and never inserts zero from a note alone',async()=>{
 mount();await addPoint();await userEvent.click(screen.getByRole('button',{name:'Criteria & AHP'}))
 await userEvent.click(await screen.findByRole('checkbox',{name:'Use criterion Flood hazard'}))
 expect(screen.getByRole('combobox',{name:'Criterion source flood_risk'})).toHaveValue('user')
 const note=screen.getByRole('textbox',{name:/Value note .* flood_risk/});await userEvent.type(note,'Hypothetical risk assumption')
 await userEvent.click(screen.getByRole('button',{name:'Prepare values'}))
 await waitFor(()=>expect(api.prepare).toHaveBeenCalled());expect(api.prepare.mock.calls[0][0].candidates[0].values.flood_risk).toBeUndefined()
})
it('reloads saved parameters/results and handles failure without fabricating scores',async()=>{
 const r=siteFixture();api.history.mockResolvedValue({items:[{id:'saved',name:r.title,method:'wlc',created_at:r.executed_at}],total:1});api.open.mockResolvedValue({...r,saved_id:'saved'})
 mount();await userEvent.click(screen.getByRole('button',{name:'Saved evaluations'}));await userEvent.click(await screen.findByRole('button',{name:'Open '+r.title}))
 expect(await screen.findByRole('button',{name:'Saved to PostGIS'})).toBeDisabled()
 api.evaluate.mockRejectedValue(new Error('Provider unavailable; no substitute'))
 await userEvent.click(screen.getByRole('button',{name:'Criteria & AHP'}));await userEvent.clear(await screen.findByRole('spinbutton',{name:'Weight road_distance_m'}))
 await userEvent.click(screen.getByRole('button',{name:'Evaluate candidates'}))
 expect(await screen.findByRole('alert')).toHaveTextContent('no substitute')
 expect(screen.queryByRole('heading',{name:'Weight sensitivity ±20%'})).not.toBeInTheDocument()
})
