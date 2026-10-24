"""Resource/migration/batching safety tests with synthetic numeric data only."""
from types import SimpleNamespace
import pytest
from app.optimization import repository,matrix
from app.optimization.solver import OptimizationError
from app.db.migrate import classify_schema
from app.db.verification import FOUNDATION_TABLES,DatabaseVerificationError

def test_large_solution_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(repository,"get_engine",lambda:pytest.fail("Database should not be opened for oversized result"))
    with pytest.raises(OptimizationError,match="8 MB"):
        repository.persist_solution("test","test",{"test_only_payload":"x"*8_000_001})

def test_additive_upgrade_accepts_exact_foundation_and_rejects_collisions():
    assert classify_schema(FOUNDATION_TABLES|{"alembic_version"},["0001_foundation"])=="upgrade"
    with pytest.raises(DatabaseVerificationError):
        classify_schema(FOUNDATION_TABLES|{"alembic_version","logistics_stops"},["0001_foundation"])

def test_large_matrix_batches_without_losing_asymmetric_cells(tmp_path,monkeypatch):
    monkeypatch.setattr(matrix,"get_settings",lambda:SimpleNamespace(provider_cache_dir=tmp_path,routing_base_url="https://example.test",routing_osrm_profile="car"))
    points=[{"coordinates":[101+i*.001,3]} for i in range(17)];calls=[]
    class Provider:
        def table(self,ps,sources,destinations,snap):
            assert len(ps)<=16 and len(sources)<=8 and len(destinations)<=8
            calls.append(1)
            def global_index(local):return round((ps[local]["coordinates"][0]-101)*1000)
            def value(a,b):
                i,j=global_index(a),global_index(b)
                return 0 if i==j else 100+abs(i-j)*10+i
            return {"code":"Ok","sources":[{"location":ps[i]["coordinates"],"distance":0} for i in sources],
                "destinations":[{"location":ps[i]["coordinates"],"distance":0} for i in destinations],
                "distances":[[value(a,b) for b in destinations] for a in sources],
                "durations":[[value(a,b)/10 for b in destinations] for a in sources]}
    r=matrix.road_matrix(points,provider=Provider())
    assert len(calls)==9 and r["pairs"]==289
    assert r["distances"][0][16]==260 and r["distances"][16][0]==276
    assert r["unreachable_pairs"]==0
    assert matrix.road_matrix(points,provider=Provider())["cached"] and len(calls)==9
