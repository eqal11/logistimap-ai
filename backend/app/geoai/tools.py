"""Allowlisted adapters to existing services; model text has no executable authority."""
import copy,json,re,hashlib
from uuid import UUID,uuid4
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.geoai import schemas as S
from app.geoai.state import GeoError,now,checkpoint
from app.core.config import get_settings
from app.schemas.spatial import SearchParams,Geometry
from app.schemas.analytics import SpatialAnalysis,RegionComparison,MatrixRequest
from app.schemas.routing import RouteRequest,RoutePoint
from app.services import features,analytics,accessibility
from app.routing import service as routing
from app.optimization import repository as logistics,jobs
from app.schemas.optimization import Scenario
from app.sites import repository as sites,service as site_service
from app.sites.mcda import evaluate_mcda
from app.schemas.sites import SiteScenario
from app.db.session import get_engine
AREAS=json.loads(Path(__file__).with_name('areas.json').read_text(encoding='utf-8'))
ALIASES={'ahtv':'tanjong-malim','tanjung malim':'tanjong-malim','tanjong malim':'tanjong-malim','shah alam':'shah-alam','bukit raja':'bukit-raja','port klang':'port-klang','pelabuhan klang':'port-klang','rawang':'rawang','klang':'klang'}
def place(value):
 key=ALIASES.get(value.lower().strip(),value.lower().strip())
 for a in AREAS:
  if key==a['id']:return {"coordinates":a['center'],"label":a['name'],"source_id":a['source_id'],"anchor_method":"Existing geocoded town/search reference; not verified entrance"}
 try:UUID(value)
 except ValueError:raise GeoError('Unknown/ambiguous location. Choose Tanjong Malim, Rawang, Shah Alam, Bukit Raja, Klang, Port Klang or an exact imported feature UUID.')
 return routing.feature_anchor(value)
def point(value):
 p=place(value);return RoutePoint(coordinates=p['coordinates'],label=p['label'])
def ids_or_selected(args,s):
 ids=[str(i) for i in getattr(args,'feature_ids',[])]
 one=getattr(args,'feature_id',None)
 if one:ids=[str(one)]
 ids=ids or s['context'].get('selected_feature_ids',[])
 if not ids:raise GeoError('Select an imported GIS feature first, or provide its feature UUID.')
 for id in ids:UUID(id)
 return ids
def search(args,s):
 ref=place(args.place)
 p=SearchParams(center=ref['coordinates'],radius_km=args.radius_km,categories=args.categories,limit=args.limit,offset=args.offset)
 data=(features.search(p,reference_feature_id=ref['feature_id']) if ref.get('feature_id') else features.search(p)).model_dump(mode='json')
 if data['meta']['mode']!='postgis' or any(f['properties'].get('synthetic') for f in data['features']):raise GeoError('Real PostGIS records required; no fixture fallback')
 data.update(reference=ref,parameters=p.model_dump(mode='json'),title='Imported GIS search',statistics={'total':data['meta']['total'],'returned':len(data['features']),'category_counts':data['meta']['category_counts']},warnings=data['meta']['warnings']+['Town references are not industrial park entrances. Explicit pagination preserves all requested categories.'],attribution=data['meta']['attribution'])
 s['context'].update(search={'place':args.place,'radius_km':args.radius_km,'categories':[x.value for x in args.categories]},last_search=data)
 return data

def feature_detail(args,s):
 ids=ids_or_selected(args,s)
 with Session(get_engine()) as db:
  fs,meta=analytics.load_layer(__import__('app.schemas.analytics',fromlist=['LayerInput']).LayerInput(ids=ids[:20]),db)
 return {'features':fs,'statistics':{'returned':len(fs)},'inputs':meta}
def buffer(args,s):
 return analytics.run_analysis(SpatialAnalysis(operation='buffer',a={'ids':ids_or_selected(args,s)},distance_m=args.distance_m,title='GeoAI geodesic/projection buffer'))
def intersect(args,s):
 return analytics.run_analysis(SpatialAnalysis(operation='intersection',a={'ids':[args.feature_ids[0]]},b={'ids':[args.feature_ids[1]]},title='GeoAI actual intersection'))
def nearest(args,s):
 id=ids_or_selected(args,s)[0];ref=routing.nearest_warehouse(id)
 fs=feature_detail(S.Feature(feature_id=ref['feature_id']),s)['features']
 return {'features':fs,'rows':[ref],'statistics':{'nearest_geography_distance_m':ref['geographic_distance_m']},'warnings':[ref['warning']],'measurement_method':ref['method']}
