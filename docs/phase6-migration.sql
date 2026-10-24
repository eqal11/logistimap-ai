BEGIN;

-- Running upgrade 0002_logistics -> 0003_site_selection

CREATE TABLE site_scenarios (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    parameters JSONB NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE site_candidates (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    feature_id VARCHAR(36), 
    logical_key VARCHAR(60) NOT NULL, 
    geometry geometry(GEOMETRY,4326) NOT NULL, 
    provenance JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (scenario_id, logical_key), 
    CHECK (ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry) AND array_position(ARRAY['ST_Point','ST_Polygon','ST_MultiPolygon'],ST_GeometryType(geometry)) IS NOT NULL), 
    FOREIGN KEY(scenario_id) REFERENCES site_scenarios (id), 
    FOREIGN KEY(feature_id) REFERENCES spatial_features (id)
);

CREATE INDEX ix_site_candidates_scenario_id ON site_candidates (scenario_id);

CREATE INDEX idx_site_candidates_geometry ON site_candidates USING gist (geometry);

CREATE TABLE site_evaluations (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    calculation_id VARCHAR(64) NOT NULL, 
    result JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(scenario_id) REFERENCES site_scenarios (id), 
    UNIQUE (calculation_id)
);

CREATE INDEX ix_site_evaluations_scenario_id ON site_evaluations (scenario_id);

CREATE TABLE site_criterion_values (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    evaluation_id VARCHAR(36) NOT NULL, 
    candidate_id VARCHAR(36) NOT NULL, 
    criterion_id VARCHAR(60) NOT NULL, 
    value FLOAT, 
    provenance JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (evaluation_id, candidate_id, criterion_id), 
    CHECK (value IS NULL OR value>=0), 
    FOREIGN KEY(evaluation_id) REFERENCES site_evaluations (id), 
    FOREIGN KEY(candidate_id) REFERENCES site_candidates (id)
);

CREATE INDEX ix_site_criterion_values_evaluation_id ON site_criterion_values (evaluation_id);

ALTER TABLE "site_scenarios" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "site_scenarios" FROM PUBLIC;

ALTER TABLE "site_candidates" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "site_candidates" FROM PUBLIC;

ALTER TABLE "site_evaluations" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "site_evaluations" FROM PUBLIC;

ALTER TABLE "site_criterion_values" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "site_criterion_values" FROM PUBLIC;

UPDATE public.alembic_version SET version_num='0003_site_selection' WHERE public.alembic_version.version_num = '0002_logistics';

COMMIT;

