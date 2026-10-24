import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {BarChart,Bar,CartesianGrid,XAxis,YAxis,Tooltip,ResponsiveContainer} from 'recharts'
import {Button} from '../components/ui/button'
import {listScenarios} from '../services/optimization'
import {downloadGeoJSON} from '../services/api'
import {distanceLabel,durationLabel} from '../services/routing'
import {createComparison,listComparisons,getComparison,getComparisonSolutions,makeOverlay,comparisonGeoJSON,exportComparisonCSV,scenarioColors,routePatterns,routeKey,type SavedComparison,type ComparisonOverlay} from '../services/comparisons'
const money=(n:number)=>'RM '+n.toFixed(2)
interface Props {comparison:SavedComparison|null;onComparison:(c:SavedComparison)=>void;overlay:ComparisonOverlay|null;onOverlay:(o:ComparisonOverlay|null)=>void}
export function LogisticsComparison({comparison,onComparison,overlay,onOverlay}:Props){
 const [page,setPage]=useState(0),[scenarioPage,setScenarioPage]=useState(0),[ids,setIds]=useState<string[]>([]),[name,setName]=useState('Fleet / scenario comparison'),[busy,setBusy]=useState(false),[error,setError]=useState(''),[note,setNote]=useState('')
 const saved=useQuery({queryKey:['comparison-history',page],queryFn:({signal})=>listComparisons(page,signal)})
 const scenarios=useQuery({queryKey:['comparison-scenarios',scenarioPage],queryFn:({signal})=>listScenarios(scenarioPage,false,signal)})
 async function run(fn:()=>Promise<void>){setBusy(true);setError('');setNote('');try{await fn()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function display(c:SavedComparison){
  onComparison(c);onOverlay(null)
  const payload=await getComparisonSolutions(c.id)
  onOverlay(makeOverlay(c,payload));setNote('Saved comparison opened with its historical solution geometries.')
 }
 return <section aria-label="Saved solution comparisons">
 <h3>Saved comparison history</h3><p className="logistics-muted">Persistent snapshots · OSRM standard car profile, not truck-verified. Each new comparison pins exact solution IDs.</p>
 <Button size="sm" variant="outline" disabled={saved.isFetching} onClick={()=>saved.refetch()}>Refresh comparisons</Button>
 {saved.isFetching&&<p role="status">Loading comparison history…</p>}{saved.error&&<p role="alert">{saved.error.message}</p>}
 {saved.data?.items.length===0&&<p>No saved comparisons yet.</p>}
 {saved.data?.items.map(c=><article className="logistics-card" key={c.id}><strong>{c.name}</strong><small>{new Date(c.created_at).toLocaleString()} · {c.scenario_count} solutions · {c.schema_version===1?'legacy snapshot':'pinned snapshot'}</small><Button size="sm" variant="outline" disabled={busy} onClick={()=>run(async()=>display(await getComparison(c.id)))}>Open comparison {c.name}</Button></article>)}
 <div className="logistics-actions"><Button size="sm" variant="outline" disabled={page===0||busy} onClick={()=>setPage(Math.max(0,page-10))}>Previous comparisons</Button><small>{saved.data?.total? page+1:0}–{Math.min(page+10,saved.data?.total??0)} / {saved.data?.total??0}</small><Button size="sm" variant="outline" disabled={busy||page+10>=(saved.data?.total??0)} onClick={()=>setPage(page+10)}>Next comparisons</Button></div>
 <details><summary>Create comparison from saved solutions</summary>
 <label>Comparison name<input aria-label="Comparison name" maxLength={160} value={name} onChange={e=>setName(e.target.value)}/></label>
 <p className="logistics-muted">Choose 2–4 solved snapshots. Creating a comparison does not run routing or modify a scenario.</p>
 {scenarios.isFetching&&<p role="status">Loading solved scenario choices…</p>}{scenarios.error&&<p role="alert">{scenarios.error.message}</p>}
 {scenarios.data?.items.map(item=><label className="logistics-check" key={item.id}><input type="checkbox" aria-label={'Compare '+item.name} disabled={busy||!item.summary||(!ids.includes(item.id)&&ids.length>=4)} checked={ids.includes(item.id)} onChange={()=>setIds(ids.includes(item.id)?ids.filter(k=>k!==item.id):[...ids,item.id])}/><span>{item.name}<small>{item.status} · {item.stops} stops</small></span></label>)}
 <div className="logistics-actions"><Button size="sm" variant="outline" disabled={scenarioPage===0||busy} onClick={()=>setScenarioPage(Math.max(0,scenarioPage-25))}>Previous choices</Button><Button size="sm" variant="outline" disabled={busy||scenarioPage+25>=(scenarios.data?.total??0)} onClick={()=>setScenarioPage(scenarioPage+25)}>Next choices</Button></div>
 <Button disabled={busy||ids.length<2||!name.trim()} onClick={()=>run(async()=>{const c=await createComparison(ids,name.trim());await saved.refetch();await display(c)})}>Save comparison {ids.length}/4</Button>
 </details>
 {busy&&<p role="status">Opening saved solution snapshots…</p>}{error&&<p role="alert" className="logistics-error">{error}</p>}{note&&<p role="status">{note}</p>}
 {comparison&&<><hr/><h3>{comparison.name}</h3><small>Snapshot {new Date(comparison.created_at).toLocaleString()} · {comparison.id}</small>
 <p className="logistics-muted">{comparison.metric_basis??'Legacy stored matrix comparison; final road metrics may be absent.'}</p>
 {!comparison.comparable_locations_and_demand&&<p className="logistics-unassigned">Locations or demands differ. Compare assumptions before interpreting the totals.</p>}
 {comparison.warnings.map((w,i)=><p key={i} className="logistics-muted">{w}</p>)}
 <div className="logistics-comparison-chart"><ResponsiveContainer width="100%" height={240}><BarChart data={comparison.rows}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="name" hide/><YAxis/><Tooltip/><Bar dataKey="distance_m" fill="#118b87" name="Matrix road distance (m)"/></BarChart></ResponsiveContainer></div>
 <Button size="sm" variant="outline" onClick={()=>exportComparisonCSV(comparison)}>CSV comparison</Button>
 <details><summary>Snapshot assumptions and provenance</summary><pre>{JSON.stringify(comparison.rows,null,2)}</pre></details>
 </>}
 {overlay&&<><hr/><h3>Comparison map legend</h3><p className="logistics-muted">Colour = scenario A–D; dash = vehicle. Parallel line offsets are display pixels only. Geometry and distances remain unchanged.</p>
 {overlay.warnings.map((w,i)=><p key={i} className="logistics-muted">{w}</p>)}
 {overlay.items.map((item,si)=><div className="logistics-card" key={item.solution_id}>
 <label className="logistics-check"><input type="checkbox" aria-label={'Show scenario '+String.fromCharCode(65+si)+': '+item.name} checked={!overlay.hiddenScenarios.includes(item.scenario_id)} onChange={()=>onOverlay({...overlay,hiddenScenarios:overlay.hiddenScenarios.includes(item.scenario_id)?overlay.hiddenScenarios.filter(x=>x!==item.scenario_id):[...overlay.hiddenScenarios,item.scenario_id]})}/><strong style={{color:scenarioColors[si]}}>{String.fromCharCode(65+si)} · {item.name}</strong></label>
 <small>Solution {item.solution_id} · {item.result.status} · {item.result.summary.unassigned_stops} unassigned</small>
 {item.result.routes.length===0&&<p className="logistics-muted">No vehicle routes; no geometry invented.</p>}
 {item.result.routes.map((r,vi)=>{const key=routeKey(item,r.vehicle_id);return <div className={'comparison-legend-route '+(overlay.selectedRoute===key?'selected':'')} key={key}>
 <label className="logistics-check"><input type="checkbox" aria-label={'Show '+String.fromCharCode(65+si)+' · '+r.vehicle_name} disabled={overlay.hiddenScenarios.includes(item.scenario_id)} checked={!overlay.hiddenRoutes.includes(key)} onChange={()=>onOverlay({...overlay,hiddenRoutes:overlay.hiddenRoutes.includes(key)?overlay.hiddenRoutes.filter(x=>x!==key):[...overlay.hiddenRoutes,key]})}/><svg width="45" height="14" aria-hidden="true"><line x1="0" y1="7" x2="45" y2="7" stroke={scenarioColors[si]} strokeWidth="3" strokeDasharray={routePatterns[vi%6].map(n=>n*3).join(' ')}/></svg><span>{r.vehicle_name}</span></label>
 <button aria-label={'Inspect '+String.fromCharCode(65+si)+' · '+r.vehicle_name} onClick={()=>onOverlay({...overlay,selectedRoute:key,hiddenScenarios:overlay.hiddenScenarios.filter(x=>x!==item.scenario_id),hiddenRoutes:overlay.hiddenRoutes.filter(x=>x!==key)})}>Inspect route</button>
 <small>{r.geometry_distance_m===undefined?'Road geometry unavailable':distanceLabel(r.geometry_distance_m)} · {r.stop_ids.length} stops · road limits {r.road_geometry_constraints_verified?'verified':'not verified'}{r.geometry_error?' · '+r.geometry_error:''}</small>
 </div>})}
 <small>{item.result.attribution}</small>
 </div>)}
 <Button size="sm" variant="outline" onClick={()=>downloadGeoJSON(comparisonGeoJSON(overlay),'logistimap-comparison-visible.geojson')}>GeoJSON visible comparison</Button>
 </>}
 </section>
}
export function ComparisonResults({comparison}:{comparison:SavedComparison}){
 return <section className="logistics-schedule" aria-label="Comparison results"><h3>Scenario comparison · saved snapshot</h3><p>Matrix = solver basis; final road = verified returned geometry. Smaller totals with unassigned stops do not represent equivalent service.</p><div className="logistics-table-scroll"><table><thead><tr>{['Scenario','Status','Matrix km','Matrix driving','Matrix MYR','Final road km','Final driving','Final MYR','Vehicles','Assigned','Unassigned'].map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{comparison.rows.map((r,i)=><tr key={r.scenario_id}><td>{String.fromCharCode(65+i)} · {r.name}</td><td>{r.status}<small>{r.proven_optimal?'Integer model optimal':'Global optimality not established'}</small></td><td>{(r.distance_m/1000).toFixed(4)}</td><td>{durationLabel(r.travel_duration_s)}</td><td>{money(r.estimated_cost)}</td><td>{r.final_road_summary?(r.final_road_summary.distance_m/1000).toFixed(4):'Unavailable'}</td><td>{r.final_road_summary?durationLabel(r.final_road_summary.travel_duration_s):'Unavailable'}</td><td>{r.final_road_summary?money(r.final_road_summary.estimated_cost):'Unavailable'}</td><td>{r.vehicles_used}/{r.vehicles_available}</td><td>{r.assigned_stops}</td><td>{r.unassigned_stops}</td></tr>)}</tbody></table></div></section>
}
