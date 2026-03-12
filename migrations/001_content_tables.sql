-- Content OS database schema
-- Works with both Supabase Postgres (ops schema) and SQLite (no schema prefix)

-- For Supabase: ensure ops schema exists
CREATE SCHEMA IF NOT EXISTS ops;

-- Content tracking: idea → outline → draft → review → scheduled → published → archived
CREATE TABLE IF NOT EXISTS ops.content_items (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL CHECK (platform IN ('youtube', 'linkedin')),
    content_type TEXT NOT NULL,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'idea'
        CHECK (status IN ('idea', 'outline', 'draft', 'review', 'scheduled', 'published', 'archived')),
    title TEXT,
    body TEXT,
    metadata JSONB DEFAULT '{}',
    source_type TEXT,
    source_id TEXT,
    pillar INTEGER,
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_platform_status ON ops.content_items(platform, status);
CREATE INDEX IF NOT EXISTS idx_content_scheduled ON ops.content_items(scheduled_for) WHERE scheduled_for IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_pillar ON ops.content_items(pillar) WHERE pillar IS NOT NULL;

-- Weekly theme template
CREATE TABLE IF NOT EXISTS ops.content_calendar (
    id SERIAL PRIMARY KEY,
    day_of_week TEXT NOT NULL,
    theme TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Competitor tracking
CREATE TABLE IF NOT EXISTS ops.channels (
    id SERIAL PRIMARY KEY,
    handle TEXT UNIQUE NOT NULL,
    name TEXT,
    subscriber_count INTEGER,
    metadata JSONB DEFAULT '{}',
    last_checked TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.processed_videos (
    id SERIAL PRIMARY KEY,
    video_id TEXT UNIQUE NOT NULL,
    channel_handle TEXT,
    title TEXT,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    duration_seconds INTEGER,
    published_at TIMESTAMPTZ,
    transcript TEXT,
    analysis JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.contrarian_angles (
    id SERIAL PRIMARY KEY,
    video_id TEXT,
    angle_title TEXT,
    angle_description TEXT,
    risk_score INTEGER,
    reward_score INTEGER,
    status TEXT DEFAULT 'new',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- News monitoring
CREATE TABLE IF NOT EXISTS ops.news_items (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE,
    description TEXT,
    relevance_score INTEGER DEFAULT 0,
    content_angle TEXT,
    metadata JSONB DEFAULT '{}',
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SEO tracking
CREATE TABLE IF NOT EXISTS ops.seo_suggestions (
    id SERIAL PRIMARY KEY,
    seed_keyword TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    source TEXT DEFAULT 'autocomplete',
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ops.seo_trends (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    trend_type TEXT,
    trend_value TEXT,
    region TEXT DEFAULT 'US',
    metadata JSONB DEFAULT '{}',
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.seo_rising_queries (
    id SERIAL PRIMARY KEY,
    seed_keyword TEXT NOT NULL,
    rising_query TEXT NOT NULL,
    rise_value TEXT,
    metadata JSONB DEFAULT '{}',
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.seo_rising_videos (
    id SERIAL PRIMARY KEY,
    video_id TEXT NOT NULL,
    title TEXT,
    channel TEXT,
    view_count INTEGER,
    view_velocity REAL,
    published_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ops.seo_reports (
    id SERIAL PRIMARY KEY,
    report_type TEXT NOT NULL,
    report_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
