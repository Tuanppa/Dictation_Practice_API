🔍 Config loaded - DATABASE_URL: postgresql://localhost/dictation_practic...
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 7c4058171e17

DROP TYPE IF EXISTS rankingmodeenum CASCADE;

CREATE TYPE rankingmodeenum AS ENUM (
            'all_time',
            'last_month',
            'current_month', 
            'last_week',
            'current_week',
            'by_lesson'
        );

ALTER TABLE top_performance_overall 
        ALTER COLUMN mode TYPE rankingmodeenum 
        USING mode::text::rankingmodeenum;

✅ Migration completed successfully!
📊 New ranking modes available:
   - all_time (unchanged)
   - last_month (NEW - for hall of fame)
   - current_month (NEW - live leaderboard)
   - last_week (NEW - for hall of fame)
   - current_week (NEW - live leaderboard)
   - by_lesson (unchanged)
INSERT INTO alembic_version (version_num) VALUES ('7c4058171e17') RETURNING alembic_version.version_num;

COMMIT;

