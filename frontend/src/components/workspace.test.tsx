import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Inspector } from './Inspector'
import { AttributeTable } from './AttributeTable'
import { categories, type SearchResult, type SpatialFeature } from '../types'
import { useWorkspace } from '../store/workspace'
const feature:SpatialFeature={type:'Feature',id:'fixture-1',geometry:{type:'Point',coordinates:[101.55,3.12]},properties:{
  name:'TEST Warehouse',categories:['warehouse','logistics_hub'],source:'Synthetic fixture',source_id:'test-1',
  dataset_id:'test-data',imported_at:'2026-10-24T00:00:00Z',synthetic:true,boundary_status:'not_applicable',attributes:{capacity:null,ownership:null},
}}
const data:SearchResult={type:'FeatureCollection',features:[feature],meta:{mode:'fixture',crs:'EPSG:4326',total:1,returned:1,offset:0,limit:250,has_more:false,category_counts:{warehouse:1,logistics_hub:1},missing_categories:[],failed_categories:[],warnings:['Synthetic test data'],attribution:'CC0'}}
beforeEach(()=>useWorkspace.setState({sketches:[],selected:null,visible:categories.map(c=>c.id),order:categories.map(c=>c.id),tool:'select'}))
describe('Feature inspection',()=>{
  it('labels synthetic data and unknown attributes',()=>{
    useWorkspace.setState({selected:feature})
    render(<Inspector data={data} tab="Feature" setTab={()=>{}}/>)
    expect(screen.getByText(/Synthetic test geometry/)).toBeInTheDocument()
    expect(screen.getAllByText('Unknown')).toHaveLength(2)
    expect(screen.getByText('TEST Warehouse')).toBeInTheDocument()
  })
  it('toggles visibility and layer order through accessible controls',async()=>{
    render(<Inspector data={data} tab="Layers" setTab={()=>{}}/>)
    const user=userEvent.setup()
    await user.click(screen.getByRole('checkbox',{name:'Show Warehouses'}))
    expect(useWorkspace.getState().visible).not.toContain('warehouse')
    expect(useWorkspace.getState().visible).toContain('logistics_hub')
    await user.click(screen.getByRole('button',{name:'Move Warehouses up'}))
    expect(useWorkspace.getState().order.indexOf('warehouse')).toBe(1)
  })
})
describe('Attribute workspace',()=>{
  it('selects actual backend feature objects and shows geometry/provenance',async()=>{
    const select=vi.fn()
    render(<AttributeTable data={data} expanded={true} setExpanded={()=>{}} tab="attributes" setTab={()=>{}} logs={[]} onSelect={select} onPage={()=>{}} busy={false}/>)
    await userEvent.click(screen.getByRole('button',{name:'TEST Warehouse'}))
    expect(select).toHaveBeenCalledWith(feature)
    expect(screen.getByText('Point')).toBeInTheDocument()
    expect(screen.getByText('Synthetic · CC0')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Next'})).toBeDisabled()
  })
  it('renders an honest empty state',()=>{
    render(<AttributeTable data={{...data,features:[],meta:{...data.meta,total:0,returned:0}}} expanded={true} setExpanded={()=>{}} tab="attributes" setTab={()=>{}} logs={[]} onSelect={()=>{}} onPage={()=>{}} busy={false}/>)
    expect(screen.getByText(/No records loaded/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Export page'})).toBeDisabled()
  })
})
