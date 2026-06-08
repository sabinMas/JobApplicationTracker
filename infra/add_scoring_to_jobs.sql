-- Migration: Add AgentCore Scoring columns to jobs table (Phase 4)
-- This adds support for job relevance scoring (1-10 scale)

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_reasoning TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_strengths JSON DEFAULT '[]';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_concerns JSON DEFAULT '[]';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_recommendation VARCHAR(50);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP WITH TIME ZONE;

-- Create index for faster filtering by score
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);

-- Add comment documenting the columns
COMMENT ON COLUMN jobs.score IS 'Job relevance score (1-10 scale from AgentCore)';
COMMENT ON COLUMN jobs.scored_at IS 'Timestamp when job was scored';

-- Migration complete
SELECT 'Migration complete: Added scoring columns to jobs table' as status;\n"