def cluster(args,s):
 ref=place(args.place)
 return analytics.run_analysis(SpatialAnalysis(operation='clusters',a={'query':{'center':ref['coordinates'],'radius_km':args.radius_km,'categories':args.categories}},eps_m=args.eps_m,min_points=args.min_points,title='GeoAI mapped-object DBSCAN'))
def density(args,s):
 return accessibility.compare_regions(RegionComparison(origins=[point(x) for x in args.places],radius_km=args.radius_km))
def road(args,s):
 result=routing.calculate(RouteRequest(points=[point(args.origin),point(args.destination)],alternatives=True,max_snap_m=2000))
 result['features']=[{'type':'Feature','id':'route-'+str(i),'geometry':r['geometry'],'properties':{'name':'OSRM car route '+str(i+1),'distance_m':r['distance_m'],'duration_s':r['duration_s'],'route_index':i}} for i,r in enumerate(result['routes'])]
 result['rows']=[{'route_index':i,'distance_m':r['distance_m'],'duration_s':r['duration_s']} for i,r in enumerate(result['routes'])]
 result['statistics']={'routes':len(result['routes']),'provider_distance_m':[r['distance_m'] for r in result['routes']],'provider_duration_s':[r['duration_s'] for r in result['routes']]};return result

def network(args,s):
 return accessibility.matrix(MatrixRequest(origins=[point(x) for x in args.origins],destinations=[point(args.destination)],max_snap_m=2000))
def rank_accessibility(args,s):
 data=s['context'].get('last_search')
 if not data:raise GeoError('Run a warehouse search in this session first.')
 if 'warehouse' not in s['context'].get('search',{}).get('categories',[]):raise GeoError('Last search must explicitly include warehouses.')
 # No silent omission: no ranking if any page/candidate exceeds bounded matrix capacity.
 candidates=[f for f in data['features'] if 'warehouse' in f['properties'].get('categories',[])]
 if data['meta']['has_more'] or data['meta'].get('offset',0)>0 or len(candidates)>23:raise GeoError('Search exceeds the 23-warehouse network-ranking cap. Narrow the radius or category; no partial top ranking was claimed.')
 if not candidates:raise GeoError('No mapped warehouses returned; no real-world absence claim.')
 from app.optimization.matrix import road_matrix
 refs=[routing.feature_anchor(str(f['id'])) for f in candidates];target=place(args.destination)
 m=road_matrix(refs+[target],2000)
 rows=[{'feature_id':str(f['id']),'name':f['properties']['name'],'duration_s':m['durations'][i][-1],'distance_m':m['distances'][i][-1]} for i,f in enumerate(candidates)]
 rows.sort(key=lambda r:(r['duration_s'] is None,r['duration_s'] if r['duration_s'] is not None else float('inf'),r['feature_id']))
 eligible=[r for r in rows if r['duration_s'] is not None];top=[r['feature_id'] for r in eligible[:args.top]]
 fs=copy.deepcopy(candidates)
 for f in fs:
  row=next(r for r in rows if r['feature_id']==str(f['id']));f['properties'].update(row,top_accessible=str(f['id']) in top,rank=1+next(i for i,r in enumerate(eligible) if r['feature_id']==str(f['id'])) if row['duration_s'] is not None else None)
 result={'features':fs,'rows':rows,'statistics':{'warehouses':len(fs),'reachable':len(eligible),'top_ids':top},'matrix':m,'warnings':['Fastest among returned mapped warehouses only. All search candidates displayed; top subset highlighted. Matrix provides metrics, not connecting road geometry. Town destination is not a terminal gate.'],'profile':'car','heavy_vehicle_verified':False}
 s['context']['ranked_features']=fs;s['context']['top_ids']=top
 return result

def filter_top(args,s):
 fs=s['context'].get('ranked_features')
 if not fs:raise GeoError('No measured accessibility ranking exists in this session.')
 chosen=[f for f in fs if f['properties'].get('rank') is not None and f['properties']['rank']<=args.top]
 return {'features':chosen,'rows':[f['properties'] for f in chosen],'statistics':{'displayed':len(chosen)},'warnings':['Filtered from the previous actual network-ranking output; no new road measurements.']}

def histories(kind,args,s):
 return analytics.get_saved(kind,str(args.id)) if args.id else analytics.history(kind,25,0)
