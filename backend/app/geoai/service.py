"""Bounded orchestration. Only actual tool outputs produce factual response text."""
import json,time,copy
from uuid import uuid4
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from shapely.errors import GEOSException
from app.geoai import tools,planner,provider,repository,state
from app.geoai.schemas import ToolCall,ToolResult
from app.geoai.state import GeoError
from app.routing.providers import RoutingError
from app.gis.analytics import AnalysisError
from app.sites.mcda import SiteError
from app.optimization.solver import OptimizationError

def safe_message(exc):
 if isinstance(exc,(GeoError,AnalysisError,SiteError,OptimizationError,RoutingError)):return str(exc)[:800]
 return 'GIS/provider/database operation unavailable or invalid output; no substitute result generated.'
def response_text(results,lang):
 ms=lang=='ms';parts=[]
 for r in results:
  if r['status']=='completed':
   summary=json.dumps(r['summary'],ensure_ascii=False,allow_nan=False)
   parts.append((r['tool']+' selesai' if ms else r['tool']+' completed')+' · '+str(len(r['features']))+(' geometri dipaparkan. ' if ms else ' displayed geometries. ')+summary)
  elif r['status']=='pending_confirmation':parts.append('Pengesahan diperlukan sebelum operasi ini.' if ms else 'Confirmation required before this operation.')
  else:parts.append(r['tool']+': '+r['data'].get('message','Operation failed'))
 return '\n'.join(parts) or ('Sila jelaskan arahan GIS.' if ms else 'Please clarify the GIS command.')
def retain(s,r):
 state.add_result(s,r)
 if r['status']=='completed' and r['tool'] in ('filter_results','export_results'):s['context']['only_map_result_id']=r['id']
 elif r['status']=='completed' and r['features']:s['context'].pop('only_map_result_id',None)
 while len(s['results'])>1 and len(json.dumps(state.public(s)).encode())>8_000_000:s['results'].pop(0)
 # Large search context duplicated in results is bounded to latest search only.

def run_calls(s,calls,lang='en',mode='deterministic'):
 for call in calls:tools.validate(call) # whole batch prevalidated before first operation
 state.enter(s);results=[];started=time.monotonic();s['pending']=None
 try:
  for call in calls:
   try:
    state.checkpoint(s)
    if time.monotonic()-started>90:raise GeoError('90-second orchestration budget exceeded; completed results retained')
    if tools.REGISTRY[call.tool][2]:
     args=tools.validate(call);preview=tools.fleet_preview(args,s)
     pending=state.preview(s,call.model_dump(mode='json'),preview)
     r=ToolResult(id=str(uuid4()),tool=call.tool,status='pending_confirmation',data={'preview':preview},executed_at=state.now()).model_dump(mode='json')
    else:r=tools.execute(call,s)
   except Exception as exc:
    r=ToolResult(id=str(uuid4()),tool=call.tool,status='cancelled' if s.get('cancel_requested') else 'failed',data={'message':safe_message(exc)},executed_at=state.now()).model_dump(mode='json')
   results.append(r);retain(s,r)
   # Dependencies never fall back to stale context after a failed step.
   if r['status']!='completed':break
  text=response_text(results,lang);partial=any(r['status']=='completed' for r in results) and any(r['status']!='completed' for r in results)
  state.message(s,'assistant',text,mode=mode,result_ids=[r['id'] for r in results],partial=partial)
  return {'session':state.public(s),'results':results,'text':text,'language':lang,'mode':mode,'partial':partial,'provider':provider.status()}
 finally:state.leave(s)

def chat(payload):
 s=state.create_or_get(payload.session_id)
 if s['id'] in state.busy:raise GeoError('Session already processing')
 s['pending']=None
 ctx=s['context'];ctx['selected_feature_ids']=[str(x) for x in payload.selected_feature_ids]
 if 'scenario_id' in payload.model_fields_set:
  if payload.scenario_id:ctx['scenario_id']=str(payload.scenario_id)
  else:ctx.pop('scenario_id',None)
 if 'mcda_id' in payload.model_fields_set:
  if payload.mcda_id:ctx['mcda_id']=str(payload.mcda_id)
  else:ctx.pop('mcda_id',None)
 lang=planner.language(payload.message) if payload.language=='auto' else payload.language
 # Never persist prompt text automatically; only bounded memory until explicit save confirmation.
 state.message(s,'user','[Rejected unsafe/sensitive input]' if planner.BLOCK.search(payload.message) else payload.message)
 try:
  if planner.BLOCK.search(payload.message):raise GeoError('Unsafe instruction rejected: approved GIS tools only; secrets, SQL, shell and arbitrary URLs unavailable.')
  calls=planner.plan(payload.message,s) if payload.mode=='deterministic' else provider.plan(payload.message,ctx)
  return run_calls(s,calls,lang,payload.mode)
 except GeoError as e:
  text=str(e);state.message(s,'assistant',text,mode=payload.mode,clarification=True)
  return {'session':state.public(s),'results':[],'text':text,'language':lang,'mode':payload.mode,'partial':False,'clarification':True,'provider':provider.status()}

def execute(payload):
 s=state.create_or_get(payload.session_id)
 return run_calls(s,payload.calls,payload.language,'typed tool')
def save_preview(id):
 s=state.create_or_get(id)
 if s['id'] in state.busy:raise GeoError('Wait for the active operation before saving')
 state.preview(s,{'tool':'save_session','arguments':{}},{'messages':len(s['messages']),'results':len(s['results']),'effect':'Persist this conversation snapshot in Supabase, including user text and calculated result references. 7-day retrieval expiry. No keys/model reasoning. Local workspace has no user authentication.'})
 return {'session':state.public(s)}
def confirm(payload):
 s=state.create_or_get(payload.session_id)
 state.enter(s)
 try:
  with state.lock:
   p=s.get('pending')
   if not p or p['token']!=payload.token or p['expires_at']<time.time():raise GeoError('Confirmation expired, mismatched or already consumed')
   s['pending']=None # one-shot before expensive execution
  call=p['call'];state.checkpoint(s)
  repository.audit(s,call,{'status':'confirmed','created_at':state.now()})
  try:
   if call['tool']=='save_session':
    data=repository.save(s);r=ToolResult(id=str(uuid4()),tool='save_session',status='completed',data=data,summary=data,executed_at=state.now()).model_dump(mode='json')
   else:
    validated=ToolCall.model_validate(call)
    fresh=tools.fleet_preview(tools.validate(validated),s)
    if fresh!=p['preview']:raise GeoError('Scenario changed since preview; request a new confirmation')
    r=tools.execute(validated,s)
  except Exception as e:r=ToolResult(id=str(uuid4()),tool=call['tool'],status='failed',data={'message':safe_message(e)},executed_at=state.now()).model_dump(mode='json')
  repository.audit(s,call,{'status':r['status'],'result_id':r['id']})
  retain(s,r);text=response_text([r],'en');state.message(s,'assistant',text,result_ids=[r['id']],mode='confirmed')
  return {'session':state.public(s),'results':[r],'text':text,'language':'en','mode':'confirmed','partial':False,'provider':provider.status()}
 finally:state.leave(s)
def restore(id):
 old=repository.load(id);s=state.create_or_get();s.update({k:old[k] for k in ('messages','results','context')});s['pending']=None
 return {'session':state.public(s),'restored_from':id}
