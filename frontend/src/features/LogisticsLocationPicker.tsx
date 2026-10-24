import {useState} from 'react'
import {Button} from '../components/ui/button'
import {parseCoordinates} from '../services/api'
import {resolveLocation,type PlaceMatch} from '../services/discovery'
import {findRoutingFacilities,getFeatureAnchor} from '../services/routing'
import type {SpatialFeature} from '../types'
import type {RoutingPoint} from '../types/routing'
import {useWorkspace} from '../store/workspace'
import {useAnalyses} from '../store/analytics'
export function LogisticsLocationPicker({onAdd,onPick}:{onAdd:(p:RoutingPoint)=>void;onPick:()=>void}){
 const [source,setSource]=useState('facility'),[text,setText]=useState(''),[places,setPlaces]=useState<PlaceMatch[]>([]),[features,setFeatures]=useState<SpatialFeature[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const layers=useAnalyses(s=>s.layers)
 async function search(){setBusy(true);setError('');setPlaces([]);setFeatures([]);try{
 const c=parseCoordinates(text)
 if(source==='place'&&c)onAdd({coordinates:c,label:'User coordinate reference'})
 else if(source==='place')setPlaces((await resolveLocation(text)).matches)
 else setFeatures((await findRoutingFacilities(text)).features.filter(f=>!f.properties.synthetic))
 }catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function feature(id:string){setBusy(true);setError('');try{onAdd(await getFeatureAnchor(id))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <div className="logistics-location-picker">
 <div className="logistics-inline"><label>Source<select aria-label="Logistics location source" value={source} onChange={e=>{setSource(e.target.value);setFeatures([]);setPlaces([])}}><option value="facility">Imported GIS facilities</option><option value="place">Place / coordinates</option></select></label><label>Location search<input aria-label="Logistics location search" placeholder="Warehouse name, city or lng,lat" value={text} onChange={e=>setText(e.target.value)}/></label></div>
 <div className="logistics-actions"><Button variant="outline" size="sm" disabled={busy||(source==='place'&&text.length<2)} onClick={search}>{busy?'Searching…':'Search locations'}</Button><Button variant="outline" size="sm" onClick={onPick}>Pick location on map</Button><Button variant="ghost" size="sm" disabled={busy||!useWorkspace.getState().selected||useWorkspace.getState().selected?.properties.synthetic} onClick={()=>{const f=useWorkspace.getState().selected;if(f)feature(f.id)}}>Use selected GIS feature</Button></div>
 {features.length>0&&<p className="logistics-muted">Up to 25 matches. Refine the name if needed. Add only candidate locations relevant to your scenario.</p>}
 <div className="logistics-matches">{features.map(f=><button key={f.id} disabled={busy} onClick={()=>feature(f.id)}>{f.properties.name}<small>{f.properties.categories.join(', ')} · {f.properties.source_id} · representative point</small></button>)}
 {places.map(p=><button key={p.source_id} onClick={()=>onAdd({coordinates:p.center,label:p.name.slice(0,160),source_id:p.source_id})}>{p.name}<small>{p.source_id} · place reference, entrance unverified</small></button>)}</div>
 {layers.length>0&&<details><summary>Reuse loaded GIS analysis points</summary><p className="logistics-muted">Only point results are eligible. Open a saved analysis in Saved Analyses first.</p>{layers.map(l=><div key={l.id}><strong>{l.result.title}</strong>{l.result.features.filter(f=>f.geometry.type==='Point').slice(0,20).map((f,i)=><button key={i} className="logistics-point-choice" onClick={()=>{if(f.geometry.type==='Point')onAdd({coordinates:f.geometry.coordinates as [number,number],label:String(f.properties?.name??l.result.title).slice(0,160),source:'Saved GIS analysis '+l.id,source_id:typeof f.properties?.source_id==='string'?f.properties.source_id:undefined})}}>Add {String(f.properties?.name??f.id??i+1)}</button>)}</div>)}</details>}
 {error&&<p role="alert" className="logistics-error">{error}</p>}
 </div>
}