def scenario_list(args,s):return logistics.get_scenario(str(args.id)) if args.id else logistics.list_scenarios(25,0)
def candidates(args,s):return sites.get(str(args.id)) if args.id else sites.history(25,0)
def mcda_id(args,s):
 id=str(args.id) if args.id else s['context'].get('mcda_id')
 if not id:raise GeoError('Choose an exact saved Phase6 evaluation in the context selector or provide its UUID.')
 return id

def mcda(args,s):
 old=sites.get(mcda_id(args,s));s['context']['mcda_id']=old['saved_id']
 if not args.weights:
  old['statistics']={'candidates':len(old['rankings']),'weights':old['weights'],'top_candidate_ids':[r['candidate_id'] for r in old['rankings'] if r['rank']==1],'top_score':old['rankings'][0]['score'] if old['rankings'] else None}
  return old
 unknown=set(args.weights)-{c['id'] for c in old['scenario']['criteria']}
 if unknown:raise GeoError('Weight keys must match selected saved criteria')
 scenario=SiteScenario.model_validate(old['scenario']);scenario.method='wlc';scenario.ahp_matrix=None
 for c in scenario.criteria:
  if c.id in args.weights:c.weight=args.weights[c.id]
 scored=evaluate_mcda(scenario,old['values']);result=copy.deepcopy(old);result.update(scored,scenario=scenario.model_dump(mode='json'),executed_at=now(),status='completed')
 result.pop('saved_id',None);result.pop('calculation_id',None)
 for f in result['features']:
  row=next((r for r in scored['rankings'] if r['candidate_id']==str(f['id'])),None)
  f['properties'].update(score=row['score'] if row else None,rank=row['rank'] if row else None,contributions=row['contributions'] if row else {})
 result['warnings']+=['Changed weights re-score the saved raw-value snapshot, not newly fetched data. WLC weights replace AHP weights for this explicit sensitivity comparison. No saved Phase6 record changed.']
 result['rows']=[{**r,'previous_rank':next(o['rank'] for o in old['rankings'] if o['candidate_id']==r['candidate_id']),'previous_score':next(o['score'] for o in old['rankings'] if o['candidate_id']==r['candidate_id']),'rank_change':r['rank']-next(o['rank'] for o in old['rankings'] if o['candidate_id']==r['candidate_id'])} for r in scored['rankings']]
 result['statistics']={'candidates':len(scored['rankings']),'rank_changes':sum(r['rank_change']!=0 for r in result['rows']),'weights':scored['weights'],'top_candidate_ids':[r['candidate_id'] for r in scored['rankings'] if r['rank']==1]}
 return result

def explain(args,s):
 result=sites.get(mcda_id(args,s));rows=result['rankings']
 if len(rows)<2:raise GeoError('At least two ranked candidates required')
 a=args.candidate_a or rows[0]['candidate_id'];b=args.candidate_b or rows[1]['candidate_id']
 selected=[r for r in rows if r['candidate_id'] in (a,b)]
 if len(selected)!=2:raise GeoError('Use two distinct exact candidate IDs from saved ranking.')
 left=next(r for r in selected if r['candidate_id']==a);right=next(r for r in selected if r['candidate_id']==b)
 contributions=[{'criterion':k,'candidate_a':a,'candidate_b':b,'a_contribution':v,'b_contribution':right['contributions'][k],'difference':v-right['contributions'][k]} for k,v in left['contributions'].items()]
 return {'features':[f for f in result['features'] if str(f['id']) in (a,b)],'rows':contributions,'statistics':{'candidate_a':a,'candidate_b':b,'a_score':left['score'],'b_score':right['score'],'difference':left['score']-right['score']},'weights':result['weights'],'warnings':result['warnings']+['Explanation is deterministic arithmetic from stored criterion contributions; not model-generated suitability facts.']}

def fleet_preview(args,s):
 if not get_settings().optimization_enabled:raise GeoError('Optimization disabled in this workspace')
 id=str(args.id) if args.id else s['context'].get('scenario_id')
 if not id:raise GeoError('Choose an exact saved logistics scenario first. Demands/capacities/windows cannot be inferred from GIS locations.')
 saved=logistics.get_scenario(id);scenario=Scenario.model_validate(saved['scenario'])
 return {'scenario_digest':hashlib.sha256(json.dumps(saved['scenario'],sort_keys=True).encode()).hexdigest(),'scenario_id':id,'name':saved['name'],'stops':len(scenario.stops),'vehicles':len(scenario.vehicles),'solver_seconds':scenario.solver_seconds,'vehicle_counts':args.vehicle_counts,'assumptions':scenario.demand_context,'capacity_unit':scenario.capacity_unit,'effect':'Confirmed operation calculates in memory only; existing scenario/solution records are unchanged.'}
