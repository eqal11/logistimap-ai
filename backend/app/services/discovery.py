"""Transactional OSM ingestion into the existing Phase 1 PostGIS schema."""
import json
from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from uuid import NAMESPACE_URL, uuid4, uuid5

from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.entities import AnalysisJob, AnalysisResult, Category, Dataset, SpatialFeature, feature_categories
from app.schemas.discovery import DiscoveryRequest
from app.services.osm import ATTRIBUTION, ProviderError, build_query, normalize, public_json
from app.core.config import get_settings

DATASET_ID = str(uuid5(NAMESPACE_URL,"https://www.openstreetmap.org/logistimap/canonical"))
gate=Lock()
active_job: str | None = None

def ingest(features, report, request, job_id, session):
    """Caller controls transaction; one canonical dataset and stable OSM object IDs."""
    now=datetime.now(timezone.utc)
    statement=insert(Dataset).values(id=DATASET_ID,created_at=now,
        name="OpenStreetMap · Malaysia industrial and logistics discovery",
        source="OpenStreetMap contributors",license="ODbL 1.0 · https://www.openstreetmap.org/copyright",
        synthetic=False,import_log={"last_job_id":job_id,"last_imported_at":now.isoformat()})
    session.execute(statement.on_conflict_do_update(index_elements=[Dataset.id],
        set_={"import_log":statement.excluded.import_log}))
    ids=[str(uuid5(NAMESPACE_URL,"https://www.openstreetmap.org/"+f["source_id"])) for f in features]
    existing=set(session.scalars(select(SpatialFeature.id).where(SpatialFeature.id.in_(ids)))) if ids else set()
    applied=set()
    allowed=set(session.scalars(select(Category.id)))
    for start in range(0,len(features),200):
        batch=features[start:start+200]; rows=[]
        for feature in batch:
            attrs={**feature["attributes"],"last_imported_at":now.isoformat()}
            rows.append({"id":str(uuid5(NAMESPACE_URL,"https://www.openstreetmap.org/"+feature["source_id"])),
                "created_at":now,"dataset_id":DATASET_ID,"source_id":feature["source_id"],
                "name":feature["name"],"geometry":from_shape(shape(feature["geometry"]),srid=4326),
                "boundary_status":feature["boundary_status"],"attributes":attrs})
        statement=insert(SpatialFeature).values(rows)
        # Cached older responses must never overwrite a newer source version.
        old_version=func.coalesce(SpatialFeature.attributes["osm_version"].as_integer(),0)
        new_version=func.coalesce(statement.excluded.attributes["osm_version"].as_integer(),0)
        changed=list(session.scalars(statement.on_conflict_do_update(
            constraint="uq_feature_source",set_={"name":statement.excluded.name,
                "geometry":statement.excluded.geometry,"attributes":statement.excluded.attributes,
                "boundary_status":statement.excluded.boundary_status},
            where=old_version<=new_version).returning(SpatialFeature.id)))
        applied.update(changed)
        if changed:
            session.execute(delete(feature_categories).where(feature_categories.c.feature_id.in_(changed)))
            links=[{"feature_id":row["id"],"category_id":c}
                for row,feature in zip(rows,batch) if row["id"] in changed
                for c in feature["categories"] if c in allowed]
            if links: session.execute(insert(feature_categories).values(links).on_conflict_do_nothing())
    return {**report,"inserted":len(applied-existing),"updated":len(applied&existing),
        "preserved_newer":len(ids)-len(applied),"dataset_id":DATASET_ID,
        "imported_at":now.isoformat(),"label":request.label,"parameters":request.model_dump(mode="json"),
        "job_id":job_id}

def create_job(payload):
    global active_job
    if not gate.acquire(blocking=False):
        raise ProviderError("Another discovery import is running. Wait for it to finish.")
    job_id=str(uuid4())
    try:
        with Session(get_engine()) as session,session.begin():
            session.add(AnalysisJob(id=job_id,operation="osm_discovery",status="queued",
                                    parameters=payload.model_dump(mode="json")))
        active_job=job_id
        return job_id
    except Exception:
        gate.release()
        raise

def run_job(job_id,payload):
    global active_job
    try:
        with Session(get_engine()) as session,session.begin():
            session.get(AnalysisJob,job_id).status="running"
        query=build_query(payload)
        raw,cached=public_json("overpass",get_settings().overpass_url,query,data={"data":query})
        features,report=normalize(raw,payload)
        report["provider_cached"]=cached
        with Session(get_engine()) as session,session.begin():
            # Multiple processes are not a supported public-provider deployment mode.
            session.execute(select(func.pg_advisory_xact_lock(1748835340,2)))
            report=ingest(features,report,payload,job_id,session)
            session.add(AnalysisResult(job_id=job_id,summary=report))
            session.get(AnalysisJob,job_id).status="completed"
    except Exception as exc:
        # Upstream bodies, URLs and database exception text are never stored/logged.
        message=str(exc) if isinstance(exc,ProviderError) else "Database import failed; transaction rolled back. Run local diagnostics."
        report={"message":message,"failed_categories":[c.value for c in payload.categories],
                "category_counts":{},"inserted":0,"updated":0,"label":payload.label,"attribution":ATTRIBUTION}
        try:
            with Session(get_engine()) as session,session.begin():
                session.add(AnalysisResult(job_id=job_id,summary=report))
                session.get(AnalysisJob,job_id).status="failed"
        except Exception:
            pass
    finally:
        active_job=None
        gate.release()

def job_record(job_id):
    with Session(get_engine()) as session:
        job=session.get(AnalysisJob,job_id)
        if job is None or job.operation!="osm_discovery": return None
        result=session.scalar(select(AnalysisResult).where(AnalysisResult.job_id==job_id).order_by(AnalysisResult.created_at.desc()))
        status=job.status
        if status in ("queued","running") and active_job != job_id:
            status="interrupted"
        return {"id":job.id,"status":status,"created_at":job.created_at.isoformat(),
                "parameters":job.parameters,"report":result.summary if result else None}

def recent_jobs():
    with Session(get_engine()) as session:
        rows=session.execute(select(AnalysisJob,AnalysisResult.summary).outerjoin(
            AnalysisResult,AnalysisResult.job_id==AnalysisJob.id).where(AnalysisJob.operation=="osm_discovery")
            .order_by(AnalysisJob.created_at.desc()).limit(30)).all()
        return [{"id":job.id,"status":("interrupted" if job.status in ("queued","running") and active_job!=job.id else job.status),
                 "created_at":job.created_at.isoformat(),"parameters":job.parameters,"report":summary}
                for job,summary in rows]
