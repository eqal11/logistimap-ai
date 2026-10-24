import json
from contextlib import nullcontext
from collections import Counter
from functools import lru_cache

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from shapely.geometry import box, shape
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.gis.measure import distance_from_center_km
from app.models.entities import Category, Dataset, SpatialFeature
from app.schemas.spatial import Feature, FeatureCollection, SearchMetadata, SearchParams


@lru_cache
def fixture_features() -> tuple[Feature, ...]:
    data = json.loads(get_settings().fixture_path.read_text(encoding="utf-8"))
    features = tuple(Feature.model_validate(f) for f in data["features"])
    if not all(f.properties.synthetic for f in features):
        raise ValueError("Fixture records must be explicitly synthetic")
    return features


def fixture_search(params: SearchParams):
    requested = set(params.categories)
    envelope = box(*params.bbox) if params.bbox else None
    selected = []
    for feature in fixture_features():
        if requested and not requested.intersection(feature.properties.categories):
            continue
        if params.q.casefold() not in feature.properties.name.casefold():
            continue
        geom = feature.geometry.model_dump()
        if envelope is not None and not envelope.intersects(shape(geom)):
            continue
        if params.center and distance_from_center_km(geom, params.center) > params.radius_km:
            continue
        selected.append(feature)
    counts = Counter(c.value for feature in selected for c in feature.properties.categories)
    return selected[params.offset:params.offset + params.limit], len(selected), dict(counts)


def postgis_search(params: SearchParams, db_session: Session | None = None, reference_feature_id: str | None = None):
    query = select(SpatialFeature, func.ST_AsGeoJSON(SpatialFeature.geometry))
    if params.categories:
        query = query.where(SpatialFeature.categories.any(Category.id.in_([c.value for c in params.categories])))
    if params.q:
        query = query.where(SpatialFeature.name.icontains(params.q, autoescape=True))
    if params.bbox:
        query = query.where(func.ST_Intersects(SpatialFeature.geometry, func.ST_MakeEnvelope(*params.bbox, 4326)))
    if reference_feature_id is not None:
        from uuid import UUID
        UUID(reference_feature_id)
        source_geometry=select(SpatialFeature.geometry).where(SpatialFeature.id==reference_feature_id).scalar_subquery()
        query=query.where(func.ST_DWithin(cast(SpatialFeature.geometry,Geography),cast(source_geometry,Geography),params.radius_km*1000))
    elif params.center:
        origin = func.ST_SetSRID(func.ST_MakePoint(*params.center), 4326)
        query = query.where(func.ST_DWithin(cast(SpatialFeature.geometry, Geography), cast(origin, Geography), params.radius_km * 1000))
    with (nullcontext(db_session) if db_session is not None else Session(get_engine())) as session:
        ids = query.with_only_columns(SpatialFeature.id).subquery()
        total = session.scalar(select(func.count()).select_from(ids))
        counts = dict(session.execute(
            select(Category.id, func.count(SpatialFeature.id)).select_from(SpatialFeature)
            .join(SpatialFeature.categories).where(SpatialFeature.id.in_(select(ids.c.id)))
            .group_by(Category.id)
        ).all())
        rows = session.execute(query.order_by(SpatialFeature.id).offset(params.offset).limit(params.limit)).all()
        features = []
        for row, geom in rows:
            features.append(Feature.model_validate({
                "type": "Feature", "id": row.id, "geometry": json.loads(geom),
                "properties": {
                    "name": row.name, "categories": [c.id for c in row.categories],
                    "source": row.dataset.source, "license": row.dataset.license, "source_id": row.source_id,
                    "dataset_id": row.dataset_id, "imported_at": row.attributes.get("last_imported_at",row.created_at.isoformat()),
                    "synthetic": row.dataset.synthetic, "boundary_status": row.boundary_status,
                    "attributes": row.attributes,
                },
            }))
    return features, total, counts


def search(params: SearchParams, reference_feature_id: str | None = None) -> FeatureCollection:
    mode = get_settings().data_mode
    features, total, counts = fixture_search(params) if mode == "fixture" else postgis_search(params,reference_feature_id=reference_feature_id)
    requested = [c.value for c in params.categories]
    category_counts = {c: counts.get(c, 0) for c in (requested or counts.keys())}
    warnings = [
        "SYNTHETIC TEST DATA: not real facilities, routes, or industrial boundaries."
        if mode == "fixture" else
        "Results describe imported records only; absence is not evidence that no real facilities exist."
    ]
    if reference_feature_id:
        warnings.append("Radius measured from the selected mapped footprint using PostGIS geography, not its town/representative centroid. Includes intersecting/touching footprints.")
    if params.offset + len(features) < total:
        warnings.append("Results are paginated; export each page to obtain the complete query.")
    return FeatureCollection(features=features, meta=SearchMetadata(
        mode=mode, total=total, returned=len(features), offset=params.offset, limit=params.limit,
        has_more=params.offset + len(features) < total, category_counts=category_counts,
        missing_categories=[c for c in requested if counts.get(c, 0) == 0],
        warnings=warnings,
        attribution="LogistiMap AI synthetic test fixture — CC0" if mode == "fixture" else "© OpenStreetMap contributors · ODbL 1.0 · https://www.openstreetmap.org/copyright; other sources retain per-feature provenance.",
    ))