def solution_features(result,prefix=''):
 return [{'type':'Feature','id':prefix+str(r['vehicle_id']),'geometry':r['geometry'],'properties':{'name':r['vehicle_name'],'vehicle_id':r['vehicle_id'],'distance_m':r['distance_m'],'duration_s':r.get('travel_duration_s'),'geometry_status':r.get('geometry_status')}} for r in result.get('routes',[]) if r.get('geometry')]

def optimize(args,s):
 preview=fleet_preview(args,s);base=Scenario.model_validate(logistics.get_scenario(preview['scenario_id'])['scenario']);variants=args.vehicle_counts or [len(base.vehicles)]
 if len(variants)>1 and len({v.start_depot for v in base.vehicles})>1:raise GeoError('Fleet-size comparison requires one start depot; configure multi-depot variants in Scenario Builder.')
 results=[]
 for count in variants:
  checkpoint(s);scenario=base.model_copy(deep=True)
  if count!=len(base.vehicles):
   # Explicitly disclosed assumption: clone first supplied vehicle specs for extra fleet members.
   template=base.vehicles[0]
   scenario.vehicles=[base.vehicles[i].model_copy(deep=True) if i<len(base.vehicles) else template.model_copy(update={'id':'geoai-vehicle-'+str(i+1),'name':'Hypothetical copy '+str(i+1)}) for i in range(count)]
  if len(scenario.stops)>12 or scenario.solver_seconds>10:raise GeoError('GeoAI solving bounded to 12 stops and 10 seconds per variant. Use Scenario Builder for larger jobs.')
  scenario=Scenario.model_validate(scenario.model_dump(mode='json'))
  result=jobs.calculate_solution(scenario,lambda stage:checkpoint(s));results.append(result)
 fs=[f for i,r in enumerate(results) for f in solution_features(r,str(i)+'-')]
 rows=[{'vehicles_configured':variants[i],'status':r['status'],**r['summary']} for i,r in enumerate(results)]
 return {'features':fs,'rows':rows,'solutions':results,'statistics':{'variants':len(results)},'warnings':['Explicitly confirmed in-memory optimization; not saved over existing scenarios. Shipment demand and costs are supplied/hypothetical. Additional vehicles clone first supplied vehicle specs; inspect before operational use. Standard car profile, not truck verified.']+sum([r.get('warnings',[]) for r in results],[])}

def compare(args,s):
 results=[logistics.results(str(id)) for id in args.ids]
 return {'features':[f for i,r in enumerate(results) for f in solution_features(r,str(i)+'-')], 'rows':[{'scenario_id':str(id),'solver_status':r['status'],**r['summary']} for id,r in zip(args.ids,results)],'warnings':['Read-only comparison of latest saved solutions; differing locations/demands/windows make metrics non-equivalent. Existing persisted comparisons unchanged.'],'statistics':{'scenarios':len(results)}}

def last_export(args,s):
 for r in reversed(s['results']):
  if r['status']=='completed' and r['features']:
   return {'features':copy.deepcopy(r['features']),'rows':r['rows'],'statistics':{'exported_features':len(r['features'])},'warnings':r['warnings'],'attribution':r['attribution'],'source_result_id':r['id']}
 raise GeoError('No completed GIS result to export.')

