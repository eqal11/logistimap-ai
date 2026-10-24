import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {beforeEach,afterEach,it,expect,vi} from 'vitest'
import {LogisticsOptimization} from './LogisticsOptimization'
import {comparisonFixture,resultFixture} from '../test/comparison-fixture'
import {useOptimization} from '../store/optimization'
import {newScenario} from '../services/optimization'
import type {FeatureCollection,Feature} from 'geojson'
const api=vi.hoisted(()=>({history:vi.fn(),get:vi.fn(),solutions:vi.fn(),create:vi.fn(),scenarios:vi.fn()}))
vi.mock('../services/comparisons',async original=>({...await original<typeof import('../services/comparisons')>(),listComparisons:api.history,getComparison:api.get,getComparisonSolutions:api.solutions,createComparison:api.create}))
vi.mock('../services/optimization',async original=>({...await original<typeof import('../services/optimization')>(),listScenarios:api.scenarios}))
vi.mock('./MapWorkspace',()=>({MapWorkspace:({optimizationData,onOptimizationSelect}:{optimizationData:FeatureCollection;onOptimizationSelect:(f:Feature)=>void})=><div role="region" aria-label="Test map"><output data-testid="map-features">{JSON.stringify(optimizationData)}</output><button onClick={()=>{const f=optimizationData.features.find(f=>f.properties?.scenario_id==='scenario-2');if(f)onOptimizationSelect(f)}}>Test select second solution</button></div>}))
beforeEach(()=>{
 vi.clearAllMocks();vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}})
 useOptimization.setState({scenario:newScenario(),result:null,savedId:null,jobId:null,jobScenarioId:null})
 const f=comparisonFixture()
 api.history.mockResolvedValue({items:[{id:f.comparison.id,name:f.comparison.name,created_at:f.comparison.created_at,scenario_count:2,schema_version:2}],total:1,limit:10,offset:0})
 api.get.mockResolvedValue(f.comparison);api.solutions.mockResolvedValue(f.response);api.create.mockResolvedValue(f.comparison)
 api.scenarios.mockResolvedValue({items:f.comparison.rows.map(r=>({id:r.scenario_id,name:r.name,summary:{assigned_stops:1},status:'best_found',stops:1})),total:2})
})
afterEach(()=>vi.unstubAllGlobals())
async function mount(){
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><LogisticsOptimization onLog={()=>{}}/></QueryClientProvider>)
 await userEvent.click(screen.getByRole('button',{name:'Comparison'}))
}
const features=()=>JSON.parse(screen.getByTestId('map-features').textContent!).features
it('reopens a pinned comparison, shows both solutions and selects the exact scenario vehicle',async()=>{
 await mount();await userEvent.click(await screen.findByRole('button',{name:'Open comparison TEST pinned comparison'}))
 await screen.findByRole('heading',{name:'Comparison map legend'})
 expect(features()).toHaveLength(8)
 await userEvent.click(screen.getByRole('button',{name:'Test select second solution'}))
 expect(screen.getByRole('heading',{name:'TEST two · Vehicle 1 · ordered schedule'})).toBeInTheDocument()
 expect(api.solutions).toHaveBeenCalledWith('comparison-1')
 await userEvent.click(screen.getByRole('checkbox',{name:'Show scenario B: TEST two'}))
 expect(features()).toHaveLength(4);expect(features().every((f:Feature)=>f.properties?.scenario_id==='scenario-1')).toBe(true)
 await userEvent.click(screen.getByRole('checkbox',{name:'Show A · Vehicle 1'}))
 expect(features()).toHaveLength(0)
 await userEvent.click(screen.getByRole('button',{name:'Inspect B · Vehicle 1'}))
 expect(features()).toHaveLength(4);expect(features()[0].properties.scenario_id).toBe('scenario-2')
 expect(screen.getByRole('button',{name:'Fit selected route'})).toBeInTheDocument()
})
it('creates and persists comparison from selected solved snapshots without rerouting',async()=>{
 await mount();await userEvent.click(screen.getByText('Create comparison from saved solutions'))
 await userEvent.click(await screen.findByRole('checkbox',{name:'Compare TEST one'}))
 await userEvent.click(screen.getByRole('checkbox',{name:'Compare TEST two'}))
 await userEvent.click(screen.getByRole('button',{name:'Save comparison 2/4'}))
 await screen.findByRole('heading',{name:'Comparison map legend'})
 expect(api.create).toHaveBeenCalledWith(['scenario-1','scenario-2'],'Fleet / scenario comparison')
 expect(features()).toHaveLength(8)
})
it('retains summary but clears geometry when historical solution retrieval fails',async()=>{
 const previous=resultFixture();useOptimization.setState({scenario:previous.scenario,result:previous,savedId:'previous-scenario'})
 api.solutions.mockRejectedValue(new Error('Exact historical solution unavailable; no substitute'))
 await mount();await userEvent.click(screen.getByRole('button',{name:'Results'}));await userEvent.click(screen.getByText('Matrix provenance & cells'));await userEvent.click(screen.getByRole('button',{name:'Show matrix cells'}));await userEvent.click(screen.getByRole('button',{name:'Comparison'}));await userEvent.click(await screen.findByRole('button',{name:'Open comparison TEST pinned comparison'}))
 expect(screen.queryByRole('heading',{name:'Asymmetric road matrix · metres / seconds'})).not.toBeInTheDocument()
 expect(await screen.findByRole('alert')).toHaveTextContent('no substitute')
 expect(screen.getByRole('region',{name:'Comparison results'})).toBeInTheDocument()
 expect(features()).toHaveLength(0)
 expect(screen.queryByRole('heading',{name:'Comparison map legend'})).not.toBeInTheDocument()
})
it('uses real download actions for visible GeoJSON and CSV snapshots',async()=>{
 const blobs:Blob[]=[];vi.stubGlobal('URL',{createObjectURL:vi.fn((b:Blob)=>{blobs.push(b);return 'blob:test'}),revokeObjectURL:vi.fn()})
 const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
 await mount();await userEvent.click(await screen.findByRole('button',{name:'Open comparison TEST pinned comparison'}))
 await screen.findByRole('heading',{name:'Comparison map legend'})
 await userEvent.click(screen.getByRole('button',{name:'GeoJSON visible comparison'}))
 await userEvent.click(screen.getByRole('button',{name:'CSV comparison'}))
 expect(blobs).toHaveLength(2);expect(blobs[0].type).toBe('application/geo+json');expect(blobs[1].type).toContain('text/csv')
 expect(click).toHaveBeenCalledTimes(2);click.mockRestore()
})
