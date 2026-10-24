import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Button} from '../components/ui/button'
import {categories,type CategoryId,type Bbox} from '../types'
import {parseCoordinates,searchFeatures} from '../services/api'
import {resolveLocation,type PlaceMatch} from '../services/discovery'
import type {LayerInput} from '../services/analytics'
import {useWorkspace} from '../store/workspace'
import {useAnalyses} from '../store/analytics'
export function AnalysisLayerPicker({label,value,onChange}:{label:string;value:LayerInput;onChange:(v:LayerInput)=>void}){
 const [kind,setKind]=useState('query'),[cats,setCats]=useState<CategoryId[]>(value.query?.categories??['industrial'])
 const [bbox,setBbox]=useState(value.query?.bbox?.join(',')??'101.25,2.72,101.87,3.4'),[center,setCenter]=useState(value.query?.center?.join(',')??''),[radius,setRadius]=useState(String(value.query?.radius_km??5)),[name,setName]=useState('')
 const [matches,setMatches]=useState<PlaceMatch[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[offset,setOffset]=useState(0)
 const [scope,setScope]=useState(value.query)
 const [preview,setPreview]=useState(false),[selected,setSelected]=useState<string[]>([]),[nameFilter,setNameFilter]=useState('')
 const sketches=useWorkspace(s=>s.sketches),layers=useAnalyses(s=>s.layers)
 function query(){const c=parseCoordinates(center);const values=bbox.split(',').map(Number);if(center.trim()&&!c)throw new Error('Use longitude,latitude for center')
 if(!cats.length)throw new Error('Select at least one category')
 if(c){if(!Number.isFinite(Number(radius))||Number(radius)<=0||Number(radius)>200)throw new Error('Radius must be >0 and ≤200 km');return {categories:cats,center:c,radius_km:Number(radius)}}
 if(values.length!==4||!values.every(Number.isFinite)||values[0]>=values[2]||values[1]>=values[3])throw new Error('Use west,south,east,north bbox')
 return {categories:cats,bbox:values as Bbox}}
 function apply(){
  try{setError('');const q=query();setScope(q);onChange({query:q});setKind('query');setOffset(0);setPreview(true)}catch(e){setError((e as Error).message)}
 }
 const data=useQuery({queryKey:['analysis-preview',scope,offset,nameFilter],queryFn:({signal})=>searchFeatures({q:nameFilter,categories:scope?.categories??cats,bbox:scope?.bbox,center:scope?.center,radius:scope?.radius_km,offset},signal,100),enabled:preview&&!!scope})
 async function find(){setBusy(true);setError('');try{setMatches((await resolveLocation(name)).matches)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 function chooseKind(k:string){setKind(k);setError('');if(k==='query')apply();if(k==='sketch'||k==='saved')onChange({features:[]})}
 return <fieldset className="analysis-input"><legend>{label}</legend>
  <label>Source<select aria-label={label+' source'} value={kind} onChange={e=>chooseKind(e.target.value)}><option value="query">Bounded imported category query</option><option value="selected">Select mapped features from preview</option><option value="sketch">Completed map sketch</option><option value="saved">Saved analysis layer</option></select></label>
  {(kind==='query'||kind==='selected')&&<>
   <div className="analysis-category-picker">{categories.filter(c=>c.id!=='study_area').map(c=><label key={c.id}><input type="checkbox" checked={cats.includes(c.id)} onChange={e=>setCats(e.target.checked?[...cats,c.id]:cats.filter(x=>x!==c.id))}/>{c.short}</label>)}</div>
   <div className="analysis-inline"><input aria-label={label+' place name'} placeholder="Search place (explicit submit)" value={name} onChange={e=>setName(e.target.value)}/><Button size="sm" variant="outline" disabled={busy||name.length<2} onClick={find}>{busy?'Searching…':'Find place'}</Button></div>
   {matches.map(m=><button className="analysis-match" key={m.source_id} onClick={()=>{setCenter(m.center.join(','));setMatches([]);setPreview(false)}}>{m.name}<small>{m.source_id} · reference, entrance unverified</small></button>)}
   <div className="analysis-inline"><label>Center lon,lat<input aria-label={label+' center'} value={center} onChange={e=>setCenter(e.target.value)} placeholder="Blank uses bbox"/></label><label>Radius km<input aria-label={label+' radius km'} type="number" min=".1" max="200" value={radius} onChange={e=>setRadius(e.target.value)}/></label></div>
   <label>Bounding box (when center is blank)<input aria-label={label+' bbox'} value={bbox} onChange={e=>setBbox(e.target.value)}/></label>
   <Button size="sm" variant="outline" onClick={apply}>Apply query & preview</Button>
   {preview&&<><p className="analysis-small">{data.isFetching?'Loading imported records…':data.error?data.error.message:(data.data?.meta.total??0)+' matching objects · preview 100/page'}</p>
   <input aria-label={label+' preview name filter'} placeholder="Filter preview name, then select IDs" value={nameFilter} onChange={e=>{setNameFilter(e.target.value);setOffset(0)}}/>
   <div className="analysis-preview-list">{data.data?.features.map(f=><label key={f.id}><input aria-label={'Select '+f.properties.name} type="checkbox" checked={selected.includes(f.id)} disabled={!selected.includes(f.id)&&selected.length>=200} onChange={e=>{const ids=e.target.checked?[...selected,f.id]:selected.filter(id=>id!==f.id);setSelected(ids);setKind('selected');onChange(ids.length?{ids}:{query:query()})}}/><span>{f.properties.name}<small>{f.geometry.type} · {f.properties.source_id}</small></span></label>)}</div>
   <div className="analysis-inline"><Button size="sm" variant="ghost" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-100))}>Previous</Button><Button size="sm" variant="ghost" disabled={!data.data?.meta.has_more} onClick={()=>setOffset(offset+100)}>Next</Button><span>{selected.length} selected</span></div></>}
  </>}
  {kind==='selected'&&!preview&&<Button variant="outline" size="sm" onClick={()=>{apply();setKind('selected')}}>Load selection preview</Button>}
  {kind==='sketch'&&<><p className="analysis-small">Draw a point, line or polygon on the map and press Finish. Choose a completed sketch below. Sketches are user references.</p><select aria-label={label+' sketch'} defaultValue="" onChange={e=>{const f=sketches[Number(e.target.value)];if(f)onChange({features:[{id:'sketch-'+e.target.value,geometry:f.geometry,name:'User sketch '+e.target.value}]})}}><option value="" disabled>Choose completed sketch</option>{sketches.map((f,i)=><option key={i} value={i}>Sketch {i+1} · {f.geometry.type}</option>)}</select></>}
  {kind==='saved'&&<select aria-label={label+' saved layer'} defaultValue="" onChange={e=>onChange({saved_id:e.target.value})}><option value="" disabled>Choose saved layer</option>{layers.filter(l=>l.result.saved_id).map(l=><option key={l.id} value={l.result.saved_id}>{l.result.title}</option>)}</select>}
  <p className="analysis-small">Active input: {value.ids?value.ids.length+' selected IDs':value.features?'user geometry':value.saved_id?'saved analysis':'bounded category query'}. Maximum query 2,000 objects; selection 200.</p>
  {error&&<p role="alert" className="analysis-error">{error}</p>}
 </fieldset>
}
