"""Opt-in live Supabase tests. All test rows are rolled back; never seed a database."""
import json
import os
from uuid import uuid4

from dotenv import dotenv_values
from geoalchemy2.shape import from_shape
import pytest
from shapely.geometry import Point, Polygon, shape
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import BACKEND_ROOT, Settings
from app.db.session import create_database_engine
from app.db.verification import safe_error, verify_connection
from app.models.entities import Category, Dataset, SpatialFeature
from app.schemas.spatial import Category as CategoryId, SearchParams
from app.services.features import postgis_search


pytestmark = pytest.mark.live_db


@pytest.fixture(scope="module")
def live_engine():
    if os.getenv("RUN_SUPABASE_INTEGRATION_TESTS") != "1":
        pytest.skip("Live Supabase tests are opt-in and require a configured local password.")
    values = dotenv_values(BACKEND_ROOT / ".env")
    # Only connection fields are relevant here; JSON CORS parsing belongs to the env source.
    allowed = {name for name in Settings.model_fields if name.startswith("database_")}
    kwargs = {key.lower():value for key,value in values.items() if key.lower() in allowed}
    engine = None
    try:
        settings = Settings(_env_file=None, **kwargs)
        engine = create_database_engine(settings)
        with engine.connect() as connection:
            verify_connection(connection, full=True)
    except Exception as exc:
        if engine is not None:
            engine.dispose()
        pytest.fail(safe_error(exc)["message"], pytrace=False)
    yield engine
    engine.dispose()


def test_live_postgis_schema_and_spatial_indexes(live_engine):
    with live_engine.connect() as connection:
        report = verify_connection(connection, full=True)
    assert report["ssl"] is True
    assert report["table_count"] == report["rls_tables"] == 26
    assert report["spatial_indexes"] == 8
    assert len(report["geometry_columns"]) == 8


def test_live_geometry_roundtrip_and_units(live_engine):
    with live_engine.connect() as connection:
        row = connection.execute(text("""
            SELECT ST_AsGeoJSON(ST_GeomFromText('LINESTRING(0 0,1 0)',4326)) AS geometry,
            ST_Length(ST_GeomFromText('LINESTRING(0 0,1 0)',4326)::geography)/1000 AS length_km
        """)).mappings().one()
    geometry = json.loads(row["geometry"])
    assert geometry["type"] == "LineString"
    assert geometry["coordinates"] == [[0,0],[1,0]]
    assert row["length_km"] == pytest.approx(111.31949, abs=0.01)


def test_live_query_repository_read_only(live_engine, monkeypatch):
    from app.services import features
    monkeypatch.setattr(features, "get_engine", lambda:live_engine)
    records,total,counts = postgis_search(SearchParams(
        categories=[CategoryId.warehouse,CategoryId.industrial,CategoryId.port],
        bbox=(99.5,0.7,119.7,7.5),limit=5,
    ))
    assert total >= len(records) and len(records) <= 5
    assert all(count >= 0 for count in counts.values())
    assert all(set(record.properties.categories) & {CategoryId.warehouse,CategoryId.industrial,CategoryId.port} for record in records)


def test_live_multicategory_query_with_rollback_only_rows(live_engine):
    token = "__integration_" + uuid4().hex + "__"
    dataset_id = str(uuid4())
    with live_engine.connect() as connection:
        writable = connection.execute(text("SELECT has_table_privilege(current_user,'public.datasets','INSERT')")).scalar_one()
        connection.rollback()
        if not writable:
            pytest.skip("Read-only account; no write privileges will be added for tests.")
        transaction = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                dataset = Dataset(id=dataset_id, name=token, source="Synthetic integration test; rollback only",
                                  license="CC0", synthetic=True, import_log={})
                session.add(dataset)
                session.flush()
                memberships = {category.id:category for category in session.query(Category).all()}
                samples = [
                    ("warehouse", Point(101.5,3.1), ["warehouse","logistics_hub"]),
                    ("industrial", Polygon([(101.51,3.11),(101.52,3.11),(101.52,3.12),(101.51,3.11)]), ["industrial"]),
                    ("port", Point(101.53,3.13), ["port"]),
                ]
                for name,geometry,category_ids in samples:
                    session.add(SpatialFeature(
                        id=str(uuid4()), dataset_id=dataset_id, name=token+name, source_id=name,
                        geometry=from_shape(geometry,srid=4326),
                        boundary_status="synthetic" if name=="industrial" else "not_applicable",
                        categories=[memberships[key] for key in category_ids], attributes={},
                    ))
                session.flush()
                records,total,counts = postgis_search(SearchParams(q=token,categories=[
                    CategoryId.warehouse,CategoryId.industrial,CategoryId.logistics_hub,CategoryId.port,
                ]), db_session=session)
                assert total == len(records) == 3
                assert len({record.id for record in records}) == 3
                assert all(counts[key] == 1 for key in ["warehouse","industrial","logistics_hub","port"])
                assert all(record.properties.synthetic for record in records)
        finally:
            transaction.rollback()
        remaining = connection.execute(text("SELECT count(*) FROM public.datasets WHERE id=:id"),{"id":dataset_id}).scalar_one()
        assert remaining == 0


