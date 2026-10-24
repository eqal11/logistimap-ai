import {useEffect,useMemo,useRef,useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Play,Save,Download,Printer} from 'lucide-react'
import {Button} from '../components/ui/button'
import {MapWorkspace,type MapHandle} from './MapWorkspace'
import {LogisticsForms} from './LogisticsForms'
import {LogisticsComparison,ComparisonResults} from './LogisticsComparison'
import {comparisonGeoJSON,routeKey,type SavedComparison,type ComparisonOverlay} from '../services/comparisons'
import {useOptimization} from '../store/optimization'
import {useWorkspace} from '../store/workspace'
import {newScenario,optimizationBounds,saveScenario,listScenarios,openScenario,getResults,startSolve,getJob,post,optimizationGeoJSON,exportOptimizationCSV,vehicleColors,clockLabel,type ScenarioItem,type OptimizationResult} from '../services/optimization'
import {downloadGeoJSON} from '../services/api'
import {distanceLabel,durationLabel} from '../services/routing'
import type {Feature,FeatureCollection} from 'geojson'
import '../styles/optimization.css'
const tabs=['Scenario Builder','Fleet','Delivery Locations','Results','Comparison','Saved Scenarios']
export const money=(n:number)=>'RM '+n.toLocaleString('en-MY',{minimumFractionDigits:2,maximumFractionDigits:2})
export function LogisticsOptimization({onLog}:{onLog:(s:string)=>void}){
 const {scenario:s,result,savedId,jobId,jobScenarioId,load,setResult,setJob}=useOptimization()
 const [tab,setTab]=useState('Scenario Builder'),[error,setError]=useState(''),[note,setNote]=useState(''),[busy,setBusy]=useState(false),[stage,setStage]=useState(''),[pick,setPick]=useState<'depot'|'delivery'|null>(null),[selectedVehicle,setSelectedVehicle]=useState<string|null>(null),[hidden,setHidden]=useState<string[]>([])
 const [offset,setOffset]=useState(0),[archived,setArchived]=useState(false),[comparison,setComparison]=useState<SavedComparison|null>(null),[overlay,setOverlay]=useState<ComparisonOverlay|null>(null),[pendingArchive,setPendingArchive]=useState<ScenarioItem|null>(null),[matrixOpen,setMatrixOpen]=useState(false)
 const map=useRef<MapHandle>(null),mapBox=useRef<HTMLDivElement>(null)
 const picked=useRef<((coordinates:[number,number])=>void)|null>(null)
 const history=useQuery({queryKey:['logistics-history',offset,archived],queryFn:({signal})=>listScenarios(offset,archived,signal),enabled:tab==='Saved Scenarios'})
 const operating=busy||!!jobId
 async function task(fn:()=>Promise<void>){setBusy(true);setError('');setNote('');try{await fn()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function save(andSolve=false){await task(async()=>{
 if(!s.depots.length||!s.vehicles.length||!s.stops.length)throw new Error('Add a depot, at least one vehicle and at least one delivery candidate.')
 const saved=savedId?{id:savedId,scenario:s}:await saveScenario(s)
 load(saved.scenario,saved.id,result);setNote('Saved immutable scenario snapshot. Editing creates a new version.')
 if(andSolve){const job=await startSolve(saved.id);setJob(job.job_id,saved.id);setStage('Queued');setTab('Results');onLog('Optimization queued · '+s.name)}
 })}
 useEffect(()=>{
 if(!jobId||!jobScenarioId)return
 const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined
 async function poll(){try{
 const job=await getJob(jobId!,controller.signal);if(controller.signal.aborted)return
 setStage(job.stage)
 if(job.status==='completed'){
 const r=await getResults(jobScenarioId!);if(controller.signal.aborted)return
 setResult(r);setJob(null,null);setNote('Solution saved · '+r.status+' · '+r.summary.assigned_stops+' assigned stops');setSelectedVehicle(r.routes[0]?.vehicle_id??null)
 onLog('Optimization '+r.status+' · '+r.summary.vehicles_used+' vehicles · '+r.summary.unassigned_stops+' unassigned');return
 }
 if(['failed','cancelled','interrupted'].includes(job.status)){setError(job.stage);setJob(null,null);return}
 timer=setTimeout(poll,3000)
 }catch(e){if(!controller.signal.aborted){setError((e as Error).message+' · Polling will retry; background job may still be running.');timer=setTimeout(poll,6000)}}}
 poll();return()=>{controller.abort();if(timer)clearTimeout(timer)}
 },[jobId,jobScenarioId,setJob,setResult,onLog])
 const comparisonTab=tab==='Comparison'
 const comparisonMode=comparisonTab&&!!overlay
 const allGeo=useMemo(()=>result?optimizationGeoJSON(result):null,[result])
 const mapFeatures=useMemo<FeatureCollection>(()=>{
 if(comparisonTab)return overlay?comparisonGeoJSON(overlay):{type:'FeatureCollection',features:[]}
 if(allGeo)return {...allGeo,features:allGeo.features.filter(f=>!hidden.includes(String(f.properties?.vehicle_id)))}
 return {type:'FeatureCollection',features:[...s.depots.map((p):Feature=>({type:'Feature',id:p.id,geometry:{type:'Point',coordinates:p.coordinates},properties:{name:p.name,label:'D',color:'#087f80',role:'depot'}})),...s.stops.map((p,i):Feature=>({type:'Feature',id:p.id,geometry:{type:'Point',coordinates:p.coordinates},properties:{name:p.name,label:String(i+1),color:'#b77a24',role:'delivery'}}))]}
 },[allGeo,s.depots,s.stops,hidden,overlay,comparisonTab])
 function fit(){const bounds=optimizationBounds(comparisonTab?mapFeatures:allGeo??mapFeatures);if(bounds)map.current?.fit(bounds)}
 useEffect(()=>{if(result||comparisonMode)fit()},[result?.solution_id,comparisonMode?overlay?.comparison.id:undefined])
 async function open(id:string,withResults=false){await task(async()=>{
 const saved=await openScenario(id);let r:OptimizationResult|null=null;if(withResults)r=await getResults(id)
 load(saved.scenario,id,r);setHidden([]);setSelectedVehicle(r?.routes[0]?.vehicle_id??null);setTab(r?'Results':'Scenario Builder');setNote(saved.archived?'Archived snapshot opened for review; restore before solving.':'Saved scenario loaded.')
 })}
 const selectedComparison= comparisonMode?overlay?.items.flatMap(item=>item.result.routes.map(route=>({item,route,key:routeKey(item,route.vehicle_id)}))).find(x=>x.key===overlay.selectedRoute&&!overlay.hiddenScenarios.includes(x.item.scenario_id)&&!overlay.hiddenRoutes.includes(x.key)):undefined
 const route=comparisonTab?selectedComparison?.route:result?.routes.find(r=>r.vehicle_id===selectedVehicle)??result?.routes[0]
 const scheduledResult=comparisonTab?selectedComparison?.item.result:result
 const enabled=s.vehicles.filter(v=>v.enabled),totalDemand=s.stops.filter(p=>p.kind==='delivery').reduce((n,p)=>n+(Number.isFinite(p.demand)?p.demand:0),0)
 return <section className="logistics-workspace" aria-label="Logistics optimization workspace">
 <div className="logistics-hero"><div><span className="eyebrow">OPERATIONS RESEARCH · ROAD NETWORK</span><h2>Logistics Optimization</h2><p>Configure candidate deliveries. Solve constrained fleet routes. Inspect the evidence.</p></div><span className="logistics-mode">{s.demand_context==='hypothetical'?'HYPOTHETICAL DEMAND':'USER-SUPPLIED DEMAND'}</span></div>
 <div className="logistics-notice">OSRM car network · Google OR-Tools · Capacities and costs supplied by you. Truck restrictions, tolls and live traffic are unverified.</div>
 <nav className="logistics-tabs" aria-label="Optimization sections">{tabs.map(t=><button key={t} className={tab===t?'active':''} onClick={()=>{setTab(t);setPick(null);picked.current=null}}>{t}</button>)}</nav>
 <div className="logistics-actionbar"><div><strong>{s.name}</strong><small>{s.depots.length} depots · {enabled.length} enabled vehicles · {s.stops.length}/20 stops · {totalDemand} {s.capacity_unit} demand</small></div><div className="logistics-actions"><Button size="sm" variant="outline" disabled={operating} onClick={()=>save()}><Save size={14}/>Save scenario</Button><Button size="sm" disabled={operating} onClick={()=>save(true)}><Play size={14}/>{jobId?'Optimizing…':'Optimize routes'}</Button></div></div>
 {error&&<div role="alert" className="logistics-error">{error}<button aria-label="Dismiss optimization error" onClick={()=>setError('')}>×</button></div>}
 {note&&<p role="status" className="logistics-note">{note}</p>}
 {jobId&&<div role="status" className="logistics-progress"><span className="status-dot"/><strong>{stage||'Processing…'}</strong><small>One bounded job · request/solver stages may take up to 20 seconds each</small><Button size="sm" variant="outline" onClick={()=>task(async()=>{await post('/jobs/'+jobId+'/cancel',{confirmed:true});setNote('Cancellation requested; waiting for current bounded stage.')})}>Cancel job</Button></div>}
 <div className="logistics-layout"><aside className="logistics-config">
 {['Scenario Builder','Fleet','Delivery Locations'].includes(tab)&&<LogisticsForms tab={tab} disabled={operating} onError={setError} onNote={setNote} onTask={task} onFly={xy=>map.current?.flyTo(xy)} onPick={(role,callback)=>{picked.current=callback;setPick(role);useWorkspace.getState().setTool('select');mapBox.current?.scrollIntoView({block:'center'})}}/>}
 {tab==='Results'&&<><h3>Optimization evidence</h3>{!result?<p className="logistics-muted">{jobId?'Processing the saved scenario…':'No result yet. Configure a scenario and select Optimize routes.'}</p>:<>
 <span className="logistics-result-status">{result.status.replaceAll('_',' ')} · {result.proven_optimal?'solver established optimality for the integer model':'global optimality not established'}</span><p className="logistics-muted">{result.engine}<br/>{result.method}<br/>Solver status: {result.solver_status}<br/>{result.elapsed_s} s / {result.time_limit_s} s limit · Independent hard-constraint validation: {result.validated?'passed':'no feasible solution to validate'}</p>
 <div className="logistics-mini-stats"><span><strong>{distanceLabel(result.summary.distance_m)}</strong>matrix road distance</span><span><strong>{durationLabel(result.summary.travel_duration_s)}</strong>estimated driving</span><span><strong>{money(result.summary.estimated_cost)}</strong>supplied cost assumptions</span><span><strong>{result.summary.assigned_stops} / {result.scenario.stops.length}</strong>assigned stops</span></div>
 {result.routed_summary&&<div className="logistics-routed-summary"><strong>Final OSRM routes · road timing limits verified</strong><p>{distanceLabel(result.routed_summary.distance_m)} · {durationLabel(result.routed_summary.travel_duration_s)} driving · {money(result.routed_summary.estimated_cost)} estimated cost</p><small>Recalculated for the returned road geometry; solver objective and matrix schedule remain separately reported.</small></div>}
 <p className="logistics-muted">{result.summary.cost_per_delivery===undefined?'':money(result.summary.cost_per_delivery)+' per delivery · '}{result.summary.cost_per_km===undefined?'':money(result.summary.cost_per_km)+' per km · '}{result.summary.vehicles_used}/{result.summary.vehicles_available} vehicles used · {result.summary.assigned_demand}/{result.summary.total_demand} {result.scenario.capacity_unit} demand · {result.matrix.pairs} road matrix cells ({result.matrix.unreachable_pairs} unreachable).</p>
 {result.routes.map((r,i)=><div className={'logistics-route-card '+(route?.vehicle_id===r.vehicle_id?'selected':'')} key={r.vehicle_id}><div><label className="logistics-check"><input type="checkbox" aria-label={'Show '+r.vehicle_name} checked={!hidden.includes(r.vehicle_id)} onChange={()=>setHidden(hidden.includes(r.vehicle_id)?hidden.filter(x=>x!==r.vehicle_id):[...hidden,r.vehicle_id])}/><i style={{background:vehicleColors[i%6]}}/>{r.vehicle_name}</label><button aria-label={'Inspect '+r.vehicle_name} onClick={()=>{setSelectedVehicle(r.vehicle_id);const p=r.schedule[1];if(p)map.current?.flyTo(p.coordinates)}}>Inspect →</button></div><strong>{distanceLabel(r.distance_m)} · {durationLabel(r.travel_duration_s)}</strong><small>{r.stop_ids.length} stops · peak {r.peak_load}/{r.capacity} · {r.capacity_utilization_pct.toFixed(1)}% · {money(r.estimated_cost)}</small><small>Final road {r.geometry_distance_m===undefined?'unavailable':distanceLabel(r.geometry_distance_m)} · {r.geometry_duration_s===undefined?'':durationLabel(r.geometry_duration_s)}{r.geometry_estimated_cost==null?'':' · '+money(r.geometry_estimated_cost)}</small><small>Road geometry: {r.geometry_status} · road timing limits {r.road_geometry_constraints_verified===undefined?'not checked (older result)':r.road_geometry_constraints_verified?'verified':'not verified — replan'}{r.geometry_error?' · '+r.geometry_error:''}</small></div>)}
 {result.unassigned.length>0&&<div className="logistics-unassigned"><strong>{result.unassigned.length} unassigned stops</strong>{result.unassigned.map(p=><p key={p.id}>{p.name} · demand {p.demand}<small>{p.reason}</small></p>)}</div>}
 <details><summary>Matrix provenance & cells</summary><p>{result.matrix.method}</p><p>Retrieved {result.matrix.retrieved_at} · {result.matrix.cached?'cache hit':'fresh'} · cache 24 h · {result.matrix.upstream_requests} original table requests</p><Button size="sm" variant="outline" onClick={()=>setMatrixOpen(!matrixOpen)}>{matrixOpen?'Hide':'Show'} matrix cells</Button></details>
 <div className="logistics-actions"><Button size="sm" variant="outline" onClick={()=>downloadGeoJSON(optimizationGeoJSON(result),'logistimap-optimized-routes.geojson')}><Download size={14}/>GeoJSON</Button>{(['assignments','schedules','summary'] as const).map(k=><Button key={k} size="sm" variant="outline" onClick={()=>exportOptimizationCSV(result,k)}>CSV {k}</Button>)}<Button size="sm" variant="outline" onClick={()=>window.print()}><Printer size={14}/>Print report</Button></div>
 <details><summary>Assumptions & limitations ({result.warnings.length})</summary>{result.warnings.map((w,i)=><p key={i} className="logistics-muted">{w}</p>)}<pre>{JSON.stringify(result.scenario,null,2)}</pre></details>
 <p className="logistics-muted">{result.attribution} · <a href={result.policy_url} target="_blank" rel="noreferrer">Provider policy</a> · <a href={result.fix_map_url} target="_blank" rel="noreferrer">Fix the map</a></p>
 </>}</>}
 {tab==='Comparison'&&<LogisticsComparison comparison={comparison} onComparison={setComparison} overlay={overlay} onOverlay={setOverlay}/>}
 {tab==='Saved Scenarios'&&<><h3>{'Saved scenario snapshots'}</h3><label className="logistics-check"><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setOffset(0)}}/>Show archived scenarios only</label><Button size="sm" variant="outline" disabled={history.isFetching} onClick={()=>history.refetch()}>Refresh scenarios</Button>
 {history.isFetching&&<p role="status">Loading saved scenarios…</p>}{history.error&&<p role="alert" className="logistics-error">{history.error.message}</p>}{history.data?.items.length===0&&<p className="logistics-muted">No saved scenarios in this list.</p>}
 {history.data?.items.map(item=><div className="logistics-card" key={item.id}><strong>{item.name}</strong><small>{item.stops} stops · {item.objective} · {item.status} · {new Date(item.created_at).toLocaleString()}</small><div className="logistics-actions"><Button size="sm" variant="outline" disabled={operating} onClick={()=>open(item.id,false)}>Open scenario</Button><Button size="sm" variant="outline" disabled={operating||!item.summary} onClick={()=>open(item.id,true)}>Open result</Button><Button size="sm" variant="ghost" disabled={operating} onClick={()=>task(async()=>{const r=await post<{id:string;scenario:typeof s}>('/scenarios/'+item.id+'/duplicate');load(r.scenario,r.id);setTab('Scenario Builder');setNote('Scenario duplicated; original preserved.');history.refetch()})}>Duplicate</Button><Button size="sm" variant="ghost" disabled={operating} onClick={()=>setPendingArchive(item)}>{item.archived?'Restore':'Archive'}</Button></div></div>)}
 <div className="logistics-actions"><Button size="sm" variant="outline" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous</Button><small>{history.data?.total?offset+1:0}–{Math.min(offset+25,history.data?.total??0)} of {history.data?.total??0}</small><Button size="sm" variant="outline" disabled={offset+25>=(history.data?.total??0)} onClick={()=>setOffset(offset+25)}>Next</Button></div>
 {pendingArchive&&<div role="dialog" aria-modal="true" aria-label="Confirm scenario archive" className="logistics-confirm"><strong>{pendingArchive.archived?'Restore':'Archive'} “{pendingArchive.name}”?</strong><p>{pendingArchive.archived?'The snapshot becomes available for solving.':'Records and solutions are retained; the snapshot leaves the active list.'}</p><Button size="sm" disabled={busy} onClick={()=>task(async()=>{await post('/scenarios/'+pendingArchive.id+'/'+(pendingArchive.archived?'restore':'archive'),{confirmed:true});setPendingArchive(null);history.refetch()})}>Confirm {pendingArchive.archived?'restore':'archive'}</Button><Button variant="ghost" size="sm" onClick={()=>setPendingArchive(null)}>Cancel</Button></div>}
 </>}
 <hr/><Button variant="ghost" size="sm" disabled={operating} onClick={()=>{load(newScenario(),null);setComparison(null);setOverlay(null);setTab('Scenario Builder');setError('');setNote('New empty scenario. Saved records are preserved.') }}>New empty scenario</Button>
 </aside>
 <div className="logistics-map-column"><div ref={mapBox} className="logistics-map"><MapWorkspace ref={map} initialBbox={[101.2,2.85,101.8,3.5]} onViewport={()=>{}} onLog={onLog} optimizationData={mapFeatures} selectedOptimizationVehicle={comparisonMode?selectedComparison?.key:route?.vehicle_id} onOptimizationSelect={f=>{const key=f.properties?.vehicle_id;if(comparisonMode&&overlay&&key){setOverlay({...overlay,selectedRoute:String(key)});return}if(key&&result){const r=result.routes.find(x=>x.vehicle_id===key);if(r)setSelectedVehicle(r.vehicle_id)}}} pickingRoutePoint={!!pick} onRoutePoint={coordinates=>{picked.current?.(coordinates);setPick(null)}}/>
 {pick&&<div className="logistics-map-pick">Click an exact {pick} reference<Button size="sm" variant="outline" onClick={()=>setPick(null)}>Cancel pick</Button></div>}</div>
 <div className="logistics-map-footer"><span>{comparisonTab?(overlay?'Comparison road solutions · colour = scenario; dash = vehicle':'No comparison geometry loaded'):result?'Vehicle road geometries and ordered references':'Depots and candidate delivery references'} · EPSG:4326</span><Button size="sm" variant="outline" onClick={fit}>{comparisonMode?'Fit visible solutions':'Fit scenario'}</Button>{comparisonMode&&route?.geometry&&<Button size="sm" variant="outline" onClick={()=>{const b=optimizationBounds({type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:route.geometry!}]});if(b)map.current?.fit(b)}}>Fit selected route</Button>}</div>
 {scheduledResult&&route&&<section className="logistics-schedule"><h3>{selectedComparison?selectedComparison.item.name+' · ':''}{route.vehicle_name} · ordered schedule</h3><p>Service-start windows · seconds from day start; integer-rounded network travel. Peak onboard load {route.peak_load} {scheduledResult.scenario.capacity_unit}.</p><div className="logistics-table-scroll"><table><thead><tr><th>Stop</th><th>Location</th><th>Matrix arrival</th><th>Matrix departure</th><th>Road arrival</th><th>Road departure</th><th>Load before → after</th></tr></thead><tbody>{route.schedule.map((p,i)=><tr key={i} onClick={()=>map.current?.flyTo(p.coordinates)}><td>{p.kind==='depot'?'D':p.sequence}</td><td>{p.name}<small>{p.kind} · {p.source_id??'User reference'}</small></td><td>{clockLabel(p.arrival_s)}</td><td>{clockLabel(p.departure_s)}</td><td>{route.road_geometry_arrival_s?clockLabel(route.road_geometry_arrival_s[i]):'Unavailable'}</td><td>{route.road_geometry_arrival_s?clockLabel(route.road_geometry_arrival_s[i]+p.departure_s-p.arrival_s):'Unavailable'}</td><td>{p.load_before} → {p.load_after}</td></tr>)}</tbody></table></div><p className="logistics-muted">Cost = distance {money(route.cost_components.distance_cost)} + fixed {money(route.cost_components.fixed_cost)} + driver {money(route.cost_components.driver_cost)} + fuel {money(route.cost_components.fuel_cost)}. Matrix {distanceLabel(route.distance_m)}; geometry {route.geometry_distance_m===undefined?'unavailable':distanceLabel(route.geometry_distance_m)}.</p></section>}
 {matrixOpen&&result&&!comparisonTab&&<section className="logistics-schedule"><h3>Asymmetric road matrix · metres / seconds</h3><div className="logistics-table-scroll"><table><thead><tr><th>From / to</th>{[...result.scenario.depots,...result.scenario.stops].map(p=><th key={p.id}>{p.name}</th>)}</tr></thead><tbody>{result.matrix.distances.map((row,i)=><tr key={i}><th>{[...result.scenario.depots,...result.scenario.stops][i].name}</th>{row.map((d,j)=><td key={j}>{d===null?'Unreachable':d.toFixed(1)+' m / '+result.matrix.durations[i][j]?.toFixed(1)+' s'}</td>)}</tr>)}</tbody></table></div></section>}
 {tab==='Comparison'&&comparison&&<ComparisonResults comparison={comparison}/>}
 </div></div>
 {result&&<div className="logistics-print-report"><h2>LogistiMap AI · Optimization report</h2><h3>{result.scenario.name}</h3><p>{result.executed_at} · {result.provider} · {result.solver_status} · {result.objective}</p><p>{result.attribution}</p><pre>{JSON.stringify({assumptions:result.scenario,matrix_summary:result.summary,final_road_summary:result.routed_summary,assignments:result.routes.map(r=>({...r,geometry:undefined})),unassigned:result.unassigned,warnings:result.warnings},null,2)}</pre></div>}
 </section>
}
