"""Read-only Phase7 integrity/runtime/export evidence. Secrets never printed."""
import json,hashlib,asyncio,csv
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from sqlalchemy import text
from shapely.geometry import shape
import httpx
from app.core.config import PROJECT_ROOT,BACKEND_ROOT
from app.db.session import get_engine
from app.db.verification import verify_connection,safe_error
from app.services.osm import ssl_context
async def runtime():
 async with httpx.AsyncClient(verify=ssl_context(),timeout=60) as c:
  paths=['/health','/ready','/api/geoai/health','/api/geoai/tools','/api/geoai/sessions','/api/industrial/features?categories=warehouse&categories=industrial&limit=1','/api/history/routes','/api/history/analyses','/api/optimization/scenarios','/api/optimization/comparisons','/api/sites/saved']
  replies=await asyncio.gather(*[c.get('http://127.0.0.1:8000'+p) for p in paths]);assert all(r.status_code==200 for r in replies)
  preview=await c.get('http://127.0.0.1:4173/');assert preview.status_code==200
  assert any(f.name in preview.text for f in (PROJECT_ROOT/'frontend/dist/assets').glob('index-*.js'))
  proxy=await c.get('http://127.0.0.1:4173/api/geoai/health');assert proxy.status_code==200 and proxy.json()['provider']['configured'] is False
  r=await c.post('http://127.0.0.1:4173/api/geoai/chat',headers={'Origin':'http://127.0.0.1:4173'},json={'message':'Find warehouses around Rawang within 5 km.'});assert r.status_code==200 and r.json()['results'][0]['status']=='completed'
  return {'backend_paths':dict(zip(paths,[r.status_code for r in replies])),'preview':200,'preview_geoai_proxy':200,'preview_origin_chat':200,'latest_dist_served':True,'note':'HTTP/proxy smoke only, no browser rendering or browser downloads verified'}
def main():
 docs=PROJECT_ROOT/'docs';baseline=json.loads((docs/'phase7-baseline.json').read_text(encoding='utf-8'));report={'verified_at':datetime.now(timezone.utc).isoformat()}
 with get_engine().connect() as db:
  db.execute(text('SET TRANSACTION READ ONLY'));report['database']=verify_connection(db,full=True);integrity={}
  for table,old in baseline['tables'].items():
   current=[r[0] for r in db.execute(text('select md5(row_to_json(t)::text) from public."'+table+'" t'))]
   integrity[table]={'before':len(old),'now':len(current),'original_missing_or_changed':sum((Counter(old)-Counter(current)).values())}
  assert all(r['original_missing_or_changed']==0 and r['before']==r['now'] for r in integrity.values())
  report['integrity']=integrity
  report['geoai_rows']={table:db.execute(text('select count(*) from public."'+table+'"')).scalar() for table in ('geoai_sessions','geoai_confirmations')}
 report['env_unchanged']=hashlib.sha256((BACKEND_ROOT/'.env').read_bytes()).hexdigest()==baseline['env_sha256'];assert report['env_unchanged']
 original=json.loads((docs/'phase7-k-export-result.json').read_text(encoding='utf-8'))['results'][0]
 exported=json.loads((docs/'phase7-frontend-export.geojson').read_text(encoding='utf-8'))
 rows=list(csv.DictReader((docs/'phase7-frontend-export.csv').open(encoding='utf-8-sig')))
 assert exported['features']==original['features'] and len(rows)==len(original['rows'])==3
 assert all(shape(f['geometry']).is_valid for f in exported['features'])
 assert exported['metadata']['profile']=='car' and exported['metadata']['heavy_vehicle_verified'] is False
 report['exports']={'status':'passed','geojson_original_geometries':3,'csv_rows':3,'verification':'actual frontend functions headless; not browser downloads'}
 report['runtime']=asyncio.run(runtime());report['phase5_browser']='pending';report['phase6_browser']='pending';report['phase7_browser']='unavailable';report['phase8_started']=False;report['status']='passed'
 (docs/'phase7-integrity.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 from app.main import app
 (docs/'openapi.json').write_text(json.dumps(app.openapi(),indent=2),encoding='utf-8')
 print(json.dumps({'status':'passed','old_tables_preserved':len(integrity),'geoai_rows':report['geoai_rows'],'env_unchanged':True,'runtime':report['runtime'],'exports':report['exports']}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps(safe_error(e)));raise SystemExit(1)