def test_live_osm_ingestion_deduplication_and_version_guard_rollback(live_engine):
    from app.services.discovery import ingest
    from app.schemas.discovery import DiscoveryRequest
    token = "__osm_contract_" + uuid4().hex
    payload = DiscoveryRequest(categories=["warehouse", "logistics_hub"], center=[101.5,3.1], radius_km=1)
    feature = {"source_id":"node/TEST-"+token,"name":token,"geometry":{"type":"Point","coordinates":[101.5,3.1]},
               "categories":["warehouse","logistics_hub"],"boundary_status":"not_applicable",
               "attributes":{"osm_version":2,"test_only":"rollback"}}
    with live_engine.connect() as connection:
        transaction=connection.begin()
        try:
            with Session(bind=connection,join_transaction_mode="create_savepoint") as session:
                first=ingest([feature],{},payload,"test-only",session)
                assert first["inserted"]==1 and first["updated"]==0
                second=ingest([feature],{},payload,"test-only",session)
                assert second["inserted"]==0 and second["updated"]==1
                feature["attributes"]["osm_version"]=1
                feature["name"]="stale"+token
                third=ingest([feature],{},payload,"test-only",session)
                assert third["preserved_newer"]==1
                records,total,counts=postgis_search(SearchParams(q=token),db_session=session)
                assert total==1 and counts["warehouse"]==counts["logistics_hub"]==1
                assert records[0].properties.name==token
                assert records[0].properties.attributes["osm_version"]==2
        finally:
            transaction.rollback()
        assert connection.execute(text("SELECT count(*) FROM public.spatial_features WHERE name=:name"),{"name":token}).scalar_one()==0


def test_live_routing_anchor_and_geographic_warehouse(live_engine,monkeypatch):
    from app.routing import service
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(),"data_mode","postgis")
    with Session(live_engine) as session:
        feature_id=session.execute(text("SELECT id FROM spatial_features WHERE name='Canpac Sdn. Bhd.' LIMIT 1")).scalar_one_or_none()
        if not feature_id: pytest.skip("Phase 2 dataset not imported in this database.")
        origin=service.feature_anchor(feature_id,session)
        nearest=service.nearest_warehouse(feature_id,session)
        assert origin["anchor_method"]=="source_point"
        assert nearest["feature_id"]!=feature_id and "warehouse" in nearest["categories"]
        assert nearest["geographic_distance_m"]>=0
        assert "not road distance" in nearest["method"]
        assert len(nearest["coordinates"])==2


def test_live_saved_route_geometry_provenance_and_idempotency(live_engine):
    from pathlib import Path
    from app.core.config import PROJECT_ROOT
    from app.routing.service import save_calculation
    from app.schemas.routing import SaveRouteRequest
    path=PROJECT_ROOT/"docs"/"phase3-routing-scenarios.json"
    if not path.exists(): pytest.skip("Run explicit live routing acceptance before checking saved routes.")
    report=json.loads(path.read_text(encoding="utf-8"))
    example=next(s for s in report["scenarios"] if s["status"]=="passed")
    with live_engine.connect() as connection:
        row=connection.execute(text("SELECT ST_IsValid(geometry),ST_SRID(geometry),GeometryType(geometry),provenance FROM routing_references WHERE id=:id"),{"id":example["saved_id"]}).one()
        assert row[0] and row[1]==4326 and row[2]=="LINESTRING"
        assert not row[3]["heavy_vehicle_verified"] and row[3]["profile"]=="car"
        assert float(row[3]["selected_route"]["distance_m"])==example["distance_m"]
        connection.rollback()
        transaction=connection.begin()
        try:
            with Session(bind=connection,join_transaction_mode="create_savepoint") as session:
                payload=SaveRouteRequest(calculation_id=row[3]["calculation_id"],route_index=0)
                first=save_calculation(payload,session);second=save_calculation(payload,session)
                assert first["id"]==second["id"]==example["saved_id"]
        finally:transaction.rollback()

