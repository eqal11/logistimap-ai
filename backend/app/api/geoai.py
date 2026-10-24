from uuid import UUID
from fastapi import APIRouter,Request,HTTPException,Query
from sqlalchemy.exc import SQLAlchemyError
from app.api.analytics import guard
from app.core.config import get_settings
from app.geoai import service,state,tools,provider,repository
from app.geoai.schemas import Chat,Execute,Confirm,SaveRequest
router=APIRouter(prefix='/api/geoai',tags=['phase7 GeoAI'])
def checked(request):
 guard(request)
 if not get_settings().geoai_enabled:raise HTTPException(403,'GeoAI disabled')
def run(fn):
 try:return fn()
 except state.GeoError as e:raise HTTPException(422,str(e))
 except (SQLAlchemyError,OSError,RuntimeError):raise HTTPException(503,'GeoAI database/provider unavailable; no fabricated response.')
@router.get('/health')
def health():return {'status':'ok','enabled':get_settings().geoai_enabled,'provider':provider.status(),'authentication':'local workspace only; no multi-user isolation','deterministic':'Bilingual bounded command grammar, not LLM intelligence','limits':{'history_messages':20,'sessions':32,'session_hours':24,'calls_per_turn':6,'map_features_per_result':2000,'saved_snapshots':100,'retrieval_days':7,'saved_snapshot_bytes':4000000}}
@router.get('/tools')
def definitions(request:Request):
 checked(request);return {'tools':tools.catalog()}
@router.post('/chat')
def chat(request:Request,payload:Chat):
 checked(request);return run(lambda:service.chat(payload))
@router.post('/execute')
def execute(request:Request,payload:Execute):
 checked(request);return run(lambda:service.execute(payload))
@router.post('/confirm')
def confirm(request:Request,payload:Confirm):
 checked(request);return run(lambda:service.confirm(payload))
@router.post('/save')
def saving(request:Request,payload:SaveRequest):
 checked(request);return run(lambda:service.save_preview(payload.session_id))
@router.post('/sessions')
def new_session(request:Request):
 checked(request);return run(lambda:{'session':state.public(state.create_or_get())})
@router.get('/sessions')
def listing(request:Request,limit:int=Query(25,ge=1,le=25),offset:int=Query(0,ge=0,le=100)):
 checked(request);return run(lambda:repository.history(limit,offset))
@router.get('/sessions/{id}')
def get(request:Request,id:UUID):
 checked(request);return run(lambda:service.restore(str(id)))
@router.get('/context/{id}')
def context(request:Request,id:UUID):
 checked(request);return run(lambda:{'session':state.public(state.create_or_get(id))})
@router.post('/sessions/{id}/cancel')
def cancel(request:Request,id:UUID):
 checked(request)
 def action():
  s=state.create_or_get(id);s['cancel_requested']=True;s['pending']=None
  return {'status':'cancellation_requested','limitations':'In-flight provider/search cannot be interrupted; cancellation checked between tools and optimization stages.'}
 return run(action)
