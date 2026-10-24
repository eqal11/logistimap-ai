import { useState } from 'react'
import { useRouting } from '../store/routing'
import { getFeatureAnchor } from '../services/routing'
import { ArrowDown, ArrowUp, ChevronRight, Database, ExternalLink, Info, Layers, MapPin, X } from 'lucide-react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categories, categoryLabel, type Health, type SearchResult } from '../types'
import { useWorkspace } from '../store/workspace'
import { Button } from './ui/button'
import { apiBase, downloadGeoJSON } from '../services/api'

export function Inspector({data,health,tab,setTab}:{data?:SearchResult;health?:Health;tab:string;setTab:(tab:string)=>void}){
  const {selected,setSelected,visible,toggleLayer,order,moveLayer}=useWorkspace()
  const [routeBusy,setRouteBusy]=useState(false),[routeError,setRouteError]=useState('')
  async function assignRoute(role:'origin'|'destination'){
    if(!selected||selected.properties.synthetic)return
    setRouteBusy(true);setRouteError('')
    try{const anchor=await getFeatureAnchor(selected.id);useRouting.getState().setEndpoint(role,anchor);location.hash='routing'}
    catch(error){setRouteError(error instanceof Error?error.message:'Feature reference could not be loaded')}
    finally{setRouteBusy(false)}
  }
  const chart=categories.filter(c=>(data?.meta.category_counts[c.id]??0)>0).map(c=>({name:c.short,count:data!.meta.category_counts[c.id],color:c.color}))
  return <aside className="inspector" aria-label="Analysis and layer panel">
    <div className="panel-tabs" role="tablist" aria-label="Inspector tabs">{['Layers','Feature','Insights'].map(name=><button role="tab" aria-selected={tab===name} key={name} className={tab===name?'selected-tab':''} onClick={()=>setTab(name)}>{name}</button>)}</div>
    {tab==='Layers'&&<>
      <div className="panel-section-heading"><div><span className="eyebrow">MAP CONTENTS</span><h3>Workspace layers</h3></div><Layers size={18}/></div>
      <p className="panel-description">Toggle visibility. Arrows set display order from top to bottom.</p>
      <div className="layer-list">{order.map((id,index)=>{const c=categories.find(c=>c.id===id)!;const count=data?.features.filter(f=>f.properties.categories.includes(id)).length??0;return <div className={'layer-row '+(!visible.includes(id)?'layer-hidden':'')} key={id}>
        <label><input type="checkbox" aria-label={'Show '+c.label} checked={visible.includes(id)} onChange={()=>toggleLayer(id)}/><span className="layer-swatch" style={{background:c.color}}/><span>{c.label}<small>{id==='road'?'Reference geometry · not routing':id==='industrial_park'?'Boundary status in attributes':'Loaded records'}</small></span></label>
        <span className="layer-count">{count}</span><div className="order-buttons"><button aria-label={'Move '+c.label+' up'} disabled={index===0} onClick={()=>moveLayer(id,-1)}><ArrowUp size={11}/></button><button aria-label={'Move '+c.label+' down'} disabled={index===order.length-1} onClick={()=>moveLayer(id,1)}><ArrowDown size={11}/></button></div>
      </div>})}</div>
      <div className="panel-callout"><Info size={16}/><p>A feature can belong to several categories. It is rendered once and remains visible while any of its categories is enabled.</p></div>
      {data?.meta.mode==='postgis'&&<p className="osm-attribution"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL 1.0 ↗</a></p>}
      <div className="source-card"><div className="source-icon"><Database size={18}/></div><div><strong>{data?.meta.mode==='fixture'?'Synthetic fixture':'Feature data source'}</strong><span>{data?.meta.mode==='fixture'?'Local test dataset · CC0':'Imported records only'}</span></div><span className="small-pill">4326</span></div>
    </>}
    {tab==='Feature'&&(selected?<div className="feature-detail"><div className="feature-title"><span className="feature-icon"><MapPin size={20}/></span><Button size="icon" variant="ghost" aria-label="Clear selected feature" onClick={()=>setSelected(null)}><X size={16}/></Button></div><span className="eyebrow">SELECTED FEATURE</span><h3>{selected.properties.name}</h3><div className="feature-tags">{selected.properties.categories.map(c=><span key={c}>{categoryLabel(c)}</span>)}</div>
      {selected.properties.synthetic&&<div className="synthetic-notice">Synthetic test geometry. No real facility or operational status is represented.</div>}
      <dl>{Object.entries({ID:selected.id,Geometry:selected.geometry.type,'Boundary status':selected.properties.boundary_status,'Source ID':selected.properties.source_id,Dataset:selected.properties.dataset_id,Imported:selected.properties.imported_at,Source:selected.properties.source,License:selected.properties.license??(selected.properties.synthetic?'CC0':null),...selected.properties.attributes}).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{value===null||value===undefined?'Unknown':typeof value==='object'?JSON.stringify(value):String(value)}</dd></div>)}</dl>
      <div className="route-assignment"><Button variant="outline" disabled={routeBusy||selected.properties.synthetic} onClick={()=>assignRoute('origin')}>Use as route origin</Button><Button variant="outline" disabled={routeBusy||selected.properties.synthetic} onClick={()=>assignRoute('destination')}>Use as route destination</Button>{routeError&&<p role="alert">{routeError}</p>}</div>
      <Button variant="outline" onClick={()=>downloadGeoJSON({type:'FeatureCollection',features:[selected]},'logistimap-selected-feature.geojson')}>Export selected feature<ChevronRight size={14}/></Button>
    </div>:<div className="empty-panel"><MapPin size={32}/><h3>Inspect a feature</h3><p>Select a point, line, or polygon on the map, or choose a row in the attribute table.</p></div>)}
    {tab==='Insights'&&<div className="insights-panel"><span className="eyebrow">QUERY SUMMARY</span><h3>Category distribution</h3><p className="panel-description">Counts from the current API query, before pagination. Memberships can overlap.</p>
      {chart.length?<div className="distribution-chart"><ResponsiveContainer width="100%" height={230}><BarChart data={chart} layout="vertical" margin={{left:0,right:12}}><XAxis type="number" allowDecimals={false} hide/><YAxis dataKey="name" type="category" width={76} tick={{fontSize:10,fill:'#73838b'}} axisLine={false} tickLine={false}/><Tooltip cursor={{fill:'#eff5f3'}}/><Bar dataKey="count" radius={[0,3,3,0]} barSize={12}>{chart.map(c=><Cell key={c.name} fill={c.color}/>)}</Bar></BarChart></ResponsiveContainer></div>:<p>No records available for this query.</p>}
      <div className="metric-list"><div><span>Unique matched records</span><strong>{data?.meta.total??'—'}</strong></div><div><span>Loaded on this page</span><strong>{data?.meta.returned??'—'}</strong></div><div><span>Missing requested categories</span><strong>{data?.meta.missing_categories.length??'—'}</strong></div></div>
      {data?.meta.missing_categories.length? <p className="synthetic-notice">No records returned for: {data.meta.missing_categories.map(categoryLabel).join(', ')}. This does not establish real-world absence.</p>:null}
      <p className="panel-description">Counts describe mapped OSM objects, not verified facility totals. Density and network analysis remain unavailable.</p>
    </div>}
    <div className="panel-footer"><span className={'status-dot '+(health?'':'offline')}/>{health?'FastAPI connected':'API connection unavailable'}<a href={(apiBase||'http://127.0.0.1:8000')+'/docs'} target="_blank" rel="noreferrer" aria-label="Open API documentation"><ExternalLink size={13}/></a></div>
  </aside>
}