def test_live_phase4_analysis_save_reload_archive_rollback(live_engine):
    from sqlalchemy.orm import Session
    from sqlalchemy import select,func
    from app.models.entities import AnalysisResult
    from app.schemas.analytics import SpatialAnalysis
    from app.services.analytics import run_analysis,save_analysis,get_saved,history,archive,restore
    from app.gis.analytics import AnalysisError
    with Session(live_engine) as session:
        payload=SpatialAnalysis(operation="buffer",title="Phase 4 rollback-only integration test",
            a={"ids":["335bcf23-dccb-5eb4-b14a-737040e1e784"]},distance_m=1000)
        result=run_analysis(payload,session)
        receipt=save_analysis(result["calculation_id"],session)
        loaded=get_saved("analyses",receipt["id"],session)
        assert loaded["features"]==result["features"]
        assert session.scalar(select(func.ST_SRID(AnalysisResult.geometry)).where(AnalysisResult.id==receipt["id"]))==4326
        assert save_analysis(result["calculation_id"],session)["id"]==receipt["id"]
        archive("analyses",receipt["id"],session)
        session.flush()
        with pytest.raises(AnalysisError):get_saved("analyses",receipt["id"],session)
        assert session.get(AnalysisResult,receipt["id"]).summary["archived_at"]
        restore("analyses",receipt["id"],session);session.flush()
        assert get_saved("analyses",receipt["id"],session)["features"]==result["features"]
        session.rollback()

def test_live_phase3_history_retains_saved_routes(live_engine):
    from sqlalchemy.orm import Session
    from app.services.analytics import history,get_saved
    with Session(live_engine) as session:
        rows=history("routes",session=session)
        assert rows["total"]>=8
        r=get_saved("routes",rows["items"][0]["id"],session)
        assert r["features"][0]["geometry"]["type"]=="LineString"
        assert r["statistics"]["distance_m"]>0

def test_live_logistics_scenario_solution_and_geometry_roundtrip(live_engine):
    from app.optimization import repository as repo
    from app.schemas.optimization import Scenario
    from app.models.logistics import VehicleAssignment
    from sqlalchemy import select,func
    s=Scenario(name="Synthetic logistics integration · rollback only",
        depots=[{"id":"d","name":"Synthetic test depot","coordinates":[101,3]}],
        vehicles=[{"id":"v","name":"Synthetic test vehicle","capacity":4,"start_depot":"d","end_depot":"d"}],
        stops=[{"id":"s","name":"Synthetic test stop","coordinates":[101.1,3],"demand":2}])
    with live_engine.connect() as connection:
        transaction=connection.begin()
        try:
            with Session(bind=connection,join_transaction_mode="create_savepoint") as db:
                saved=repo.save_scenario(s,db)
                assert repo.get_scenario(saved["id"],db)["scenario"]==s.model_dump(mode="json")
                job=repo.create_job(saved["id"],db)
                result={"status":"test_only","summary":{"assigned_stops":1},"routes":[{"vehicle_id":"v","geometry":{"type":"MultiLineString","coordinates":[[[101,3],[101.05,3.01],[101.1,3]]]}}]}
                key=repo.persist_solution(saved["id"],job,result,db)
                assert repo.results(saved["id"],db)["solution_id"]==key
                valid=db.execute(select(func.ST_IsValid(VehicleAssignment.geometry),func.ST_SRID(VehicleAssignment.geometry)).where(VehicleAssignment.solution_id==key)).one()
                assert valid==(True,4326)
                repo.archive(saved["id"],True,db)
                assert repo.get_scenario(saved["id"],db,True)["archived"]
                repo.archive(saved["id"],False,db)
                assert not repo.get_scenario(saved["id"],db)["archived"]
                clone=repo.duplicate(saved["id"],db)
                assert clone["id"]!=saved["id"] and clone["scenario"]["stops"]==saved["scenario"]["stops"]
        finally:transaction.rollback()


