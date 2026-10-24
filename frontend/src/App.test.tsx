import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { getHealth, searchFeatures, searchMapFeatures } from './services/api'

vi.mock('./features/GeoAICopilot',()=>({GeoAICopilot:()=> <div aria-label="GeoAI Copilot test stub"/>}))
vi.mock('./features/FreightRoutePlanner',()=>({FreightRoutePlanner:()=> <div aria-label="Road route planner test stub"/>}))
vi.mock('./components/DiscoveryPanel',()=>({DiscoveryPanel:()=> <div aria-label="Discovery component test stub"/>}))
vi.mock('./features/MapWorkspace',()=>({MapWorkspace:()=> <div aria-label="Map component test stub"/>}))
vi.mock('./services/api',async importOriginal=>{
  const original=await importOriginal<typeof import('./services/api')>()
  return {...original,getHealth:vi.fn(),searchFeatures:vi.fn(),searchMapFeatures:vi.fn()}
})
const health={status:'ok',mode:'fixture' as const,version:'0.1.0',database_configured:false,limitations:[]}
const empty={type:'FeatureCollection' as const,features:[],meta:{mode:'fixture' as const,crs:'EPSG:4326' as const,total:0,returned:0,offset:0,limit:250,has_more:false,category_counts:{},missing_categories:[],failed_categories:[],warnings:['synthetic'],attribution:'CC0'}}
beforeEach(()=>{
  vi.clearAllMocks();location.hash='';localStorage.clear()
  vi.mocked(getHealth).mockResolvedValue(health);vi.mocked(searchFeatures).mockResolvedValue(empty);vi.mocked(searchMapFeatures).mockResolvedValue(empty)
})
function mount(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  return render(<QueryClientProvider client={client}><App/></QueryClientProvider>)
}
describe('Connected workspace behavior',()=>{
  it('keeps navigation and map tools available when API fails',async()=>{
    vi.mocked(searchFeatures).mockRejectedValue(new Error('Provider offline'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Provider offline')
    expect(screen.getByRole('heading',{name:'Industrial GIS Explorer',level:1})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Retry'})).toBeEnabled()
    expect(screen.getByRole('button',{name:'Export GeoJSON'})).toBeDisabled()
  })
  it('surfaces empty results and sends submitted search to real query adapter',async()=>{
    mount()
    expect(await screen.findByText(/No matching records in this dataset/)).toBeInTheDocument()
    await userEvent.type(screen.getByRole('textbox',{name:'Search features or coordinates'}),'Warehouse')
    await userEvent.click(screen.getByRole('button',{name:'Run search'}))
    await waitFor(()=>expect(searchFeatures).toHaveBeenLastCalledWith(expect.objectContaining({q:'Warehouse'}),expect.any(AbortSignal)))
  })
  it('opens implemented GeoAI workspace',async()=>{
    mount()
    await userEvent.click(screen.getByRole('button',{name:/GeoAI Copilot/}))
    expect(screen.getByLabelText('GeoAI Copilot test stub')).toBeInTheDocument()
  })
})
