BEGIN;

-- Running upgrade 0003_site_selection -> 0004_geoai

CREATE TABLE geoai_sessions (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    snapshot JSONB NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (octet_length(snapshot::text)<=8000000)
);

CREATE INDEX ix_geoai_sessions_expires_at ON geoai_sessions (expires_at);

CREATE TABLE geoai_confirmations (
    id VARCHAR(36) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    session_key VARCHAR(36) NOT NULL, 
    action VARCHAR(70) NOT NULL, 
    request_digest VARCHAR(64) NOT NULL, 
    outcome JSONB NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_geoai_confirmations_session_key ON geoai_confirmations (session_key);

ALTER TABLE "geoai_sessions" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "geoai_sessions" FROM PUBLIC;

ALTER TABLE "geoai_confirmations" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE "geoai_confirmations" FROM PUBLIC;

UPDATE public.alembic_version SET version_num='0004_geoai' WHERE public.alembic_version.version_num = '0003_site_selection';

COMMIT;

