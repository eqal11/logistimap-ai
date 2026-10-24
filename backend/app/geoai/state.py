"""Single-process, local-only capability sessions; not multi-user authentication."""
import copy,time,secrets,threading
from uuid import uuid4
from collections import deque
from datetime import datetime,timezone
class GeoError(ValueError):pass
lock=threading.RLock()
sessions={};busy=set();rate=deque()
def now():return datetime.now(timezone.utc).isoformat()
def create_or_get(key=None):
 with lock:
  for k in list(sessions):
   if time.time()-sessions[k]["touched"]>86400 and k not in busy:del sessions[k]
  if key:
   if str(key) not in sessions:raise GeoError("Session missing/expired. Open a saved snapshot or start a new conversation.")
   s=sessions[str(key)];s["touched"]=time.time();return s
  if len(sessions)>=32:raise GeoError("32 active sessions reached; wait for expiry")
  key=str(uuid4());s={"id":key,"created_at":now(),"touched":time.time(),"messages":[],"results":[],"context":{},"pending":None,"cancel_requested":False};sessions[key]=s;return s

def enter(s):
 with lock:
  t=time.monotonic()
  while rate and rate[0]<t-60:rate.popleft()
  if len(rate)>=12:raise GeoError("GeoAI limit: 12 requests/minute in this local process")
  if s['id'] in busy:raise GeoError("This session is processing")
  if len(busy)>=2:raise GeoError("Two GeoAI requests already processing")
  rate.append(t);busy.add(s['id']);s['cancel_requested']=False

def leave(s):
 with lock:busy.discard(s['id'])
def checkpoint(s):
 if s.get('cancel_requested'):raise GeoError("Cancellation requested; completed tools remain available")
def public(s):
 return copy.deepcopy({k:v for k,v in s.items() if k not in ('touched','cancel_requested')})
def add_result(s,r):
 s['results']=(s['results']+[r])[-6:]
 # Context points to actual tool output, never generated geometry.
 if r['status']=='completed' and r['features']:
  s['context']['last_feature_ids']=[str(f['id']) for f in r['features'] if f.get('id')]
  s['context']['last_result_id']=r['id']
def message(s,role,text,**kw):
 s['messages']=(s['messages']+[{"id":str(uuid4()),"role":role,"text":text,"created_at":now(),**kw}])[-20:]
def preview(s,call,details):
 token=secrets.token_hex(32)
 s['pending']={"token":token,"call":call,"preview":details,"expires_at":time.time()+300,"created_at":now()}
 return s['pending']
