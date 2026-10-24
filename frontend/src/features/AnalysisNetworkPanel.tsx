import {useState} from 'react'
import {Button} from '../components/ui/button'
import {parseCoordinates} from '../services/api'
import {resolveLocation,type PlaceMatch} from '../services/discovery'
import {findRoutingFacilities,getFeatureAnchor} from '../services/routing'
import type {RoutingPoint} from '../types/routing'
import type {SpatialFeature} from '../types'
import {useRouting} from '../store/routing'
export function AnalysisNetworkPanel({origins,destinations,onOrigins,onDestinations,onPick}:{origins:RoutingPoint[];destinations:RoutingPoint[];onOrigins:(p:RoutingPoint[])=>void;onDestinations:(p:RoutingPoint[])=>void;onPick:(role:'origin'|'destination')=>void}){
 const [target,setTarget]=useState<'origin'|'destination'>('origin'),[kind,setKind]=useState('place'),[text,setText]=useState('')
 const [places,setPlaces]=useState<PlaceMatch[]>([]),[features,setFeatures]=useState<SpatialFeature[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 function add(p:RoutingPoint){if((target==='origin'?origins:destinations).length>=5){setError('Maximum five references per side');return}
 if(target==='origin')onOrigins([...origins,p]);else onDestinations([...destinations,p]);setPlaces([]);setFeatures([])}
 async function search(){setBusy(true);setError('');setPlaces([]);setFeatures([]);try{const c=parseCoordinates(text)
 if(kind==='place'&&c)add({coordinates:c,label:'User reference '+text})
 else if(kind==='place')setPlaces((await resolveLocation(text)).matches)
 else setFeatures((await findRoutingFacilities(text)).features.filter(f=>!f.properties.synthetic))
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <div className="network-config">
 <p className="analysis-small">Up to 5 origins × 5 destinations. Road nearest ranks only supplied candidates by estimated car time. Choose exact references; footprints are not verified gates.</p>
 <div className="analysis-inline"><label>Add to<select value={target} onChange={e=>setTarget(e.target.value as typeof target)} aria-label="Reference role"><option value="origin">Origins</option><option value="destination">Destinations</option></select></label><label>Source<select aria-label="Network reference source" value={kind} onChange={e=>setKind(e.target.value)}><option value="place">Place / coordinates</option><option value="facility">Imported GIS feature</option></select></label></div>
 <div className="analysis-inline"><input aria-label="Network reference search" placeholder="Name or longitude,latitude" value={text} onChange={e=>setText(e.target.value)}/><Button size="sm" variant="outline" disabled={busy||text.length<2} onClick={search}>{busy?'Searching…':'Search reference'}</Button></div>
 {places.map(p=><button className="analysis-match" key={p.source_id} onClick={()=>add({coordinates:p.center,label:p.name,source_id:p.source_id})}>{p.name}<small>{p.source_id} · geocoder reference</small></button>)}
 {features.map(f=><button className="analysis-match" key={f.id} disabled={busy} onClick={async()=>{setBusy(true);try{add(await getFeatureAnchor(f.id))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>{f.properties.name}<small>{f.properties.categories.join(', ')} · {f.geometry.type}</small></button>)}
 <div className="analysis-inline"><Button size="sm" variant="outline" onClick={()=>onPick(target)}>Pick {target} on map</Button><Button size="sm" variant="ghost" onClick={()=>{const stops=useRouting.getState().stops;if(stops.some(s=>!s.point)){setError('Complete references in Freight Route Planner first');return}onOrigins([stops[0].point!]);onDestinations(stops.slice(1,6).map(s=>s.point!))}}>Use current route stops</Button></div>
 {([['Origins',origins,onOrigins],['Destinations',destinations,onDestinations]] as const).map(([name,points,update])=><section key={name}><strong>{name} · {points.length}/5</strong>{points.map((p,i)=><div className="network-reference" key={i}><span>{p.label}<small>{p.coordinates?.join(', ')} {p.feature_id?' · imported geometry reference':''}</small></span><button aria-label={'Remove '+name+' '+(i+1)} onClick={()=>update(points.filter((_,j)=>j!==i))}>×</button></div>)}</section>)}
 {error&&<p role="alert" className="analysis-error">{error}</p>}
 <div className="analysis-unavailable"><strong>Network isochrones unavailable</strong><p>10 / 20 / 30 / 45 / 60 min: current OSRM route/table provider has no isochrone endpoint. Imported roads are not a validated directed routing graph. No circular substitute is generated.</p></div>
 </div>
}
