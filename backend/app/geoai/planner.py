"""Explicit bilingual command grammar. Never described as an LLM."""
import re
from uuid import UUID
from app.geoai.schemas import ToolCall
from app.geoai.state import GeoError
# Long names first prevents Klang from shadowing Port Klang.
PATTERNS=[('Port Klang',r'port klang|pelabuhan klang'),('Tanjong Malim',r'tanj[ou]ng malim|ahtv'),('Shah Alam',r'shah alam'),('Bukit Raja',r'bukit raja'),('Rawang',r'rawang'),('Klang',r'(?<!port )(?<!pelabuhan )klang')]
CATEGORIES={'warehouse':r'warehouse|warehouses|gudang','industrial_park':r'industrial park|industrial parks|kawasan industri|taman perindustrian','industrial':r'industrial facilit|manufactur|kilang|kemudahan industri','logistics_hub':r'logistics? hub|logistics? cent|hab logistik','port':r'ports|pelabuhan(?! klang)','airport':r'airport|lapangan terbang','road':r'roads|highways|jalan utama','rail':r'railway|railways|kereta api'}
BLOCK=re.compile(r'(ignore.{0,35}(instruction|system)|abaikan.{0,35}arahan|system prompt|developer message|reveal.{0,25}(secret|password|key)|kata laluan|database_password|\.env|execute sql|drop table|delete from|shell command|powershell|os\.system|eval\(|https?://|<script|sk-[a-zA-Z0-9_-]{12,}|postgres(?:ql)?://|api[_ -]?key|authorization:)',re.I)
def language(text):return 'ms' if re.search(r'\b(cari|buat|gudang|daripada|kawasan|banding|berapa|papar|terdekat|simpan|ubah|tingkatkan|arahan)\b',text,re.I) else 'en'
def places(text):
 remaining=text.lower();found=[]
 for canonical,pattern in PATTERNS:
  for m in re.finditer(pattern,remaining):found.append((m.start(),canonical))
  remaining=re.sub(pattern,lambda m:' '*len(m.group()),remaining)
 return [x[1] for x in sorted(found)]
def radius(text):
 m=re.search(r'(\d+(?:\.\d+)?)\s*(km|kilometer|kilometre|kilometers|kilometres|m|meter|metre)\b',text)
 return float(m[1])*(.001 if m[2] in ('m','meter','metre') else 1) if m else None
