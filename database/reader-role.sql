-- Optional Phase 1 read-only role setup. Run deliberately as a migration owner.
-- No login/password is created. Grant this group role to a separately provisioned
-- backend login, outside this file. Never use an anon/service-role key in the UI.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'logistimap_reader') THEN
        CREATE ROLE logistimap_reader NOLOGIN;
    END IF;
END $$;
GRANT USAGE ON SCHEMA public TO logistimap_reader;
-- Add GRANT USAGE ON SCHEMA extensions if PostGIS lives there.
GRANT SELECT ON datasets, categories, spatial_features, feature_categories,
    alembic_version TO logistimap_reader;
CREATE POLICY reader_datasets ON datasets FOR SELECT TO logistimap_reader USING (true);
CREATE POLICY reader_categories ON categories FOR SELECT TO logistimap_reader USING (true);
CREATE POLICY reader_features ON spatial_features FOR SELECT TO logistimap_reader USING (true);
CREATE POLICY reader_memberships ON feature_categories FOR SELECT TO logistimap_reader USING (true);
-- Example, performed separately with your real backend login:
-- GRANT logistimap_reader TO your_backend_login;
-- Policy creation is intentionally one-time; do not repeatedly run unchanged.