# name -> schema, operation, confirmation, description
REGISTRY={
 'search_industrial_features':(S.Search,search,False,'Search ALL requested categories in imported PostGIS; radius + explicit place; paginated'),
 'search_warehouses':(S.Search,search,False,'Warehouse search; include warehouse category'),
 'search_logistics_hubs':(S.Search,search,False,'Logistics hub search; include logistics_hub category'),
 'get_feature_details':(S.Feature,feature_detail,False,'Read selected imported feature attributes'),
 'create_buffer':(S.Buffer,buffer,False,'Actual metre-unit buffer of selected imported IDs'),
 'intersect_features':(S.Intersection,intersect,False,'Actual intersection of two imported features'),
 'nearest_facility':(S.Feature,nearest,False,'Nearest different mapped warehouse by geography distance'),
 'analyze_industrial_clusters':(S.Clusters,cluster,False,'Actual descriptive DBSCAN of bounded imported industrial objects'),
 'compare_industrial_density':(S.Density,density,False,'Compare mapped object concentration in explicit radius'),
 'calculate_network_accessibility':(S.Accessibility,network,False,'Actual OSRM car matrix to selected reference'),
 'rank_warehouse_accessibility':(S.Rank,rank_accessibility,False,'Rank all last-search warehouses <=23 using actual asymmetric road matrix'),
 'calculate_road_route':(S.Road,road,False,'Actual OSRM car route and provider alternatives; not guaranteed shortest-distance path'),
 'get_saved_routes':(S.Saved,lambda a,s:histories('routes',a,s),False,'Read saved route history or exact UUID'),
 'get_saved_analyses':(S.Saved,lambda a,s:histories('analyses',a,s),False,'Read saved spatial analysis history or UUID'),
 'get_logistics_scenarios':(S.Saved,scenario_list,False,'Read existing supplied/hypothetical logistics scenarios'),
 'optimize_vehicle_routes':(S.Fleet,optimize,True,'EXPENSIVE: preview and confirm bounded existing scenario solve/fleet variants'),
 'compare_optimization_scenarios':(S.Compare,compare,False,'Read-only comparison of saved optimization outputs'),
 'get_warehouse_candidates':(S.Saved,candidates,False,'Read saved MCDA evaluations/candidate records'),
 'evaluate_mcda_scenario':(S.MCDA,mcda,False,'Read saved ranking or re-score original values with explicitly supplied WLC weights'),
 'explain_mcda_ranking':(S.Explain,explain,False,'Explain exact stored candidate contribution arithmetic'),
 'run_mcda_sensitivity_analysis':(S.MCDA,mcda,False,'Re-score saved raw values with changed weights and bounded sensitivity'),
 'filter_results':(S.Filter,filter_top,False,'Filter previous measured accessibility ranking'),
 'export_results':(S.Empty,last_export,False,'Return original completed GIS features for client GeoJSON export')
}

def validate(call):
 if call.tool not in REGISTRY:raise GeoError('Tool not allowlisted')
 try:args=REGISTRY[call.tool][0].model_validate(call.arguments)
 except ValidationError:raise GeoError('Invalid tool arguments; use the published strict schema.') from None
 if call.tool=='search_warehouses' and 'warehouse' not in args.categories:raise GeoError('Warehouse category required')
 if call.tool=='search_logistics_hubs' and 'logistics_hub' not in args.categories:raise GeoError('Logistics hub category required')
 return args

def catalog():return [{'name':name,'description':v[3],'requires_confirmation':v[2],'input_schema':v[0].model_json_schema()} for name,v in REGISTRY.items()]
def execute(call,s):
 args=validate(call);checkpoint(s)
 if call.tool in ('calculate_network_accessibility','rank_warehouse_accessibility','calculate_road_route','optimize_vehicle_routes') and not get_settings().routing_enabled:raise GeoError('Road routing disabled in this workspace')
 data=REGISTRY[call.tool][1](args,s)
 if not isinstance(data,dict):raise GeoError('Tool returned an invalid object')
 fs=data.get('features',[])
 if len(fs)>2300:raise GeoError('Tool result exceeds 2,000 map features; narrow the request')
 for f in fs:
  if f.get('type')!='Feature' or f.get('id') is None:raise GeoError('Invalid tool feature identity')
  Geometry.model_validate(f['geometry'])
 body=json.dumps(data,allow_nan=False,default=str)
 if len(body.encode())>4_000_000:raise GeoError('Result exceeds 4MB; narrow the request')
 rows=data.get('rows',data.get('rankings',data.get('items',[])))
 if len(rows)>2300:raise GeoError('Too many rows')
 return S.ToolResult(id=str(uuid4()),tool=call.tool,status='completed',data=data,features=fs,rows=rows,summary=data.get('statistics',data.get('summary',{})),warnings=list(dict.fromkeys(data.get('warnings',[])+['Results cover imported OSM only; no completeness/land availability guarantee. EPSG:4326; car routing is not truck verified.'])),attribution=data.get('attribution',S.ToolResult.model_fields['attribution'].default),executed_at=now(),measurement_method=data.get('measurement_method',data.get('methodology','Existing validated PostGIS/geodesic/OSRM or saved snapshot service; inspect parameters'))).model_dump(mode='json')