def test_live_comparison_pins_solutions_and_survives_new_solve_rollback(live_engine):
    import copy
    from sqlalchemy import select
    from app.optimization import repository as repo
    from app.models.logistics import OptimizationSolution,OptimizationJob
    with Session(live_engine) as db:
        # Only insert rollback rows; historical scenario/solution rows are never edited.
        ids=list(dict.fromkeys(db.scalars(select(OptimizationSolution.scenario_id).order_by(OptimizationSolution.created_at)).all()))[:2]
        assert len(ids)==2
        c=repo.compare(ids,"TEST comparison persistence · rollback only",db)
        assert c["schema_version"]==2 and all(row["solution_id"] for row in c["rows"])
        assert repo.get_comparison(c["id"],db)==c
        assert c["id"] in [r["id"] for r in repo.list_comparisons(100,0,db)["items"]]
        before=repo.comparison_solutions(c["id"],db)
        original=before["items"][0]
        job=OptimizationJob(scenario_id=original["scenario_id"],status="test_only",metadata_json={"stage":"Rollback only"})
        db.add(job);db.flush()
        later=copy.deepcopy(original["result"]);later["summary"]["distance_m"]+=123
        db.add(OptimizationSolution(scenario_id=original["scenario_id"],job_id=job.id,result=later));db.flush()
        assert repo.results(original["scenario_id"],db)["summary"]["distance_m"]==later["summary"]["distance_m"]
        assert repo.comparison_solutions(c["id"],db)==before
        db.rollback()

def test_live_legacy_comparison_resolves_without_modification_and_rejects_mismatch(live_engine):
    import copy
    from sqlalchemy import select
    from app.optimization import repository as repo
    from app.models.logistics import LogisticsComparison,OptimizationSolution
    with Session(live_engine) as db:
        old=db.scalar(select(LogisticsComparison).where(~LogisticsComparison.result.has_key("schema_version")).order_by(LogisticsComparison.created_at).limit(1))
        assert old is not None
        untouched=copy.deepcopy(old.result)
        resolved=repo.comparison_solutions(old.id,db)
        assert len(resolved["items"])==len(old.result["rows"]) and resolved["warnings"]
        assert old.result==untouched
        broken=copy.deepcopy(untouched);broken["rows"][0]["distance_m"]+=123
        bad=LogisticsComparison(name="TEST legacy mismatch · rollback",result=broken);db.add(bad);db.flush()
        with pytest.raises(repo.ComparisonUnavailable):repo.comparison_solutions(bad.id,db)
        assert old.result==untouched
        db.rollback()


def test_live_site_metrics_geometry_persistence_and_ahp_rollback(live_engine):
    from sqlalchemy import select,func
    from app.schemas.sites import SiteScenario as Payload
    from app.sites import service,repository
    from app.models.sites import SiteCandidate,SiteCriterionValue
    payload=Payload(name="TEST Phase6 real GIS · rollback only",candidates=[
      {"id":"canpac","name":"Canpac mapped reference","feature_id":"335bcf23-dccb-5eb4-b14a-737040e1e784"},
      {"id":"warehouse","name":"Pharmaniaga mapped reference","feature_id":"030efbe3-8d74-545d-90e0-15df09508265"}],
      criteria=[{"id":k,"source":"gis","direction":"benefit" if k=="industrial_count" else "cost","weight":1} for k in ("road_distance_m","warehouse_distance_m","industrial_count")],
      method="ahp",ahp_matrix=[[1,1,1],[1,1,1],[1,1,1]])
    with Session(live_engine) as db:
        r=service.evaluate(payload,db)
        assert r["values"]["canpac"]["warehouse_distance_m"]["value"]==pytest.approx(537.6253,abs=.1)
        assert r["ahp"]["cr"]<1e-9 and sum(r["weights"].values())==pytest.approx(1)
        receipt=repository.save(r["calculation_id"],db)
        assert repository.save(r["calculation_id"],db)["id"]==receipt["id"]
        loaded=repository.get(receipt["id"],db)
        assert loaded["features"]==r["features"] and loaded["scenario"]==r["scenario"] and loaded["sensitivity"]==r["sensitivity"]
        geometries=db.execute(select(func.ST_IsValid(SiteCandidate.geometry),func.ST_SRID(SiteCandidate.geometry)).where(SiteCandidate.scenario_id==receipt["scenario_id"])).all()
        assert len(geometries)==2 and all(x==(True,4326) for x in geometries)
        assert db.scalar(select(func.count()).select_from(SiteCriterionValue).where(SiteCriterionValue.evaluation_id==receipt["id"]))==6
        assert repository.history(100,0,db)["total"]>=1
        db.rollback()

