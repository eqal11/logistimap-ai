import {useState} from 'react'
import {render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {it,expect,vi} from 'vitest'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {AnalysisLayerPicker} from './AnalysisLayerPicker'
import {searchFeatures} from '../services/api'
import type {LayerInput} from '../services/analytics'
vi.mock('../services/api',async original=>({...await original<typeof import('../services/api')>(),searchFeatures:vi.fn()}))
it('keeps the query preview after selecting multiple imported IDs',async()=>{
 vi.mocked(searchFeatures).mockResolvedValue({features:['one','two'].map(id=>({type:'Feature',id,geometry:{type:'Point',coordinates:[101,3]},properties:{name:'TEST '+id,source_id:'TEST/'+id,synthetic:false}})),meta:{total:2,has_more:false}} as never)
 function Harness(){const [value,setValue]=useState<LayerInput>({query:{categories:['industrial'],bbox:[101,3,102,4]}});return <><AnalysisLayerPicker label="Input A" value={value} onChange={setValue}/><output>{JSON.stringify(value)}</output></>}
 const q=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}});render(<QueryClientProvider client={q}><Harness/></QueryClientProvider>)
 expect(screen.getByRole('textbox',{name:'Input A bbox'})).toHaveValue('101,3,102,4')
 await userEvent.click(screen.getByRole('button',{name:'Apply query & preview'}))
 await userEvent.click(await screen.findByRole('checkbox',{name:'Select TEST one'}))
 await userEvent.click(screen.getByRole('checkbox',{name:'Select TEST two'}))
 expect(screen.getByRole('status')).toHaveTextContent('{"ids":["one","two"]}')
 expect(screen.getByText('2 selected')).toBeInTheDocument()
})
