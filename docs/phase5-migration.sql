BEGIN;

-- Running upgrade 0001_foundation -> 0002_logistics

CREATE TABLE logistics_depots (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    logical_key VARCHAR(60) NOT NULL, 
    geometry geometry(POINT,4326) NOT NULL, 
    parameters JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (scenario_id, logical_key), 
    CHECK (ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id)
);

CREATE INDEX ix_logistics_depots_scenario_id ON logistics_depots (scenario_id);

CREATE INDEX idx_logistics_depots_geometry ON logistics_depots USING gist (geometry);

CREATE TABLE logistics_stops (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    logical_key VARCHAR(60) NOT NULL, 
    geometry geometry(POINT,4326) NOT NULL, 
    parameters JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (scenario_id, logical_key), 
    CHECK (ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id)
);

CREATE INDEX ix_logistics_stops_scenario_id ON logistics_stops (scenario_id);

CREATE INDEX idx_logistics_stops_geometry ON logistics_stops USING gist (geometry);

CREATE TABLE logistics_vehicles (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    start_depot_id VARCHAR(36) NOT NULL, 
    end_depot_id VARCHAR(36) NOT NULL, 
    logical_key VARCHAR(60) NOT NULL, 
    capacity INTEGER NOT NULL, 
    parameters JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (scenario_id, logical_key), 
    CHECK (capacity>0), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id), 
    FOREIGN KEY(start_depot_id) REFERENCES logistics_depots (id), 
    FOREIGN KEY(end_depot_id) REFERENCES logistics_depots (id)
);

CREATE INDEX ix_logistics_vehicles_scenario_id ON logistics_vehicles (scenario_id);

CREATE TABLE logistics_demands (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    stop_id VARCHAR(36) NOT NULL, 
    pickup_stop_id VARCHAR(36), 
    amount INTEGER NOT NULL, 
    unit VARCHAR(30) NOT NULL, 
    context VARCHAR(30) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (stop_id), 
    CHECK (amount>0), 
    FOREIGN KEY(stop_id) REFERENCES logistics_stops (id), 
    FOREIGN KEY(pickup_stop_id) REFERENCES logistics_stops (id)
);

CREATE TABLE optimization_jobs (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    metadata JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id)
);

CREATE INDEX ix_optimization_jobs_scenario_id ON optimization_jobs (scenario_id);

CREATE TABLE optimization_solutions (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    scenario_id VARCHAR(36) NOT NULL, 
    job_id VARCHAR(36) NOT NULL, 
    result JSONB NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (job_id), 
    FOREIGN KEY(scenario_id) REFERENCES optimization_scenarios (id), 
    FOREIGN KEY(job_id) REFERENCES optimization_jobs (id)
);

CREATE INDEX ix_optimization_solutions_scenario_id ON optimization_solutions (scenario_id);

CREATE TABLE vehicle_route_assignments (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    solution_id VARCHAR(36) NOT NULL, 
    vehicle_id VARCHAR(36) NOT NULL, 
    geometry geometry(MULTILINESTRING,4326), 
    summary JSONB NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(solution_id) REFERENCES optimization_solutions (id), 
    FOREIGN KEY(vehicle_id) REFERENCES logistics_vehicles (id)
);

CREATE INDEX ix_vehicle_route_assignments_solution_id ON vehicle_route_assignments (solution_id);

CREATE INDEX idx_vehicle_route_assignments_geometry ON vehicle_route_assignments USING gist (geometry);

CREATE TABLE logistics_comparisons (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    name VARCHAR(160) NOT NULL, 
    result JSONB NOT NULL, 
    PRIMARY KEY (id)
);

ALTER TABLE "logistics_depots" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "logistics_depots" FROM PUBLIC;

ALTER TABLE "logistics_stops" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "logistics_stops" FROM PUBLIC;

ALTER TABLE "logistics_vehicles" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "logistics_vehicles" FROM PUBLIC;

ALTER TABLE "logistics_demands" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "logistics_demands" FROM PUBLIC;

ALTER TABLE "optimization_jobs" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "optimization_jobs" FROM PUBLIC;

ALTER TABLE "optimization_solutions" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "optimization_solutions" FROM PUBLIC;

ALTER TABLE "vehicle_route_assignments" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "vehicle_route_assignments" FROM PUBLIC;

ALTER TABLE "logistics_comparisons" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "logistics_comparisons" FROM PUBLIC;

UPDATE public.alembic_version SET version_num='0002_logistics' WHERE public.alembic_version.version_num = '0001_foundation';

COMMIT;