def call(tool,**arguments):return ToolCall(tool=tool,arguments=arguments)
def plan(text,s):
 t=text.lower().strip();p=places(t);r=radius(t);ctx=s['context'];selected=ctx.get('selected_feature_ids',[])
 if BLOCK.search(t):raise GeoError('Unsafe instruction rejected. Only approved GIS tools are available; no SQL, shell, secrets, arbitrary URLs or system-prompt access.')
 if re.search(r'isochrone|isokron|flood|banjir|land price|harga tanah|legal|zoning approval',t):raise GeoError('Unsupported/unavailable official dataset or network isochrone. No fabricated result will be generated.')
 if re.search(r'export|eksport|download|muat turun',t):return [call('export_results')]
 if re.search(r'show only|only those|papar.*sahaja|tiga sahaja',t):
  n=re.search(r'\b(\d+)\b',t);return [call('filter_results',top=int(n[1]) if n else 3)]
 if re.search(r'nearest|terdekat',t) and not re.search(r'road|jalan|travel',t):return [call('nearest_facility',feature_id=selected[0] if selected else None)]
 if re.search(r'buffer|penampan',t):
  if r is None:raise GeoError('Specify buffer distance in km or metres and select exact imported feature(s). A town reference is not an industrial park boundary.')
  return [call('create_buffer',feature_ids=selected,distance_m=r*1000)]
 if re.search(r'intersect|persilangan',t):return [call('intersect_features',feature_ids=selected)]
 if re.search(r'explain|jelas|mengapa|why',t) and re.search(r'candidate|calon|mcda|rank',t):
  ids=[x for x in re.findall(r'candidate\s+([\w.:-]+)',text,re.I) if x.lower() not in ('ranks','rank','is','above','below','sites','site')]
  return [call('explain_mcda_ranking',id=ctx.get('mcda_id'),candidate_a=ids[0] if ids else None,candidate_b=ids[1] if len(ids)>1 else None)]
 if re.search(r'mcda|rank.*candidate|rank.*calon|kedudukan.*calon|current.*weights',t) and not re.search(r'increase|decrease|change|ubah|tingkatkan|sensitivity|sensitiviti|=',t):return [call('evaluate_mcda_scenario',id=ctx.get('mcda_id'))]
 if re.search(r'weight|pemberat|sensitivity|sensitiviti',t):
  # Absolute weights only; percentage and factor ambiguity must be clarified.
  m=re.search(r'(road_distance_m|warehouse_distance_m|industrial_count|port_time_s|airport_time_s)\s*(?:to|kepada|=)\s*(\d+(?:\.\d+)?)',t)
  if not m:raise GeoError('Specify an exact criterion and absolute weight, e.g. road_distance_m=0.4. Select a saved MCDA evaluation; weights are renormalized.')
  return [call('run_mcda_sensitivity_analysis',id=ctx.get('mcda_id'),weights={m[1]:float(m[2])})]
 if re.search(r'mcda|rank.*candidate|rank.*calon|kedudukan.*calon|current.*weights',t):return [call('evaluate_mcda_scenario',id=ctx.get('mcda_id'))]
 if re.search(r'optimi[sz]e|optimi[sz]ation|optimum|vehicles? versus|vehicles? vs|kenderaan lawan',t):
  nums=re.search(r'(\d+)\s*(?:vehicles?|kenderaan)?\s*(?:versus|vs|lawan)\s*(\d+)',t)
  if not nums and re.search(r'two vehicles versus three',t):counts=[2,3]
  else:counts=[int(nums[1]),int(nums[2])] if nums else []
  # Do not invent delivery demand/coordinates for "10 destinations" requests.
  if not ctx.get('scenario_id'):raise GeoError('Select a saved logistics scenario with explicit demands, capacities and windows. GIS locations alone do not define shipments.')
  return [call('optimize_vehicle_routes',id=ctx['scenario_id'],vehicle_counts=counts)]
 if re.search(r'saved routes|sejarah laluan',t):return [call('get_saved_routes')]
 if re.search(r'saved analyses|analisis disimpan',t):return [call('get_saved_analyses')]
 if re.search(r'saved scenarios|senario disimpan',t):return [call('get_logistics_scenarios')]
 if re.search(r'cluster|kelompok',t):
  if len(p)!=1 or r is None:raise GeoError('Specify one supported place and study radius; e.g. clusters Shah Alam radius 5 km. Defaults: eps=1000m, min_points=3 (editable typed tool).')
  return [call('analyze_industrial_clusters',place=p[0],radius_km=r,categories=['industrial','industrial_park'])]
 if re.search(r'density|ketumpatan',t):
  if len(p)<2 or r is None:raise GeoError('Specify at least two supported places and the comparison radius.')
  return [call('compare_industrial_density',places=p,radius_km=r)]
 if re.search(r'route|laluan',t):
  refs=p if len(p)==2 else selected if len(selected)==2 else []
  if len(refs)!=2:raise GeoError('Specify two supported places or select exactly two imported facilities.')
  return [call('calculate_road_route',origin=refs[0],destination=refs[1])]
 if re.search(r'compare accessibility|banding.*akses',t):
  if len(p)<3:raise GeoError('Specify comparison origins and a common destination, e.g. Rawang and Shah Alam to Port Klang.')
  return [call('calculate_network_accessibility',origins=p[:-1],destination=p[-1])]
 byroad=bool(re.search(r'by road|road travel|travel time|masa perjalanan|melalui jalan|akses.*jalan',t))
 if byroad and ctx.get('last_search') and (len(p)<=1):return [call('rank_warehouse_accessibility',destination=p[-1] if p else 'Port Klang',top=3)]
 cats=[k for k,pat in CATEGORIES.items() if re.search(pat,t)]
 if not cats and re.search(r'industrial|industri',t):cats=['industrial','industrial_park']
 if cats:
  if not p and len(selected)==1:
   p=[selected[0]]
   if 'warehouse' in cats:cats=['warehouse']
  if not p:raise GeoError('Specify an unambiguous supported place. This command grammar does not guess unknown locations.')
  if r is None:raise GeoError('Specify a search radius in km, e.g. warehouses Shah Alam 10 km. No default radius is silently assumed.')
  calls=[call('search_industrial_features',place=p[0],radius_km=r,categories=cats)]
  if byroad:
   if len(p)<2:raise GeoError('Specify the road-ranking destination as well as the search area.')
   calls.append(call('rank_warehouse_accessibility',destination=p[-1],top=3))
  return calls
 raise GeoError('Command is ambiguous or unsupported in deterministic mode. Choose a documented example or the typed tool form. No GIS operation was guessed.')
