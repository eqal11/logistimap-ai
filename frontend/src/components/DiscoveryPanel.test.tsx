import { beforeEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DiscoveryPanel } from './DiscoveryPanel'
import { discover, getDiscoveryJobs, getStudyTargets, resolveLocation } from '../services/discovery'
vi.mock('../services/discovery',()=>({discover:vi.fn(),getDiscoveryJobs:vi.fn(),getStudyTargets:vi.fn(),resolveLocation:vi.fn()}))
const place={name:'Rawang, Selangor, Malaysia',center:[101.5773144,3.3197692] as [number,number],bbox:[101.53,3.27,101.62,3.36] as [number,number,number,number],source_id:'node/254074012',type:'town'}
beforeEach(()=>{
  vi.clearAllMocks()
  vi.mocked(getStudyTargets).mockResolvedValue({areas:[{id:'tanjong-malim',name:'AHTV / Tanjong Malim',query:'Tanjong Malim, Perak, Malaysia',note:'Town reference'}]})
  vi.mocked(getDiscoveryJobs).mockResolvedValue({jobs:[]})
  vi.mocked(resolveLocation).mockResolvedValue({matches:[place],cached:false,attribution:'OSM'})
  vi.mocked(discover).mockResolvedValue({id:'job-1',status:'queued'})
})
function mount(mode='postgis'){
  const onScope=vi.fn()
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  render(<QueryClientProvider client={client}><DiscoveryPanel mode={mode} defaultOpen onScope={onScope} getBounds={()=>[101.5,3.1,101.51,3.11]} onLog={()=>{}}/></QueryClientProvider>)
  return onScope
}
it('resolves only on explicit submit and sends all eight selected categories',async()=>{
  const scope=mount()
  expect(resolveLocation).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button',{name:'Find place'}))
  await userEvent.click(await screen.findByRole('button',{name:/Rawang, Selangor, Malaysia/}))
  expect(scope).toHaveBeenCalledWith(expect.objectContaining({center:place.center,radius_km:5}))
  await userEvent.click(screen.getByRole('button',{name:'Import selected categories'}))
  await waitFor(()=>expect(discover).toHaveBeenCalledWith(expect.objectContaining({
    center:place.center,radius_km:5,categories:['industrial','industrial_park','warehouse','logistics_hub','port','airport','road','rail'],
  })))
})
it('requires a real chosen match before a place import',async()=>{
  mount()
  await userEvent.click(screen.getByRole('button',{name:'Import selected categories'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Choose an OSM place reference')
  expect(discover).not.toHaveBeenCalled()
})
it('reports provider failure without inventing matches',async()=>{
  vi.mocked(resolveLocation).mockRejectedValue(new Error('Geocoder HTTP 429'))
  mount()
  await userEvent.click(screen.getByRole('button',{name:'Find place'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('429')
  expect(screen.queryByLabelText('OSM location matches')).not.toBeInTheDocument()
})
it('validates bounding boxes and disables live imports in fixture mode',async()=>{
  mount('fixture')
  expect(screen.getByRole('button',{name:'Import selected categories'})).toBeDisabled()
  await userEvent.click(screen.getByRole('button',{name:'Bounding box'}))
  await userEvent.click(screen.getByRole('button',{name:'Use current map extent'}))
  expect(screen.getByLabelText('Discovery bounding box')).toHaveValue('101.5,3.1,101.51,3.11')
})
