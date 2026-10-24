import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDownToLine, ArrowDownUp, ArrowDown, ArrowUp, ArrowRight, Check, Clock3, Database, MapPin, MousePointer2, Plus, RefreshCw, Route, Search, ShieldAlert, Trash2, Warehouse, X } from 'lucide-react'
import { Button } from '../components/ui/button'
import { MapWorkspace, type MapHandle } from './MapWorkspace'
import { useRouting } from '../store/routing'
import { useWorkspace } from '../store/workspace'
import { downloadGeoJSON, parseCoordinates, searchFeatures } from '../services/api'
import { resolveLocation } from '../services/discovery'
import { anchorLabel, calculateRoute, distanceLabel, durationLabel, findRoutingFacilities, getFeatureAnchor, getNearestWarehouse, getRoutingProvider, routeGeoJSON, saveRoute } from '../services/routing'
import type { PlaceMatch } from '../services/discovery'
import type { SpatialFeature } from '../types'
import type { Coordinate, RouteStop } from '../types/routing'

const errorText=(error:unknown)=>error instanceof Error?error.message:'Operation failed. Retry after checking the provider.'
export function FreightRoutePlanner({mode,onLog}:{mode?:string;onLog:(message:string)=>void}){
  const {stops,result,activeRoute,pickId,revision,setPoint,addStop,reverse,reset,setPick,setResult,setActiveRoute}=useRouting()
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[note,setNoteValue]=useState('')
  const [alternatives,setAlternatives]=useState(true),[snap,setSnap]=useState('1000')
  const [context,setContext]=useState(true),[saving,setSaving]=useState(false),[saved,setSaved]=useState('')
  const [findingNearest,setFindingNearest]=useState(false)
  const controller=useRef<AbortController|null>(null),generation=useRef(0)
  const noteAt=useRef(0)
  function setNote(value:string){noteAt.current=useRouting.getState().revision;setNoteValue(value)}
  const map=useRef<MapHandle>(null),mapContainer=useRef<HTMLDivElement>(null)
  const provider=useQuery({queryKey:['routing-provider'],queryFn:({signal})=>getRoutingProvider(signal),staleTime:30000})
  const facilities=useQuery({queryKey:['route-facility-context'],queryFn:({signal})=>searchFeatures({q:'',categories:['industrial','warehouse','logistics_hub','port'],offset:0},signal),enabled:context})
  useEffect(()=>{generation.current++;controller.current?.abort();setBusy(false);setError('');setSaved('')},[revision])
  useEffect(()=>{setSaved('')},[activeRoute,result?.calculation_id])
  useEffect(()=>()=>controller.current?.abort(),[])
  useEffect(()=>{if(result)fitRoute()},[result,activeRoute])
  const selected=result?.routes[activeRoute]
  function fitRoute(){
    const route=useRouting.getState().result?.routes[useRouting.getState().activeRoute]
    if(!route)return
    const coords=route.geometry.coordinates
    map.current?.fit([Math.min(...coords.map(p=>p[0])),Math.min(...coords.map(p=>p[1])),Math.max(...coords.map(p=>p[0])),Math.max(...coords.map(p=>p[1]))])
  }
  function pick(id:string){
    setPick(pickId===id?null:id);useWorkspace.getState().setTool('select')
    if(pickId!==id)mapContainer.current?.scrollIntoView({block:'center',behavior:'auto'})
  }
  function mapPoint(coordinates:Coordinate){
    const id=useRouting.getState().pickId
    if(!id)return
    setPoint(id,{coordinates,label:'Map reference '+coordinates.map(n=>n.toFixed(5)).join(', '),source:'Map click',anchor_method:'user_reference'})
    setNote('Map reference selected. The routing provider will snap it to a road; this is not a verified facility entrance.')
  }
  async function compute(){
    setError('');setSaved('');setNote('')
    const maxSnap=Number(snap)
    if(stops.some(s=>!s.point)||!Number.isInteger(maxSnap)||maxSnap<25||maxSnap>2000){
      setError('Choose all stops and a road snapping radius between 25 and 2,000 meters.');return
    }
    controller.current?.abort();controller.current=new AbortController()
    const token=++generation.current
    setBusy(true)
    try{
      const response=await calculateRoute(stops,alternatives,maxSnap,controller.current.signal)
      if(token!==generation.current)return
      setResult(response)
      onLog('Road route from '+response.provider+' · '+distanceLabel(response.routes[0].distance_m)+' · car estimate '+durationLabel(response.routes[0].duration_s))
      provider.refetch()
    }catch(e){
      if(token===generation.current&&!controller.current?.signal.aborted)setError(errorText(e))
    }finally{if(token===generation.current)setBusy(false)}
  }
  async function nearest(){
    const id=stops[0].point?.feature_id
    if(!id)return
    const revisionAtStart=useRouting.getState().revision
    const destinationId=stops.at(-1)!.id
    setFindingNearest(true);setError('')
    try{
      const destination=await getNearestWarehouse(id)
      if(useRouting.getState().revision!==revisionAtStart)return
      setPoint(destinationId,destination)
      setNote('Closest mapped warehouse by geographic footprint distance: '+distanceLabel(destination.geographic_distance_m)+'. Driving proximity has not been ranked; calculate a road route.')
    }catch(e){setError(errorText(e))}
    finally{setFindingNearest(false)}
  }
  async function save(){
    if(!result)return
    setSaving(true);setError('')
    const calculationId=result.calculation_id, routeIndex=activeRoute
    try{
      const receipt=await saveRoute(result,routeIndex)
      onLog('Saved provider route to PostGIS · '+receipt.id)
      const current=useRouting.getState()
      if(current.result?.calculation_id===calculationId&&current.activeRoute===routeIndex)setSaved(receipt.id)
    }
    catch(e){setError(errorText(e))}
    finally{setSaving(false)}
  }
  const routeStops=stops.flatMap((s,index)=>s.point?.coordinates?[{coordinates:s.point.coordinates,label:index===0?'A':index===stops.length-1?'B':String(index),name:s.point.label}]:[])
  return <section className="freight-workspace" aria-label="Freight route planner">
    <div className="routing-notice"><ShieldAlert size={20}/><div><strong>Standard car network · planning reference</strong><p>Truck restrictions, vehicle height/weight, hazardous goods and live traffic are unsupported. Estimates are not verified heavy-vehicle routes.</p></div><span>PHASE 3</span></div>
    <div className="freight-layout">
      <div className="route-controls">
        <div className="route-control-heading"><div><span className="eyebrow">ROAD NETWORK PLANNING</span><h2>Build your itinerary</h2></div><Route size={22}/></div>
        <div className="route-stop-list">{stops.map((stop,index)=><StopEditor key={stop.id} stop={stop} index={index} total={stops.length} picking={pickId===stop.id} onPick={()=>pick(stop.id)} onError={setError}/>)}</div>
        <div className="stop-actions"><Button variant="outline" size="sm" disabled={stops.length>=8||busy} onClick={addStop}><Plus size={13}/>Add intermediate stop</Button><Button variant="ghost" size="sm" disabled={busy} onClick={reverse}><ArrowDownUp size={13}/>Reverse</Button><Button variant="ghost" size="icon" aria-label="Clear route plan" disabled={busy} onClick={reset}><Trash2 size={14}/></Button></div>
        <p className="routing-small">Up to 8 points, in the order shown. Stop order is preserved; no route optimization is performed.</p>
        {stops[0].point?.feature_id&&<Button className="nearest-warehouse" variant="outline" size="sm" disabled={findingNearest||busy} onClick={nearest}><Warehouse size={14}/>{findingNearest?'Finding warehouse…':'Closest mapped warehouse · geographic'}</Button>}
        <div className="route-options"><label>Vehicle profile<select aria-label="Routing vehicle profile" value="car" disabled><option value="car">Standard car · truck profile unavailable</option></select></label><label>Maximum road snapping · meters<input aria-label="Maximum road snapping meters" type="number" min="25" max="2000" step="25" value={snap} onChange={e=>{setSnap(e.target.value);useRouting.setState(s=>({result:null,revision:s.revision+1}))}}/></label><label className="route-alternatives"><input type="checkbox" checked={alternatives} onChange={e=>{setAlternatives(e.target.checked);useRouting.setState(s=>({result:null,revision:s.revision+1}))}}/>Request alternatives for two-point routes</label></div>
        <div className="calculate-actions"><Button disabled={busy||provider.data?.configured===false} onClick={compute}><Route size={16}/>{busy?'Calculating road route…':'Calculate road route'}</Button>{busy&&<Button variant="outline" onClick={()=>{generation.current++;controller.current?.abort();setBusy(false);setNote('Request cancelled in this browser. A server request already in progress may finish and be cached.')}}>Cancel</Button>}</div>
        {error&&<div className="routing-error" role="alert"><ShieldAlert size={16}/>{error}</div>}
        {note&&noteAt.current===revision&&<p className="routing-feedback" role="status">{note}</p>}
        {busy&&<p className="routing-feedback" role="status"><RefreshCw size={14} className="spin"/>Requesting real road geometry. No straight-line substitute will be displayed.</p>}
        <div className="route-provider"><strong>{provider.data?.provider??'Checking routing configuration…'}</strong><span>{provider.isLoading?'Checking configuration…':provider.error?provider.error.message:provider.data?.configured?(provider.data.last_failure?'Last upstream request failed':provider.data.last_success_at?'Last upstream request succeeded':'Configured · availability unverified'):'Routing unavailable'}</span>{provider.data?.cooldown_seconds? <p>Provider cooldown: {provider.data.cooldown_seconds} seconds</p>:null}<p>Local workspace · 24-hour cache · 12 upstream requests/minute maximum</p><a href={provider.data?.policy_url??'https://routing.openstreetmap.de/about.html'} target="_blank" rel="noreferrer">Provider policy ↗</a><a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Fix the map ↗</a></div>
      </div>
      <div className="route-map-column">
        <div className="route-map-toolbar"><div><span className="live-dot"/><strong>Road route workspace</strong><small>{result?result.routes.length+' provider route'+(result.routes.length===1?'':'s'):'Select references, then calculate'}</small></div><Button variant="outline" size="sm" disabled={!result} onClick={fitRoute}>Fit route</Button></div>
        {pickId&&<div className="route-pick-prompt" role="status"><MousePointer2 size={17}/>Click the map to place {stops.findIndex(s=>s.id===pickId)===0?'origin':stops.findIndex(s=>s.id===pickId)===stops.length-1?'destination':'intermediate stop'}.<button aria-label="Cancel route map picking" onClick={()=>setPick(null)}><X size={16}/></button></div>}
        <div className="route-map" ref={mapContainer}><MapWorkspace ref={map} data={context?facilities.data:undefined} initialBbox={[101.2,2.65,101.9,3.95]} onViewport={()=>{}} onLog={onLog}
          routingResult={result??undefined} activeRoute={activeRoute} routeStops={routeStops} pickingRoutePoint={!!pickId} onRoutePoint={mapPoint} onRouteSelect={setActiveRoute}/></div>
        <div className="route-map-caption"><label><input type="checkbox" checked={context} onChange={e=>setContext(e.target.checked)}/>Imported facility context</label><span>{context?facilities.isFetching?'Loading facilities…':facilities.error?'Facility context unavailable':(facilities.data?.meta.returned??0)+' of '+(facilities.data?.meta.total??0)+' reference objects':'Context hidden'} · EPSG:4326</span></div>
        {selected&&result?<div className="route-results">
          <div className="route-results-heading"><div><span className="eyebrow">PROVIDER-COMPUTED ROAD ROUTES</span><h2>Compare & inspect</h2></div><span className="route-cache-badge">{result.cached?'Cached result':'Live provider result'}</span></div>
          <div className="route-comparison">{result.routes.map((route,index)=><button key={index} className={'route-option '+(activeRoute===index?'route-option-active':'')} onClick={()=>setActiveRoute(index)} aria-label={'Select route '+(index+1)} aria-pressed={activeRoute===index}><span className="route-choice-mark">{activeRoute===index?<Check size={14}/>:index+1}</span><span><strong>{index===0?'Provider recommendation':'Alternative '+index}</strong><small>{distanceLabel(route.distance_m)} · {durationLabel(route.duration_s)}</small>{index>0&&<small>{(route.distance_m-result.routes[0].distance_m>=0?'+':'')+((route.distance_m-result.routes[0].distance_m)/1000).toFixed(2)} km · {(route.duration_s-result.routes[0].duration_s>=0?'+':'')+Math.round((route.duration_s-result.routes[0].duration_s)/60)} min vs recommendation</small>}</span></button>)}</div>
          <div className="route-summary-metrics"><div><Route size={18}/><span>Road distance<strong>{distanceLabel(selected.distance_m)}</strong></span></div><div><Clock3 size={18}/><span>Estimated car duration<strong>{durationLabel(selected.duration_s)}</strong></span></div><div><MapPin size={18}/><span>Ordered waypoints<strong>{result.waypoints.length}</strong></span></div></div>
          <div className="route-result-actions"><Button variant="outline" size="sm" onClick={()=>downloadGeoJSON(routeGeoJSON(result,activeRoute),'logistimap-road-route.geojson')}><ArrowDownToLine size={14}/>Export selected route</Button>{result.routes.length>1&&<Button variant="ghost" size="sm" onClick={()=>downloadGeoJSON(routeGeoJSON(result,activeRoute,true),'logistimap-route-comparison.geojson')}>Export alternatives</Button>}<Button variant="outline" size="sm" disabled={saving||mode!=='postgis'} onClick={save}><Database size={14}/>{saving?'Saving…':'Save selected to PostGIS'}</Button></div>
          {saved&&<p className="routing-feedback" role="status">Saved to PostGIS · {saved}</p>}
          <details className="route-detail" open><summary>Legs & road snapping</summary><ol>{selected.legs.map((leg,index)=><li key={index}><span>{result.waypoints[index].label}<ArrowRight size={12}/>{result.waypoints[index+1].label}</span><strong>{distanceLabel(leg.distance_m)} · {durationLabel(leg.duration_s)}</strong>{leg.summary&&<small>{leg.summary}</small>}</li>)}</ol><div className="snapping-list">{result.waypoints.map((point,index)=><div key={index}><strong>{index===0?'A':index===result.waypoints.length-1?'B':index}</strong><span>{point.label}<small>Road snap: {point.snap_distance_m.toFixed(1)} m · {point.road_name||'Unnamed road'} · {anchorLabel(point.anchor_method)}</small>{point.feature_id&&<small>GIS feature: {point.feature_id}</small>}</span></div>)}</div></details>
          <details className="route-detail"><summary>Provider, methodology & limitations</summary><p>{result.provider} · car · retrieved {new Date(result.retrieved_at).toLocaleString()}</p><p>Routing dataset version: {result.data_version??'Not supplied by provider'}. Independent of the imported feature dataset.</p><ul>{result.warnings.map(w=><li key={w}>{w}</li>)}</ul><p>{result.attribution}</p><a href={result.fix_map_url} target="_blank" rel="noreferrer">Fix the map ↗</a></details>
        </div>:<div className="route-empty"><Route size={25}/><div><strong>Your road itinerary will appear here</strong><p>Select at least two references. Distance, duration and geometry come from the routing provider only.</p></div></div>}
      </div>
    </div>
  </section>
}

