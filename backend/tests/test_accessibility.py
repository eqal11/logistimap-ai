import json
from contextlib import nullcontext
from types import SimpleNamespace
import pytest
from app.schemas.analytics import MatrixRequest
from app.services import accessibility as service
from app.routing.providers import RoutingError
def configure(monkeypatch,tmp_path,raw):
 settings=SimpleNamespace(routing_base_url="https://example.test",routing_osrm_profile="driving",routing_provider_label="TEST",provider_cache_dir=tmp_path)
 monkeypatch.setattr(service,"get_settings",lambda:settings)
 monkeypatch.setattr("app.services.analytics.get_settings",lambda:settings)
 monkeypatch.setattr(service,"get_engine",lambda:None)
 monkeypatch.setattr(service,"Session",lambda _:nullcontext(None))
 provider=SimpleNamespace(table=lambda *args:raw)
 monkeypatch.setattr(service,"get_provider",lambda:provider)
 monkeypatch.setattr(service,"provider_info",lambda:{"provider":"TEST","attribution":"TEST"})
 return provider
def request():return MatrixRequest(origins=[{"coordinates":[101,3]}],destinations=[{"coordinates":[101.01,3]},{"coordinates":[101.02,3]}])
def data():return {"code":"Ok","durations":[[120,None]],"distances":[[1400,None]],"sources":[{"location":[101,3],"distance":0}],"destinations":[{"location":[101.01,3],"distance":0},{"location":[101.02,3],"distance":0}]}
def test_matrix_unreachable_scores_nearest_and_cache(monkeypatch,tmp_path):
 provider=configure(monkeypatch,tmp_path,data())
 r=service.matrix(request())
 assert r["rows"][1]["reachable"] is False and r["rows"][1]["accessibility_score"]==0
 assert r["statistics"]["nearest_by_time"][0]["destination_index"]==0
 assert r["rows"][0]["distance_m"]==1400
 assert r["features"][0]["geometry"]["type"]=="Point" # no fake road line
 provider.table=lambda *args:(_ for _ in ()).throw(AssertionError("No second network call"))
 assert service.matrix(request())["cached"] is True
@pytest.mark.parametrize("mode",["dimensions","mismatch","invalid_snap","fallback","negative","unavailable"])
def test_rejects_bad_or_non_network_matrix(monkeypatch,tmp_path,mode):
 raw=data()
 if mode=="dimensions":raw["durations"]=[]
 if mode=="mismatch":raw["distances"]=[[None,None]]
 if mode=="invalid_snap":raw["sources"][0]["location"]=[999,0]
 if mode=="fallback":raw["fallback_speed_cells"]=[[0,0]]
 if mode=="negative":raw["distances"]=[[-1,None]]
 if mode=="unavailable":raw["code"]="NoTable"
 configure(monkeypatch,tmp_path,raw)
 with pytest.raises(RoutingError):service.matrix(request())
