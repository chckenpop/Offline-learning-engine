-- Interaction Logs Table
CREATE TABLE IF NOT EXISTS delivery_interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    lesson_id TEXT,
    concept_id TEXT,
    video_id TEXT, -- Added for video tracking
    question_id TEXT,
    event_type TEXT NOT NULL, -- 'answer', 'video_watch', 'video_skip'
    correct BOOLEAN,
    time_taken INTEGER, -- in seconds
    watch_percent INTEGER,
    skip_count INTEGER,
    attempt INTEGER DEFAULT 1,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Learning Profiles Table (Mastery Tracking)
CREATE TABLE IF NOT EXISTS delivery_user_profiles (
    user_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    mastery_probability FLOAT DEFAULT 0.1, -- Initial P(Knowledge)
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, concept_id)
);

-- Index for faster profile lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON delivery_user_profiles(user_id);