function StopEditor({stop,index,total,picking,onPick,onError}:{stop:RouteStop;index:number;total:number;picking:boolean;onPick:()=>void;onError:(message:string)=>void}){
  const [kind,setKind]=useState<'place'|'facility'>('place'),[query,setQuery]=useState('')
  const [places,setPlaces]=useState<PlaceMatch[]>([]),[facilities,setFacilities]=useState<SpatialFeature[]>([])
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('')
  const {setPoint,removeStop,moveStop}=useRouting()
  const role=index===0?'origin':index===total-1?'destination':'stop '+index
  const letter=index===0?'A':index===total-1?'B':String(index)
  async function search(){
    setBusy(true);setPlaces([]);setFacilities([]);setMessage('');onError('')
    try{
      const coords=parseCoordinates(query)
      if(kind==='place'&&coords){setPoint(stop.id,{coordinates:coords,label:'Coordinate reference '+query,source:'User coordinates',anchor_method:'user_reference'});return}
      if(kind==='place'){
        const found=await resolveLocation(query);setPlaces(found.matches)
        if(!found.matches.length)setMessage('No location match returned. Try another name or pick a reference on the map.')
      }else{
        const found=await findRoutingFacilities(query);setFacilities(found.features.filter(f=>!f.properties.synthetic))
        if(!found.features.some(f=>!f.properties.synthetic))setMessage('No real imported feature matched. Adjust the feature name.')
        else if(found.meta.has_more)setMessage('First 25 results; narrow the feature name for more precise matching.')
      }
    }catch(e){onError(errorText(e))}
    finally{setBusy(false)}
  }
  async function chooseFeature(feature:SpatialFeature){
    setBusy(true);onError('')
    try{setPoint(stop.id,await getFeatureAnchor(feature.id));setFacilities([]);setMessage('Representative geometry reference selected; inspect the road snap before use.')}
    catch(e){onError(errorText(e))}
    finally{setBusy(false)}
  }
  return <article className={'route-stop '+(picking?'stop-picking':'')}>
    <div className="stop-title"><span className={'stop-letter '+(index===total-1?'stop-destination':'')}>{letter}</span><strong>{index===0?'Origin':index===total-1?'Destination':'Intermediate stop '+index}</strong><div>{index>0&&index<total-1&&<><button aria-label={'Move stop '+index+' up'} disabled={index===1} onClick={()=>moveStop(stop.id,-1)}><ArrowUp size={12}/></button><button aria-label={'Move stop '+index+' down'} disabled={index===total-2} onClick={()=>moveStop(stop.id,1)}><ArrowDown size={12}/></button><button aria-label={'Remove stop '+index} onClick={()=>removeStop(stop.id)}><X size={13}/></button></>}<button aria-label={'Pick '+role+' on map'} title="Pick on map" onClick={onPick} className={picking?'picking-active':''}><MousePointer2 size={15}/></button></div></div>
    {stop.point&&<div className="chosen-stop"><strong>{stop.point.label}</strong><small>{stop.point.coordinates?.map(v=>v.toFixed(6)).join(', ')} · {stop.point.source_id??stop.point.source??'GIS reference'}</small><small>{anchorLabel(stop.point.anchor_method)}</small><button aria-label={'Clear '+role} onClick={()=>setPoint(stop.id,null)}><X size={13}/></button></div>}
    <div className="stop-source-tabs"><button className={kind==='place'?'active':''} onClick={()=>{setKind('place');setFacilities([]);setMessage('')}}>Place / coordinates</button><button className={kind==='facility'?'active':''} onClick={()=>{setKind('facility');setPlaces([]);setMessage('')}}>Imported GIS</button></div>
    <form className="stop-search" onSubmit={e=>{e.preventDefault();search()}}><input aria-label={'Search '+role+' name or coordinates'} placeholder={kind==='place'?'Location name or longitude,latitude':'Facility, warehouse, hub or port name'} value={query} maxLength={200} onChange={e=>setQuery(e.target.value)}/><button type="submit" aria-label={'Search '+role} disabled={busy||query.trim().length<2}>{busy?<RefreshCw className="spin" size={15}/>:<Search size={15}/>}</button></form>
    {places.length>0&&<div className="stop-matches">{places.map(place=><button key={place.source_id} onClick={()=>{setPoint(stop.id,{coordinates:place.center,label:place.name.slice(0,160),source:'OSM place reference',source_id:place.source_id,anchor_method:'geocoder_reference'});setPlaces([])}}><MapPin size={13}/><span>{place.name}<small>{place.type} · {place.source_id}</small></span></button>)}</div>}
    {facilities.length>0&&<div className="stop-matches">{facilities.map(feature=><button key={feature.id} disabled={busy} onClick={()=>chooseFeature(feature)}><Database size={13}/><span>{feature.properties.name}<small>{feature.properties.categories.join(' · ')} · {feature.geometry.type}</small></span></button>)}</div>}
    {message&&<p className="stop-message">{message}</p>}
  </article>
}
