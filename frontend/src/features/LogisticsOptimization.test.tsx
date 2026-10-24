import {render,screen,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {beforeEach,describe,it,expect,vi} from 'vitest'
import {LogisticsOptimization} from './LogisticsOptimization'
import {useOptimization} from '../store/optimization'
import {newScenario} from '../services/optimization'
const api=vi.hoisted(()=>({save:vi.fn(),list:vi.fn(),open:vi.fn(),results:vi.fn(),start:vi.fn(),job:vi.fn()}))
vi.mock('../services/optimization',async original=>({...await original<typeof import('../services/optimization')>(),saveScenario:api.save,listScenarios:api.list,openScenario:api.open,getResults:api.results,startSolve:api.start,getJob:api.job}))
vi.mock('./MapWorkspace',()=>({MapWorkspace:()=> <div role="region" aria-label="Test map"/>}))
vi.mock('./LogisticsLocationPicker',()=>({LogisticsLocationPicker:({onAdd}:{onAdd:(p:object)=>void})=><button onClick={()=>onAdd({coordinates:[101.5,3.1],label:'TEST warehouse',feature_id:'test-feature',source_id:'way/123'})}>Add test GIS candidate</button>}))
beforeEach(()=>{useOptimization.setState({scenario:newScenario(),result:null,savedId:null,jobId:null,jobScenarioId:null});vi.clearAllMocks();api.list.mockResolvedValue({items:[],total:0})})
function mount(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><LogisticsOptimization onLog={()=>{}}/></QueryClientProvider>)}
describe('logistics scenario workflow',()=>{
 it('shows honest empty state and prevents empty solve',async()=>{mount();await userEvent.click(screen.getByRole('button',{name:'Optimize routes'}));expect(await screen.findByRole('alert')).toHaveTextContent('Add a depot');expect(api.start).not.toHaveBeenCalled()})
 it('adds a selected GIS depot with source ID and editable assumed vehicle',async()=>{mount();await userEvent.click(screen.getByRole('button',{name:'Add test GIS candidate'}));const s=useOptimization.getState().scenario;expect(s.depots[0].source_id).toBe('way/123');expect(s.vehicles[0].capacity).toBe(10);expect(s.vehicles[0].cost_per_km).toBe(0)})
 it('edits fleet capacity and disables availability',async()=>{mount();await userEvent.click(screen.getByRole('button',{name:'Add test GIS candidate'}));await userEvent.click(screen.getByRole('button',{name:'Fleet'}));const capacity=screen.getByRole('spinbutton',{name:'Capacity'});await userEvent.clear(capacity);await userEvent.type(capacity,'25');expect(useOptimization.getState().scenario.vehicles[0].capacity).toBe(25);await userEvent.click(screen.getByRole('checkbox',{name:'Vehicle available'}));expect(useOptimization.getState().scenario.vehicles[0].enabled).toBe(false)})
 it('shows API errors without losing scenario inputs',async()=>{const s=newScenario();s.depots=[{id:'d',name:'TEST depot',coordinates:[101,3],window:[0,86400]}];s.vehicles=[{id:'v',name:'TEST',capacity:10,start_depot:'d',end_depot:'d'}] as typeof s.vehicles;s.stops=[{id:'s',name:'TEST candidate',coordinates:[101.1,3],demand:1}] as typeof s.stops;useOptimization.setState({scenario:s});api.save.mockRejectedValue(new Error('Provider unavailable'));mount();await userEvent.click(screen.getByRole('button',{name:'Save scenario'}));expect(await screen.findByRole('alert')).toHaveTextContent('Provider unavailable');expect(useOptimization.getState().scenario.stops).toHaveLength(1)})
 it('loads empty saved list with no fake scenarios',async()=>{mount();await userEvent.click(screen.getByRole('button',{name:'Saved Scenarios'}));await waitFor(()=>expect(screen.getByText('No saved scenarios in this list.')).toBeInTheDocument())})
 it('editing assumptions invalidates old saved identity and result',async()=>{useOptimization.setState({savedId:'old-id'});mount();await userEvent.clear(screen.getByRole('textbox',{name:'Scenario name'}));await userEvent.type(screen.getByRole('textbox',{name:'Scenario name'}),'New assumptions');expect(useOptimization.getState().savedId).toBeNull()})
})
