"""Explicitly confirmed, bounded snapshots; never stores keys or model reasoning."""
import json,copy,hashlib
from datetime import datetime,timezone,timedelta
from contextlib import nullcontext
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.db.session import get_engine
from app.models.geoai import GeoAISession,GeoAIConfirmation
from app.geoai.state import GeoError,public

def save(s,db=None):
 snapshot=public(s);snapshot['pending']=None
 if len(json.dumps(snapshot).encode())>4_000_000:raise GeoError('Conversation snapshot exceeds 4MB; start a shorter conversation')
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  # Snapshot/audit writer quota serialized across processes. Never evicts user records silently.
  tx.execute(__import__('sqlalchemy').text('SELECT pg_advisory_xact_lock(1748835340,7)'))
  if tx.scalar(select(func.count()).select_from(GeoAISession))>=100:raise GeoError('100 saved GeoAI snapshots reached. Operator-reviewed retention maintenance required; no existing data deleted.')
  row=GeoAISession(expires_at=datetime.now(timezone.utc)+timedelta(days=7),snapshot=snapshot);tx.add(row);tx.flush();id=row.id
  if db is None:tx.commit()
 return {'id':id,'status':'saved','retention':'Available for 7 days; at most 100 snapshots, no silent deletion. Physical expiry cleanup requires reviewed maintenance.'}

def history(limit=25,offset=0,db=None):
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  q=select(GeoAISession).where(GeoAISession.expires_at>datetime.now(timezone.utc)).order_by(GeoAISession.created_at.desc(),GeoAISession.id).limit(limit).offset(offset)
  items=[{'id':r.id,'created_at':r.created_at.isoformat(),'expires_at':r.expires_at.isoformat(),'messages':len(r.snapshot.get('messages',[])),'results':len(r.snapshot.get('results',[]))} for r in tx.scalars(q)]
  total=tx.scalar(select(func.count()).select_from(GeoAISession).where(GeoAISession.expires_at>datetime.now(timezone.utc)))
 return {'items':items,'total':total,'limit':limit,'offset':offset}
def load(id,db=None):
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  row=tx.get(GeoAISession,id)
  if row is None or row.expires_at<=datetime.now(timezone.utc):raise GeoError('Saved GeoAI snapshot missing or expired')
  return copy.deepcopy(row.snapshot)
def audit(s,call,outcome,db=None):
 with (nullcontext(db) if db is not None else Session(get_engine())) as tx:
  tx.execute(__import__('sqlalchemy').text('SELECT pg_advisory_xact_lock(1748835340,7)'))
  if tx.scalar(select(func.count()).select_from(GeoAIConfirmation))>=1000:raise GeoError('1000 audit records reached; reviewed retention maintenance required')
  row=GeoAIConfirmation(session_key=s['id'],action=call['tool'],request_digest=hashlib.sha256(json.dumps(call,sort_keys=True).encode()).hexdigest(),outcome=outcome);tx.add(row);tx.flush()
  if db is None:tx.commit()