def test_live_site_polygon_area_user_values_and_provider_failure(live_engine,monkeypatch):
    from app.schemas.sites import SiteScenario as Payload
    from app.sites import service
    from app.gis.analytics import GEOD
    from shapely.geometry import shape
    from app.routing.providers import RoutingError
    geometry={"type":"Polygon","coordinates":[[[101.5,3.1],[101.51,3.1],[101.51,3.11],[101.5,3.11],[101.5,3.1]]]}
    payload=Payload(name="TEST hypothetical geometry · read-only",candidates=[{"id":"polygon","name":"TEST user polygon","geometry":geometry,"values":{"land_cost":{"value":123456,"note":"Hypothetical test assumption, not a property valuation"}}}],
      criteria=[{"id":"parcel_area_m2","source":"gis","direction":"benefit"},{"id":"land_cost","source":"user","direction":"cost"}])
    with Session(live_engine) as db:
        data=service.prepare(payload,db)
        expected=abs(GEOD.geometry_area_perimeter(shape(geometry))[0])
        assert data["values"]["polygon"]["parcel_area_m2"]["value"]==pytest.approx(expected,rel=1e-7)
        assert data["values"]["polygon"]["land_cost"]["status"]=="user_supplied"
        assert data["candidates"][0]["provenance"]["kind"]=="hypothetical_site"
        payload=Payload.model_validate({**payload.model_dump(mode="json"),"criteria":[{"id":"port_time_s","source":"network","direction":"cost"}],"targets":{"port":{"coordinates":[101.4,3],"label":"TEST target reference"}}})
        monkeypatch.setattr(service,"road_matrix",lambda *a,**kw:(_ for _ in ()).throw(RoutingError("TEST provider unavailable")))
        data=service.prepare(payload,db)
        assert data["values"]["polygon"]["port_time_s"]["value"] is None and data["values"]["polygon"]["port_time_s"]["status"]=="provider_unavailable"
        db.rollback()


def test_live_geoai_session_audit_snapshot_roundtrip_rollback(live_engine):
 from app.geoai import state,repository
 from app.models.geoai import GeoAISession,GeoAIConfirmation
 from sqlalchemy import select,func
 s=state.create_or_get();state.message(s,'user','TEST explicit saved snapshot; rollback')
 s['context']={'search':{'place':'Shah Alam','radius_km':5,'categories':['warehouse']}}
 state.preview(s,{'tool':'save_session','arguments':{}},{'effect':'test'})
 with Session(live_engine) as db:
  before=db.scalar(select(func.count()).select_from(GeoAISession))
  receipt=repository.save(s,db);loaded=repository.load(receipt['id'],db)
  assert loaded['context']==s['context'] and loaded['messages']==s['messages'] and loaded['pending'] is None
  repository.audit(s,{'tool':'save_session','arguments':{}},{'status':'confirmed'},db)
  assert repository.history(25,0,db)['total']>=before+1
  row=db.scalar(select(GeoAIConfirmation).where(GeoAIConfirmation.session_key==s['id']))
  assert row and len(row.request_digest)==64 and row.outcome['status']=='confirmed'
  db.rollback()

def test_live_geoai_real_warehouse_tool_geometry_and_categories(live_engine,monkeypatch):
 from app.geoai import tools,state
 from app.geoai.schemas import Search
 from app.core.config import Settings
 import app.services.features as features
 from app.schemas.spatial import SearchParams
 from types import SimpleNamespace
 # Same production PostGIS query, use explicit live engine while offline suite config remains isolated.
 def actual(p):
  with Session(live_engine) as db:
   fs,total,counts=features.postgis_search(p,db)
  return SimpleNamespace(model_dump=lambda **kw:{'type':'FeatureCollection','features':[f.model_dump(mode='json') for f in fs],'meta':{'mode':'postgis','total':total,'returned':len(fs),'offset':p.offset,'limit':p.limit,'has_more':p.offset+len(fs)<total,'category_counts':counts,'warnings':[],'attribution':'OSM ODbL'}})
 monkeypatch.setattr(tools.features,'search',actual)
 s=state.create_or_get();r=tools.search(Search(place='Shah Alam',categories=['warehouse','industrial'],radius_km=5),s)
 assert r['meta']['category_counts']['warehouse']>0 and r['meta']['category_counts']['industrial']>0
 assert all(shape(f['geometry']).is_valid and not f['properties']['synthetic'] for f in r['features'])


def test_live_geoai_feature_proximity_uses_footprint_not_centroid(live_engine):
 id='335bcf23-dccb-5eb4-b14a-737040e1e784'
 with Session(live_engine) as db:
  p=SearchParams(center=[101.5,3.1],radius_km=1,categories=['warehouse'],limit=200)
  fs,total,counts=postgis_search(p,db,reference_feature_id=id)
  expected=db.execute(text("SELECT count(*) FROM spatial_features f JOIN feature_categories c ON c.feature_id=f.id WHERE c.category_id='warehouse' AND ST_DWithin(f.geometry::geography,(SELECT geometry::geography FROM spatial_features WHERE id=:id),1000)"),{'id':id}).scalar()
  assert total==expected and total>0 and all(not f.properties.synthetic for f in fs)
