import {describe,it,expect,vi,afterEach} from 'vitest'
import {newScenario,newVehicle,optimizationCSVRows,optimizationBounds,optimizationGeoJSON,exportOptimizationCSV,clockLabel,type OptimizationResult} from './optimization'
import {csvText} from './analytics'
export function testResult():OptimizationResult{
 const s=newScenario();s.name='TEST hypothetical only';s.depots=[{id:'d',name:'TEST depot',coordinates:[101,3],window:[0,86400]}];s.stops=[{id:'s',name:'TEST candidate',coordinates:[101.1,3],window:[0,86400],demand:2,service_s:0,priority:1,mandatory:false,kind:'delivery'}];s.vehicles=[newVehicle('d',1)]
 return {status:'best_found',solver_status:'success',solver_code:1,engine:'TEST OR-Tools',method:'TEST bounded solver',objective:'distance',objective_value:100,objective_unit:'metres',proven_optimal:false,validated:true,elapsed_s:1,time_limit_s:1,
 routes:[{vehicle_id:'v',vehicle_name:'Vehicle 1',capacity:10,stop_ids:['s'],schedule:[{id:'d',name:'TEST depot',sequence:0,coordinates:[101,3],kind:'depot',arrival_s:0,departure_s:0,load_before:2,load_after:2,demand:0},{id:'s',name:'TEST candidate',sequence:1,coordinates:[101.1,3],kind:'delivery',arrival_s:10,departure_s:10,load_before:2,load_after:0,demand:2}],distance_m:100,travel_duration_s:10,working_duration_s:10,peak_load:2,assigned_demand:2,capacity_utilization_pct:20,estimated_cost:0,cost_components:{distance_cost:0,fixed_cost:0,driver_cost:0,fuel_cost:0},geometry:{type:'MultiLineString',coordinates:[[[101,3],[101.05,3.02],[101.1,3]]]},geometry_status:'available'}],
 unassigned:[],summary:{distance_m:100,travel_duration_s:10,estimated_cost:0,assigned_stops:1,vehicles_used:1,vehicles_available:1,assigned_demand:2,total_demand:2,unassigned_stops:0},
 scenario:s,matrix:{id:'test',nodes:2,pairs:4,unreachable_pairs:0,cached:true,upstream_requests:1,retrieved_at:'TEST',distances:[[0,100],[150,0]],durations:[[0,10],[15,0]],snapped:[],method:'TEST matrix fixture only'},warnings:['TEST synthetic UI fixture; never live industrial result'],provider:'TEST provider',profile:'car',heavy_vehicle_verified:false,attribution:'TEST attribution',executed_at:'2026-10-24',geometry_complete:true,policy_url:'https://example.test',fix_map_url:'https://example.test'}
}
afterEach(()=>vi.unstubAllGlobals())
describe('optimization exports and assumptions',()=>{
 it('starts empty and labels demands hypothetical',()=>{const s=newScenario();expect(s.stops).toEqual([]);expect(s.depots).toEqual([]);expect(s.demand_context).toBe('hypothetical')})
 it('vehicle defaults contain zero price assumptions',()=>{const v=newVehicle('d',1);expect(v.cost_per_km+v.fixed_cost+v.driver_cost_per_hour+v.fuel_price_per_l).toBe(0)})
 it('preserves supplied route geometry and solver provenance',()=>{const r=testResult();const g=optimizationGeoJSON(r);expect(g.features[0].geometry).toEqual(r.routes[0].geometry);expect(g.features[0].properties?.heavy_vehicle_verified).toBe(false);expect(g.features[0].properties?.provider).toBe('TEST provider')})
 it('omits absent route geometry instead of inventing a line',()=>{const r=testResult();r.routes[0].geometry=null;r.geometry_complete=false;expect(optimizationGeoJSON(r).features.every(f=>f.geometry.type==='Point')).toBe(true)})
 it('preserves schedule numbering and source identifier',()=>{const r=testResult();r.routes[0].schedule[1].source_id='way/123';expect(optimizationGeoJSON(r).features[2].properties).toMatchObject({label:'1',source_id:'way/123',demand_context:'hypothetical'})})
 it('neutralizes spreadsheet formula names in exported rows',()=>{expect(csvText([{name:'=HYPERLINK("x")'}])).toContain("'=HYPERLINK")})
 it('formats absolute scenario seconds including 24:00',()=>{expect(clockLabel(28805)).toBe('08:00:05');expect(clockLabel(86400)).toBe('24:00:00')})
 it('downloads attributed assignment CSV through a blob',()=>{
 const create=vi.fn(()=> 'blob:test'),revoke=vi.fn();vi.stubGlobal('URL',{createObjectURL:create,revokeObjectURL:revoke})
 const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{})
 exportOptimizationCSV(testResult(),'assignments');expect(create).toHaveBeenCalled();expect(click).toHaveBeenCalled();click.mockRestore()
 })
})


it('fits final road detours with 150000 vertices without argument overflow',()=>{
 const coordinates=Array.from({length:150000},(_,i)=>[101+i/100000,3+(i%10)/100])
 const bounds=optimizationBounds({type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:{type:'LineString',coordinates}}]})
 expect(bounds).toEqual([101,3,102.49999,3.09])
 expect(optimizationBounds({type:'FeatureCollection',features:[]})).toBeUndefined()
})


it.each(['assignments','schedules'] as const)('retains infeasible scenario context in empty %s CSV',kind=>{
 const r=testResult();r.routes=[];r.status='infeasible';r.unassigned=[{id:'s',name:'TEST candidate',demand:2,reason:'infeasible'}]
 const rows=optimizationCSVRows(r,kind)
 expect(rows).toHaveLength(1);expect(rows[0]).toMatchObject({record_type:'no_vehicle_routes',status:'infeasible',unassigned:r.unassigned,provider:'TEST provider',demand_context:'hypothetical'})
 expect(csvText(rows)).toContain('TEST candidate')
})
