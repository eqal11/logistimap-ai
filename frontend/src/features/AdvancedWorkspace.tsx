import {useEffect,useRef,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer} from 'recharts'
import {Button} from '../components/ui/button'
import {MapWorkspace,type MapHandle} from './MapWorkspace'
import {AnalysisLayerPicker} from './AnalysisLayerPicker'
import {AnalysisNetworkPanel} from './AnalysisNetworkPanel'
import {useAnalyses} from '../store/analytics'
import {useWorkspace} from '../store/workspace'
import {analyze,matrix,compareRegions,getHistory,openSaved,saveAnalysis,archiveSaved,restoreSaved,exportCSV,operationLabels,type LayerInput,type Operation,type AnalysisResult,type HistoryItem} from '../services/analytics'
import {downloadGeoJSON,parseCoordinates} from '../services/api'
import {resolveLocation} from '../services/discovery'
import type {RoutingPoint} from '../types/routing'
import {useRouting} from '../store/routing'
const bbox:[number,number,number,number]=[101.25,2.72,101.87,3.75]
const blank:LayerInput={query:{categories:['industrial'],bbox}}
const regionNames=['Tanjong Malim, Perak, Malaysia','Rawang, Selangor, Malaysia','Shah Alam, Selangor, Malaysia','Bukit Raja, Selangor, Malaysia','Klang, Selangor, Malaysia','Port Klang, Selangor, Malaysia']
export function AdvancedWorkspace({module,onLog}:{module:string;onLog:(s:string)=>void}){
 const {layers,activeId,add,toggle,remove,activate}=useAnalyses()
 const [operation,setOperation]=useState<Operation>('buffer'),[title,setTitle]=useState(''),[a,setA]=useState<LayerInput>(blank),[b,setB]=useState<LayerInput>({...blank,query:{...blank.query!,categories:['industrial_park']}})
 const [distance,setDistance]=useState('5'),[unit,setUnit]=useState('km'),[predicate,setPredicate]=useState('intersects'),[eps,setEps]=useState('1000'),[min,setMin]=useState('3'),[grid,setGrid]=useState('1000'),[group,setGroup]=useState('all')
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[note,setNote]=useState(''),[heat,setHeat]=useState(false),[showInputs,setShowInputs]=useState(true)
 const [kind,setKind]=useState<'analyses'|'routes'>(module==='route-history'?'routes':'analyses'),[offset,setOffset]=useState(0),[pendingDelete,setPendingDelete]=useState<HistoryItem|null>(null),[lastArchive,setLastArchive]=useState<{kind:string;id:string}|null>(null)
 const [origins,setOrigins]=useState<RoutingPoint[]>([]),[destinations,setDestinations]=useState<RoutingPoint[]>([]),[reference,setReference]=useState('60')
 const [pick,setPick]=useState<'origin'|'destination'|null>(null),[regionText,setRegionText]=useState(regionNames.join('\n')),[radius,setRadius]=useState('5')
 const [selected,setSelected]=useState<{id?:string|number;properties:Record<string,unknown>|null}|null>(null),[tablePage,setTablePage]=useState(0)
 const abort=useRef<AbortController|null>(null),token=useRef(0),map=useRef<MapHandle>(null),mapBox=useRef<HTMLDivElement>(null)
 const active=layers.find(l=>l.id===activeId)?.result
 const history=useQuery({queryKey:['analysis-history',kind,offset],queryFn:({signal})=>getHistory(kind,offset,signal),enabled:['saved-analyses','route-history'].includes(module)})
 useEffect(()=>{setKind(module==='route-history'?'routes':'analyses');setOffset(0);setError('');setSelected(null)},[module])
 useEffect(()=>()=>abort.current?.abort(),[])
 useEffect(()=>{setTablePage(0);setSelected(null)},[activeId])
 function fit(r:AnalysisResult){const all:number[][]=[];function positions(v:unknown){if(!Array.isArray(v))return;if(typeof v[0]==='number')all.push(v as number[]);else v.forEach(positions)}
 r.features.forEach(f=>{if('coordinates' in f.geometry)positions(f.geometry.coordinates)})
 if(all.length)map.current?.fit([Math.min(...all.map(p=>p[0])),Math.min(...all.map(p=>p[1])),Math.max(...all.map(p=>p[0])),Math.max(...all.map(p=>p[1]))])}
 async function work(fn:(signal:AbortSignal)=>Promise<AnalysisResult>){
 abort.current?.abort();abort.current=new AbortController();const seq=++token.current
 setBusy(true);setError('');setNote('')
 try{const r=await fn(abort.current.signal);if(seq!==token.current)return;add(r);fit(r);onLog(r.title+' · '+r.features.length+' output features');setNote('Completed · '+r.features.length+' geometries · '+r.executed_at)}
 catch(e){if(seq===token.current&&!abort.current?.signal.aborted)setError((e as Error).message)}finally{if(seq===token.current)setBusy(false)}
 }
 function runSpatial(){const op=module==='clusters'?(operation==='grid'?'grid':'clusters'):operation;work(signal=>analyze({operation:op,title:title||operationLabels[op],a,b:['buffer','intersection','clip','difference','spatial_join','nearest','aggregate','union'].includes(op)?b:undefined,distance_m:Number(distance)*(unit==='km'?1000:1),predicate,eps_m:Number(eps),min_points:Number(min),grid_m:Number(grid),dissolve_by:group,crs:'EPSG:4326'},signal))}
 async function regionComparison(signal:AbortSignal){
 const points:RoutingPoint[]=[]
 const lines=regionText.split('\n').map(x=>x.trim()).filter(Boolean);if(!lines.length||lines.length>6)throw new Error('Provide 1–6 study references')
 for(const line of lines){const [name,coords]=line.split('|');const c=coords?parseCoordinates(coords):null
 if(coords&&!c)throw new Error('Invalid coordinate reference: '+name)
 if(c)points.push({coordinates:c,label:name});else {const found=await resolveLocation(name,signal);if(!found.matches.length)throw new Error('No geocoder match for '+name)
 const p=found.matches[0];points.push({coordinates:p.center,label:p.name.slice(0,160),source_id:p.source_id})}}
 if(signal.aborted)throw new Error('Cancelled')
 return compareRegions(points,Number(radius),['industrial','industrial_park'],signal)
 }
 const spatial=['toolbox','clusters'].includes(module),network=module==='accessibility',regional=module==='industrial-accessibility',saved=['saved-analyses','route-history'].includes(module)
 const op=module==='clusters'?(operation==='grid'?'grid':'clusters'):operation
 const rows:Record<string,unknown>[]=active?.rows.length?active.rows:active?.features.map(f=>({id:f.id,...f.properties}))??[]
 const columns=[...new Set(rows.flatMap(r=>Object.keys(r)))]
 const chartData=active?.statistics.matched_category_counts??active?.statistics.category_counts??active?.statistics.category_counts_a
 const chartRows=chartData&&typeof chartData==='object'?Object.entries(chartData).map(([name,value])=>({name,value})):active?.operation==='region_comparison'?active.rows.map(r=>({name:String(r.name).split(',')[0],value:r.objects_per_km2})):active?.operation==='clusters'?active.rows.map(r=>({name:'Cluster '+r.cluster_id,value:r.count})):[]
 return <section className="advanced-workspace" aria-label="Advanced spatial analytics">
 <div className="analysis-notice"><strong>Calculated spatial evidence</strong><span>Real imported records · EPSG:4326 output · source coverage limits apply</span></div>
 <div className="analysis-layout"><aside className="analysis-controls">
 {spatial&&<><div className="analysis-section-title"><small>ANALYSIS CONFIGURATION</small><h2>{module==='clusters'?'Industrial concentration':'Spatial Analysis Toolbox'}</h2></div>
 <label>Operation<select aria-label="Spatial operation" value={op} onChange={e=>setOperation(e.target.value as Operation)}>{Object.entries(operationLabels).filter(([id])=>module==='clusters'?['clusters','grid'].includes(id):true).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>
 <label>Analysis title<input aria-label="Analysis title" placeholder={operationLabels[op]} value={title} onChange={e=>setTitle(e.target.value)}/></label>
 <AnalysisLayerPicker label="Input A" value={a} onChange={setA}/>
 {['buffer','intersection','clip','difference','spatial_join','nearest','aggregate','union'].includes(op)&&<AnalysisLayerPicker label="Input B" value={b} onChange={setB}/>}
 {op==='buffer'&&<div className="analysis-inline"><label>Buffer distance<input aria-label="Buffer distance" type="number" min=".001" value={distance} onChange={e=>setDistance(e.target.value)}/></label><label>Units<select aria-label="Buffer units" value={unit} onChange={e=>setUnit(e.target.value)}><option value="km">km</option><option value="m">meters</option></select></label></div>}
 {['spatial_join','aggregate'].includes(op)&&<label>Predicate A relative to B<select value={predicate} onChange={e=>setPredicate(e.target.value)}><option value="intersects">Intersects (includes boundary)</option><option value="within">Within (excludes boundary-only)</option><option value="contains">Contains</option><option value="nearest">Nearest footprint</option></select></label>}
 {['union','dissolve'].includes(op)&&<label>Dissolve grouping<select value={group} onChange={e=>setGroup(e.target.value)}><option value="all">All features</option><option value="category">Category membership set</option></select></label>}
 {op==='clusters'&&<div className="analysis-inline"><label>DBSCAN epsilon meters<input aria-label="DBSCAN epsilon meters" type="number" min="25" max="20000" value={eps} onChange={e=>setEps(e.target.value)}/></label><label>Minimum points<input aria-label="DBSCAN minimum points" type="number" min="2" max="100" value={min} onChange={e=>setMin(e.target.value)}/></label></div>}
 {op==='grid'&&<label>Grid resolution meters<input aria-label="Grid resolution meters" type="number" min="100" max="20000" value={grid} onChange={e=>setGrid(e.target.value)}/></label>}
 <Button disabled={busy} onClick={runSpatial}>{busy?'Processing geometry…':'Run spatial analysis'}</Button>
 <p className="analysis-small">Bounded local metric CRS. Density is mapped-object concentration, not economic activity. DBSCAN is descriptive, not a significance test. Buffer matches use supplied B only.</p></>}
 {network&&<><div className="analysis-section-title"><small>ROAD NETWORK EVIDENCE</small><h2>Accessibility matrix</h2></div>
 <AnalysisNetworkPanel origins={origins} destinations={destinations} onOrigins={setOrigins} onDestinations={setDestinations} onPick={role=>{setPick(role);useWorkspace.getState().setTool('select');mapBox.current?.scrollIntoView({block:'center'})}}/>
 <label>Score reference minutes<input aria-label="Accessibility score reference minutes" type="number" min="1" max="240" value={reference} onChange={e=>setReference(e.target.value)}/></label>
 <Button disabled={busy||!origins.length||!destinations.length} onClick={()=>work(signal=>matrix(origins,destinations,Number(reference),signal))}>Calculate road matrix</Button>
 <p className="analysis-small">Score = 100 / (1 + minutes/reference). Unreachable = 0. Transparent travel-time heuristic, not validated site suitability. Matrix contains metrics, no route geometry.</p></>}
 {regional&&<><div className="analysis-section-title"><small>COMPARABLE STUDY WINDOWS</small><h2>Industrial accessibility</h2></div>
 <p className="analysis-small">One public place name per line (first geocoder match will be reported), or Name|longitude,latitude for an exact reference. Review resolved inputs after calculation. No city point is claimed as a verified industrial gate.</p>
 <label>Study references<textarea aria-label="Study references" rows={8} value={regionText} onChange={e=>setRegionText(e.target.value)}/></label><label>Study radius km<input aria-label="Comparison radius km" type="number" min=".1" max="50" value={radius} onChange={e=>setRadius(e.target.value)}/></label>
 <Button disabled={busy} onClick={()=>work(regionComparison)}>Compare industrial areas</Button><p className="analysis-small">Counts/density, mapped road segments and geography proximity to warehouse, port, airport and hub. Use Network Accessibility with exact references for road travel metrics.</p></>}
 {saved&&<><div className="analysis-section-title"><small>PERSISTED POSTGIS RECORDS</small><h2>{kind==='routes'?'Saved route history':'Saved analyses'}</h2></div>
 <Button size="sm" variant="outline" disabled={history.isFetching} onClick={()=>history.refetch()}>Refresh history</Button>
 <p className="analysis-small">{history.data?.total??0} active saved records. Open multiple records to compare them as layers. Delete archives a record; original geometry/provenance remain stored.</p>
 {history.isLoading&&<p role="status">Loading history…</p>}{history.error&&<p role="alert">{history.error.message}</p>}
 {history.data?.items.length===0&&<p>No saved records yet. Save a completed result first.</p>}
 {history.data?.items.map(item=><article className="saved-analysis-card" key={item.id}><strong>{item.title||'Saved route'}</strong><small>{item.created_at} · {item.operation??item.provider}</small>{item.distance_m!=null&&<p>{(item.distance_m/1000).toFixed(2)} km · {Math.round((item.duration_s??0)/60)} min · car</p>}<div className="analysis-inline"><Button size="sm" variant="outline" disabled={busy} onClick={()=>work(signal=>openSaved(kind,item.id,signal))}>Open saved {kind==='routes'?'route':'analysis'}</Button><Button size="sm" variant="ghost" onClick={()=>setPendingDelete(item)}>Delete</Button></div></article>)}
 <div className="analysis-inline"><Button variant="ghost" size="sm" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous records</Button><Button variant="ghost" size="sm" disabled={offset+25>=(history.data?.total??0)} onClick={()=>setOffset(offset+25)}>Next records</Button></div>
 {pendingDelete&&<div role="dialog" aria-label="Confirm saved record deletion" className="analysis-confirm"><strong>Delete this saved record from active history?</strong><p>{pendingDelete.title}. Original row/geometry will be retained as an archive.</p><Button onClick={async()=>{try{await archiveSaved(kind,pendingDelete.id);setLastArchive({kind,id:pendingDelete.id});setPendingDelete(null);setNote('Record archived; original data retained.');history.refetch()}catch(e){setError((e as Error).message)}}}>Confirm delete</Button><Button variant="outline" onClick={()=>setPendingDelete(null)}>Cancel deletion</Button></div>}
 </>}
 {lastArchive&&<Button variant="outline" size="sm" onClick={async()=>{try{await restoreSaved(lastArchive.kind,lastArchive.id);setLastArchive(null);setNote("Archived record restored.");history.refetch()}catch(e){setError((e as Error).message)}}}>Undo last deletion</Button>}
 {busy&&<p role="status" className="analysis-small">Processing bounded spatial request…</p>}
 {busy&&<Button variant="outline" onClick={()=>{++token.current;abort.current?.abort();setBusy(false);setNote('Browser request cancelled. Server work already started may finish safely.')}}>Cancel analysis request</Button>}
 {error&&<p role="alert" className="analysis-error">{error}</p>}{note&&<p role="status" className="analysis-feedback">{note}</p>}
 </aside>
 <div className="analysis-main"><div className="analysis-map-heading"><div><small>SPATIAL RESULTS WORKSPACE</small><h2>{active?.title??'Configure an analysis'}</h2></div><Button size="sm" variant="outline" disabled={!active?.features.length} onClick={()=>active&&fit(active)}>Zoom to result</Button></div>
 {pick&&<div className="analysis-pick">Click map to add {pick}. <button onClick={()=>setPick(null)}>Cancel map picking</button></div>}
 <div className="analysis-map" ref={mapBox}><MapWorkspace ref={map} initialBbox={bbox} onLog={onLog} onViewport={()=>{}} analysisLayers={active?.input_features&&showInputs?[{id:'input-context',result:{...active,features:active.input_features},visible:true,color:'#8796a5'},...layers]:layers} analysisHeatmap={heat} onAnalysisSelect={setSelected} pickingRoutePoint={!!pick} onRoutePoint={coordinates=>{if(pick==='origin')setOrigins([...origins,{coordinates,label:'Map origin '+coordinates.map(n=>n.toFixed(5)).join(',')}].slice(0,5));else setDestinations([...destinations,{coordinates,label:'Map destination '+coordinates.map(n=>n.toFixed(5)).join(',')}].slice(0,5));setPick(null)}}/></div>
 <div className="analysis-layer-bar"><strong>Result layers · {layers.length}/5</strong><label><input type="checkbox" checked={showInputs} onChange={e=>setShowInputs(e.target.checked)}/>Input geometries</label><label><input type="checkbox" checked={heat} disabled={!layers.some(l=>l.visible&&l.result.features.some(f=>['density_point','cluster_point'].includes(String(f.properties?.role))))} onChange={e=>setHeat(e.target.checked)}/>Heatmap (representative points)</label>{layers.map(l=><div key={l.id}><input aria-label={'Show '+l.result.title} type="checkbox" checked={l.visible} onChange={()=>toggle(l.id)}/><i style={{background:l.color}}/><button className={activeId===l.id?'active-result':''} onClick={()=>activate(l.id)}>{l.result.title}</button><button aria-label={'Remove layer '+l.result.title} onClick={()=>remove(l.id)}>×</button></div>)}</div>
 {active?.operation==='grid'&&<p className="analysis-scale">Grid fill: mapped objects/km² · 0 (pale) → 2 → 10 → 50+ (dark). Occupied cells only. Heatmap is zoom-dependent visual concentration, not calibrated density.</p>}
 {active?.operation==='clusters'&&<p className="analysis-scale">Cluster colors repeat every 5 IDs; inspect cluster_id in attributes. −1 = noise (gray). Hulls only for non-degenerate groups &gt;1 m²; descriptive shapes, not industrial boundaries.</p>}
 {layers.filter(l=>l.result.operation==='saved_route').length>1&&<div className="analysis-results"><strong>Saved route comparison · car estimates</strong><div className="analysis-table"><table><thead><tr><th>Route</th><th>km</th><th>minutes</th></tr></thead><tbody>{layers.filter(l=>l.result.operation==='saved_route').map(l=><tr key={l.id} onClick={()=>activate(l.id)}><td>{l.result.title}</td><td>{(Number(l.result.statistics.distance_m)/1000).toFixed(2)}</td><td>{(Number(l.result.statistics.duration_s)/60).toFixed(2)}</td></tr>)}</tbody></table></div></div>}
 {selected&&<details className="analysis-selected" open><summary>Selected result attributes</summary><pre>{JSON.stringify({id:selected.id,...selected.properties},null,2)}</pre></details>}
 {active?<section className="analysis-results"><div className="analysis-result-actions"><Button size="sm" variant="outline" onClick={()=>downloadGeoJSON(active,'logistimap-'+active.operation+'.geojson')}>Export result GeoJSON</Button><Button size="sm" variant="outline" onClick={()=>exportCSV(active)}>Download CSV statistics</Button><Button size="sm" disabled={busy||!active.calculation_id} onClick={async()=>{try{setBusy(true);const receipt=await saveAnalysis(active.calculation_id!);add({...active,saved_id:receipt.id});setNote('Saved analysis to PostGIS · '+receipt.id)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Save analysis to PostGIS</Button></div>
 <div className="analysis-metadata"><span>{active.status} · {active.operation}</span><span>{active.features.length} geometries · {active.crs}</span><span>{active.executed_at}</span>{active.saved_id&&<span>Saved · {active.saved_id}</span>}</div>
 {active.operation==='matrix'&&Array.isArray(active.statistics.nearest_by_time)&&<div className="analysis-network-nearest"><strong>Fastest supplied destination per origin</strong>{(active.statistics.nearest_by_time as Record<string,unknown>[]).map((row,i)=><article key={i}><span>{String(row.origin)} → {String(row.destination)}</span><small>{(Number(row.distance_m)/1000).toFixed(2)} km · {(Number(row.duration_s)/60).toFixed(2)} min · score {String(row.accessibility_score)}/100</small><Button variant="outline" size="sm" onClick={()=>{const origins=active.inputs.origins as RoutingPoint[],destinations=active.inputs.destinations as RoutingPoint[];useRouting.getState().reset();useRouting.getState().setEndpoint('origin',origins[Number(row.origin_index)]);useRouting.getState().setEndpoint('destination',destinations[Number(row.destination_index)]);location.hash='routing'}}>Inspect pair in road planner</Button></article>)}</div>}
 <div className="analysis-statistics">{Object.entries(active.statistics).filter(([,v])=>typeof v==='number').map(([key,v])=><div key={key}><small>{key.replaceAll('_',' ')}</small><strong>{typeof v==='number'?v.toLocaleString('en-MY',{maximumFractionDigits:3}):String(v)}</strong></div>)}</div>
 {active.features.length===0&&<p className="analysis-empty">No result geometry. The operation completed with an empty result; no substitute features were generated.</p>}
 {chartRows.length>0&&<div className="analysis-chart"><h3>{active.operation==='region_comparison'?'Mapped objects per km²':active.operation==='buffer'?'Matched category memberships (overlap allowed)':'Input category memberships (overlap allowed)'}</h3><ResponsiveContainer width="100%" height={190}><BarChart data={chartRows}><XAxis dataKey="name" tick={{fontSize:10}}/><YAxis/><Tooltip/><Bar dataKey="value" fill="#0d9c89"/></BarChart></ResponsiveContainer></div>}
 <details className="analysis-method"><summary>Inputs, parameters, methodology & limitations</summary><p>{active.attribution}</p>{active.warnings.map(w=><p key={w}>{w}</p>)}<pre>{JSON.stringify({inputs:active.inputs,parameters:active.parameters,calculation_crs:active.calculation_crs},null,2)}</pre></details>
 <div className="analysis-table-heading"><strong>Result attributes · {rows.length} rows</strong><div><Button size="sm" variant="ghost" disabled={!tablePage} onClick={()=>setTablePage(tablePage-1)}>Previous rows</Button><Button size="sm" variant="ghost" disabled={(tablePage+1)*100>=rows.length} onClick={()=>setTablePage(tablePage+1)}>Next rows</Button></div></div>
 <p className="analysis-small">Scroll horizontally for all columns; click a row to inspect its full attributes.</p><div className="analysis-table"><table><thead><tr>{columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{rows.slice(tablePage*100,(tablePage+1)*100).map((row,i)=><tr key={i} onClick={()=>setSelected({id:String(row.id??row.input_id??row.cluster_id??(tablePage*100+i)),properties:row})}>{columns.map(c=><td key={c}>{typeof row[c]==='object'?JSON.stringify(row[c]):String(row[c]??'Unknown')}</td>)}</tr>)}</tbody></table></div>
 </section>:<div className="analysis-empty"><h3>Analysis results will appear here</h3><p>Configure bounded inputs, run an operation or open a saved record. No precomputed industrial statistics are shown.</p></div>}
 </div></div></section>
}
