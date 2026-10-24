import { downloadGeoJSON } from '../services/api'
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Download, Globe2, MapPin, RefreshCw, Search, TriangleAlert } from 'lucide-react'
import { Button } from './ui/button'
import { categories, categoryLabel, type Bbox, type CategoryId } from '../types'
import { discover, getDiscoveryJobs, getStudyTargets, resolveLocation, type DiscoveryJob, type DiscoveryScope, type PlaceMatch } from '../services/discovery'

export function DiscoveryPanel({mode,onScope,getBounds,onLog,defaultOpen=false}:{
  mode?:string;onScope:(scope:DiscoveryScope)=>void;getBounds:()=>Bbox|undefined;onLog:(s:string)=>void;defaultOpen?:boolean
}){
  const client=useQueryClient()
  const [query,setQuery]=useState('Tanjong Malim, Perak, Malaysia'),[matches,setMatches]=useState<PlaceMatch[]>([])
  const [place,setPlace]=useState<PlaceMatch|null>(null),[radius,setRadius]=useState('5'),[bbox,setBbox]=useState('')
  const [scopeType,setScopeType]=useState<'place'|'bbox'>('place')
  const [selected,setSelected]=useState<CategoryId[]>(categories.filter(c=>c.id!=='study_area').map(c=>c.id))
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('')
  const [jobId,setJobId]=useState<string|null>(null),[lastFinished,setLastFinished]=useState('')
  const targets=useQuery({queryKey:['study-targets'],queryFn:({signal})=>getStudyTargets(signal),staleTime:Infinity})
  const history=useQuery({queryKey:['discovery-jobs'],queryFn:({signal})=>getDiscoveryJobs(signal),
    enabled:mode==='postgis',refetchInterval:jobId?3000:false})
  const jobs=history.data?.jobs??[]
  const current=jobs.find(j=>j.id===jobId)
  const running=!!jobId && (!current||['queued','running'].includes(current.status))
  useEffect(()=>{
    if(!current||['queued','running'].includes(current.status)||current.id===lastFinished)return
    setLastFinished(current.id);setJobId(null)
    if(current.status==='completed'){
      setMessage('Import complete: '+current.report?.inserted+' new, '+current.report?.updated+' refreshed. All categories are reported below.')
      onScope(current.parameters)
      onLog('OSM import completed · '+current.parameters.label+' · '+current.report?.valid_features+' valid source objects.')
      client.invalidateQueries({queryKey:['features']});client.invalidateQueries({queryKey:['map-features']})
    }else setError(current.report?.message??'Import interrupted. Check history before retrying; completed transactions are retained.')
  },[current,lastFinished,client,onScope,onLog])
  async function locate(){
    setBusy(true);setError('');setMessage('');setPlace(null);setMatches([])
    try{
      const result=await resolveLocation(query)
      setMatches(result.matches)
      if(!result.matches.length)setMessage('No place match returned. Try another name or use a bounded box; no coordinates were guessed.')
      else setMessage('Choose a matching OSM reference below. This is not a verified industrial boundary.')
    }catch(e){setError(e instanceof Error?e.message:'Location provider failed')}
    finally{setBusy(false)}
  }
  async function start(){
    setError('');setMessage('')
    const km=Number(radius)
    let scope:DiscoveryScope
    if(scopeType==='place'){
      if(!place||!Number.isFinite(km)||km<=0||km>10){setError('Choose an OSM place reference and radius above 0, at most 10 km.');return}
      scope={center:place.center,radius_km:km,label:place.name.split(',').slice(0,2).join(',')}
    }else{
      const values=bbox.split(',').map(s=>Number(s.trim()))
      if(values.length!==4||values.some(n=>!Number.isFinite(n))||values[0]>=values[2]||values[1]>=values[3]){setError('Use west,south,east,north, with increasing coordinates. Maximum area: 400 km².');return}
      scope={bbox:values as Bbox,label:'User bounding-box discovery'}
    }
    setBusy(true)
    try{
      const job=await discover({...scope,categories:selected})
      setJobId(job.id);setLastFinished('');await history.refetch()
      onLog('Started bounded Overpass import; job '+job.id)
    }catch(e){setError(e instanceof Error?e.message:'Import could not start')}
    finally{setBusy(false)}
  }
  return <details className="discovery-panel" open={defaultOpen||undefined}>
    <summary><span className="discovery-symbol"><Globe2 size={19}/></span><span><strong>Real OSM discovery</strong><small>Resolve a place · select categories · import to PostGIS</small></span><span className="discovery-tag">PHASE 2</span></summary>
    <div className="discovery-content">
      <div className="discovery-intro"><p>Import community-mapped features from OpenStreetMap. Existing objects are refreshed by their OSM ID. Coverage is incomplete; boundaries and commercial attributes are unverified.</p><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL 1.0 ↗</a></div>
      <div className="discovery-grid"><div>
        <div className="scope-tabs"><button type="button" className={scopeType==='place'?'active':''} onClick={()=>setScopeType('place')}><MapPin size={14}/>Place & radius</button><button type="button" className={scopeType==='bbox'?'active':''} onClick={()=>setScopeType('bbox')}>Bounding box</button></div>
        {scopeType==='place'?<><label className="discovery-field">Initial study target<select aria-label="Discovery study target" defaultValue="tanjong-malim" onChange={e=>{const t=targets.data?.areas.find(a=>a.id===e.target.value);if(t){setQuery(t.query);setPlace(null);setMatches([])}}}>{targets.data?.areas.map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select></label>
          <form className="place-search" onSubmit={e=>{e.preventDefault();locate()}}><input aria-label="Location name in Malaysia" value={query} maxLength={200} onChange={e=>{setQuery(e.target.value);setPlace(null)}}/><Button type="submit" variant="outline" disabled={busy||running||query.trim().length<2}><Search size={14}/>{busy?'Working…':'Find place'}</Button></form>
          {matches.length>0&&<div className="place-matches" aria-label="OSM location matches">{matches.map(m=><button key={m.source_id} className={place?.source_id===m.source_id?'chosen':''} onClick={()=>{setPlace(m);onScope({center:m.center,radius_km:Number(radius)||5,label:m.name.split(',')[0]})}}><MapPin size={13}/><span>{m.name}<small>{m.type} · {m.source_id} · {m.center.join(', ')}</small></span></button>)}</div>}
          <label className="discovery-field radius-field">Discovery radius · km<input aria-label="Discovery radius km" type="number" min="0.1" max="10" step="0.1" value={radius} onChange={e=>setRadius(e.target.value)}/></label></>:
          <><label className="discovery-field">EPSG:4326 · west,south,east,north<input aria-label="Discovery bounding box" placeholder="Use map extent or enter bounds" value={bbox} onChange={e=>setBbox(e.target.value)}/></label><Button variant="outline" onClick={()=>{const b=getBounds();if(b)setBbox(b.join(','));else setError('Map is not ready.')}}>Use current map extent</Button><p className="discovery-note">Maximum 400 km². Reduce the map extent if a query exceeds provider limits.</p></>}
      </div><div><fieldset><legend>OSM categories · multiple selections</legend><div className="discovery-categories">{categories.filter(c=>c.id!=='study_area').map(c=><label key={c.id}><input type="checkbox" checked={selected.includes(c.id)} onChange={()=>setSelected(s=>s.includes(c.id)?s.filter(id=>id!==c.id):[...s,c.id])}/><i style={{background:c.color}}/>{c.label}</label>)}</div></fieldset><p className="discovery-note">Major roads only: motorway, trunk, primary, secondary and links. Airports are not verified cargo facilities. Land-use polygons are not official park boundaries.</p><Button disabled={busy||running||!selected.length||mode!=='postgis'} onClick={start}><Database size={15}/>{running?'Import running…':'Import selected categories'}</Button>{mode!=='postgis'&&<p className="discovery-note">Live imports require PostGIS mode.</p>}</div></div>
      {running&&<p role="status" className="import-progress"><RefreshCw className="spin" size={15}/>Overpass query / validation / database transaction in progress. This may take over a minute. You can keep using the map.</p>}
      {error&&<p role="alert" className="discovery-error"><TriangleAlert size={15}/>{error}</p>}
      {message&&<p role="status" className="discovery-message">{message}</p>}
      {targets.error&&<p role="alert">{targets.error.message}</p>}
      <div className="import-history"><div><h3>Import history & coverage</h3><Button variant="ghost" size="sm" disabled={history.isFetching||mode!=='postgis'} onClick={()=>history.refetch()}><RefreshCw size={13}/>Refresh history</Button></div>
        {history.error&&<p role="alert">{history.error.message}</p>}
        {!jobs.length&&<p className="discovery-note">No imports recorded yet.</p>}
        {jobs.map(job=><ImportRecord key={job.id} job={job} onScope={onScope}/>)}
      </div>
      <p className="discovery-policy">Local workspace access only. One import at a time; Overpass cooldown 12 seconds, cache 24 hours. Place search: no autocomplete, at most one request per 1.1 seconds, cache 7 days. <a href="https://operations.osmfoundation.org/policies/nominatim/" target="_blank" rel="noreferrer">Nominatim policy ↗</a></p>
    </div>
  </details>
}
function ImportRecord({job,onScope}:{job:DiscoveryJob;onScope:(scope:DiscoveryScope)=>void}){
  return <details className={'import-record status-'+job.status}><summary><span><strong>{job.parameters.label}</strong><small>{new Date(job.created_at).toLocaleString()} · {job.status}</small></span><span>{job.report?.valid_features??'—'} valid objects</span></summary><div>
    {job.report?.message&&<p role="alert">{job.report.message}</p>}
    {job.report&&<><p>{job.report.inserted??0} new · {job.report.updated??0} refreshed · {Object.values(job.report.skipped??{}).reduce((a,b)=>a+b,0)} invalid/incomplete objects skipped · {job.report.provider_cached?'cached provider response':'live provider response'}</p>
    <div className="coverage-counts">{Object.entries(job.report.category_counts??{}).map(([category,count])=><span key={category}>{categoryLabel(category)}<strong>{count}</strong></span>)}</div>
    {job.report.missing_categories?.length>0&&<p>Zero returned: {job.report.missing_categories.map(categoryLabel).join(', ')}. This does not establish real-world absence.</p>}
    {job.report.failed_categories?.length>0&&<p>Failed categories: {job.report.failed_categories.map(categoryLabel).join(', ')}</p>}
    <p>OSM snapshot: {job.report.osm_base_timestamp??'Unavailable'}</p></>}
    <div className="import-record-actions"><Button variant="outline" size="sm" onClick={()=>onScope(job.parameters)}>View imported extent</Button><Button variant="ghost" size="sm" onClick={()=>downloadGeoJSON(job,'logistimap-import-'+job.id+'.json')}><Download size={13}/>Export report</Button></div>
  </div></details>
}
