BEGIN;

CREATE TABLE public.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_foundation

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE datasets (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    name VARCHAR(240) NOT NULL, 
    source VARCHAR(240) NOT NULL, 
    license VARCHAR(240) NOT NULL, 
    synthetic BOOLEAN NOT NULL, 
    import_log JSONB NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE categories (
    id VARCHAR(40) NOT NULL, 
    label VARCHAR(100) NOT NULL, 
    PRIMARY KEY (id)
);

INSERT INTO categories (id, label) VALUES ('industrial', 'Industrial facilities');

INSERT INTO categories (id, label) VALUES ('industrial_park', 'Industrial parks');

INSERT INTO categories (id, label) VALUES ('warehouse', 'Warehouses');

INSERT INTO categories (id, label) VALUES ('logistics_hub', 'Logistics hubs');

INSERT INTO categories (id, label) VALUES ('port', 'Ports');

INSERT INTO categories (id, label) VALUES ('airport', 'Airports');

INSERT INTO categories (id, label) VALUES ('road', 'Road references');

INSERT INTO categories (id, label) VALUES ('rail', 'Rail infrastructure');

INSERT INTO categories (id, label) VALUES ('study_area', 'Study areas');

CREATE TABLE spatial_features (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    dataset_id VARCHAR(36) NOT NULL, 
    name VARCHAR(240) NOT NULL, 
    source_id VARCHAR(240) NOT NULL, 
    geometry geometry(GEOMETRY,4326) NOT NULL, 
    boundary_status VARCHAR(30) NOT NULL, 
    attributes JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_feature_source UNIQUE (dataset_id, source_id), 
    CONSTRAINT ck_feature_valid CHECK (ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)), 
    CONSTRAINT ck_boundary_status CHECK (boundary_status IN ('not_applicable','unverified','verified','synthetic')), 
    FOREIGN KEY(dataset_id) REFERENCES datasets (id)
);

CREATE INDEX ix_spatial_features_name ON spatial_features (name);

CREATE INDEX ix_spatial_features_dataset_id ON spatial_features (dataset_id);

CREATE TABLE feature_categories (
    feature_id VARCHAR(36) NOT NULL, 
    category_id VARCHAR(40) NOT NULL, 
    PRIMARY KEY (feature_id, category_id), 
    FOREIGN KEY(feature_id) REFERENCES spatial_features (id) ON DELETE CASCADE, 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE CASCADE
);

CREATE INDEX ix_feature_categories_category_id ON feature_categories (category_id);

CREATE TABLE study_areas (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    name VARCHAR(240) NOT NULL, 
    geometry geometry(MULTIPOLYGON,4326) NOT NULL, 
    provenance JSONB NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE analysis_jobs (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    study_area_id VARCHAR(36), 
    operation VARCHAR(80) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    parameters JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(study_area_id) REFERENCES study_areas (id)
);

CREATE TABLE analysis_results (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    job_id VARCHAR(36) NOT NULL, 
    geometry geometry(GEOMETRY,4326), 
    summary JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(job_id) REFERENCES analysis_jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_analysis_results_job_id ON analysis_results (job_id);

CREATE TABLE candidate_sites (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    feature_id VARCHAR(36) NOT NULL, 
    job_id VARCHAR(36), 
    criteria JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (feature_id), 
    FOREIGN KEY(feature_id) REFERENCES spatial_features (id), 
    FOREIGN KEY(job_id) REFERENCES analysis_jobs (id)
);

CREATE TABLE optimization_scenarios (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    name VARCHAR(240) NOT NULL, 
    parameters JSONB NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE vehicles (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    depot_id VARCHAR(36) NOT NULL, 
    capacity FLOAT NOT NULL, 
    capacity_unit VARCHAR(30) NOT NULL, 
    constraints JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_vehicle_capacity CHECK (capacity > 0), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id) ON DELETE CASCADE, 
    FOREIGN KEY(depot_id) REFERENCES spatial_features (id)
);

CREATE INDEX ix_vehicles_scenario_id ON vehicles (scenario_id);

CREATE TABLE shipments (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    destination_id VARCHAR(36) NOT NULL, 
    demand FLOAT NOT NULL, 
    demand_unit VARCHAR(30) NOT NULL, 
    time_window JSONB, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_shipment_demand CHECK (demand > 0), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id) ON DELETE CASCADE, 
    FOREIGN KEY(destination_id) REFERENCES spatial_features (id)
);

CREATE INDEX ix_shipments_scenario_id ON shipments (scenario_id);

CREATE TABLE routing_references (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36), 
    provider VARCHAR(100) NOT NULL, 
    profile VARCHAR(80) NOT NULL, 
    geometry geometry(LINESTRING,4326), 
    provenance JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id)
);

CREATE INDEX idx_spatial_features_geometry ON spatial_features USING gist (geometry);

CREATE INDEX idx_study_areas_geometry ON study_areas USING gist (geometry);

CREATE INDEX idx_analysis_results_geometry ON analysis_results USING gist (geometry);

CREATE INDEX idx_routing_references_geometry ON routing_references USING gist (geometry);

ALTER TABLE "datasets" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "datasets" FROM PUBLIC;

ALTER TABLE "categories" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "categories" FROM PUBLIC;

ALTER TABLE "spatial_features" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "spatial_features" FROM PUBLIC;

ALTER TABLE "feature_categories" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "feature_categories" FROM PUBLIC;

ALTER TABLE "study_areas" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "study_areas" FROM PUBLIC;

ALTER TABLE "analysis_jobs" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "analysis_jobs" FROM PUBLIC;

ALTER TABLE "analysis_results" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "analysis_results" FROM PUBLIC;

ALTER TABLE "candidate_sites" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "candidate_sites" FROM PUBLIC;

ALTER TABLE "optimization_scenarios" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "optimization_scenarios" FROM PUBLIC;

ALTER TABLE "vehicles" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "vehicles" FROM PUBLIC;

ALTER TABLE "shipments" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "shipments" FROM PUBLIC;

ALTER TABLE "routing_references" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "routing_references" FROM PUBLIC;

INSERT INTO public.alembic_version (version_num) VALUES ('0001_foundation') RETURNING public.alembic_version.version_num;

COMMIT;

