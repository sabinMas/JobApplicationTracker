-- Add Actor Framework Tables (Phase 5: Mini-Apify)

-- Actors: Registry of available scrapers
CREATE TABLE actors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    module_path VARCHAR(500) NOT NULL,
    input_schema JSONB,
    output_schema JSONB,
    is_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ScraperRuns: Track execution of each actor
CREATE TABLE scraper_runs (
    id SERIAL PRIMARY KEY,
    actor_name VARCHAR(100) NOT NULL REFERENCES actors(name),
    run_name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, success, failed, cancelled

    -- Configuration
    input_config JSONB NOT NULL,

    -- Execution
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- Results
    items_scraped INTEGER DEFAULT 0,
    dataset_id INTEGER,  -- FK to datasets.id (set below)
    error_message TEXT,
    log_entries JSONB DEFAULT '[]',

    -- Metadata
    webhook_url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Datasets: Results from scraper runs
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES scraper_runs(id),

    -- S3 Storage
    s3_bucket VARCHAR(200) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    item_count INTEGER DEFAULT 0,

    -- Schema
    item_schema JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add FK from scraper_runs.dataset_id to datasets.id
ALTER TABLE scraper_runs
ADD CONSTRAINT fk_scraper_runs_dataset_id
FOREIGN KEY (dataset_id) REFERENCES datasets(id);

-- Indexes for common queries
CREATE INDEX idx_scraper_runs_actor_status ON scraper_runs(actor_name, status);
CREATE INDEX idx_scraper_runs_status ON scraper_runs(status);
CREATE INDEX idx_scraper_runs_created ON scraper_runs(created_at DESC);
CREATE INDEX idx_datasets_run_id ON datasets(run_id);

-- Insert default actors
INSERT INTO actors (name, display_name, description, module_path, is_enabled) VALUES
('linkedin', 'LinkedIn Job Scraper', 'Scrapes LinkedIn jobs for a given query', 'app.scrapers.linkedin_actor', 1),
('indeed', 'Indeed Job Scraper', 'Scrapes Indeed jobs for a given query', 'app.scrapers.indeed_actor', 0),
('greenhouse', 'Greenhouse Job Scraper', 'Scrapes Greenhouse job boards', 'app.scrapers.greenhouse_actor', 0)
ON CONFLICT (name) DO NOTHING;
