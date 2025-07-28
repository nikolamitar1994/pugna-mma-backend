-- MMA Database Schema
-- Core tables for comprehensive MMA data management

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    abbreviation VARCHAR(10) NOT NULL UNIQUE,
    founded_date DATE,
    headquarters VARCHAR(255),
    website VARCHAR(255),
    logo_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weight classes table
CREATE TABLE weight_classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(100) NOT NULL,
    weight_limit_lbs INTEGER NOT NULL,
    weight_limit_kg DECIMAL(5,2) NOT NULL,
    gender VARCHAR(10) CHECK (gender IN ('male', 'female')) DEFAULT 'male',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fighters table with structured names
CREATE TABLE fighters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) DEFAULT '',
    full_name VARCHAR(255) GENERATED ALWAYS AS (
        CASE 
            WHEN last_name = '' THEN first_name
            ELSE CONCAT(first_name, ' ', last_name)
        END
    ) STORED,
    display_name VARCHAR(255),
    birth_first_name VARCHAR(100),
    birth_last_name VARCHAR(100),
    nickname VARCHAR(255),
    date_of_birth DATE,
    birth_place VARCHAR(255),
    nationality VARCHAR(100),
    height_cm INTEGER,
    weight_kg DECIMAL(5,2),
    reach_cm INTEGER,
    stance VARCHAR(20) CHECK (stance IN ('orthodox', 'southpaw', 'switch')),
    fighting_out_of VARCHAR(255),
    team VARCHAR(255),
    years_active VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    profile_image_url TEXT,
    wikipedia_url TEXT,
    social_media JSONB DEFAULT '{}',
    
    -- Career statistics
    total_fights INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    no_contests INTEGER DEFAULT 0,
    
    -- Win breakdown
    wins_by_ko INTEGER DEFAULT 0,
    wins_by_tko INTEGER DEFAULT 0,
    wins_by_submission INTEGER DEFAULT 0,
    wins_by_decision INTEGER DEFAULT 0,
    
    -- Data source tracking
    data_source VARCHAR(50) DEFAULT 'manual',
    data_quality_score DECIMAL(3,2) DEFAULT 0.0,
    last_data_update TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fighter name variations for search
CREATE TABLE fighter_name_variations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fighter_id UUID REFERENCES fighters(id) ON DELETE CASCADE,
    first_name_variation VARCHAR(100),
    last_name_variation VARCHAR(100),
    full_name_variation VARCHAR(255),
    variation_type VARCHAR(50) DEFAULT 'alternative',
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events table
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    event_number INTEGER,
    date DATE NOT NULL,
    location VARCHAR(255) NOT NULL,
    venue VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    
    -- Event details
    attendance INTEGER,
    gate_revenue DECIMAL(12,2),
    ppv_buys INTEGER,
    broadcast_info JSONB DEFAULT '{}',
    
    -- Status and metadata
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'live', 'completed', 'cancelled', 'postponed')),
    poster_url TEXT,
    wikipedia_url TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fights table
CREATE TABLE fights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    weight_class_id UUID REFERENCES weight_classes(id),
    
    -- Fight details
    fight_order INTEGER NOT NULL,
    is_main_event BOOLEAN DEFAULT false,
    is_title_fight BOOLEAN DEFAULT false,
    is_interim_title BOOLEAN DEFAULT false,
    scheduled_rounds INTEGER DEFAULT 3,
    
    -- Fight outcome
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'live', 'completed', 'cancelled', 'no_contest')),
    winner_id UUID REFERENCES fighters(id),
    method VARCHAR(50),
    method_details VARCHAR(255),
    ending_round INTEGER,
    ending_time VARCHAR(10),
    referee VARCHAR(100),
    
    -- Performance bonuses
    performance_bonuses JSONB DEFAULT '[]',
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fight participants (many-to-many between fights and fighters)
CREATE TABLE fight_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID REFERENCES fights(id) ON DELETE CASCADE,
    fighter_id UUID REFERENCES fighters(id) ON DELETE CASCADE,
    corner VARCHAR(10) CHECK (corner IN ('red', 'blue')),
    result VARCHAR(20) CHECK (result IN ('win', 'loss', 'draw', 'no_contest')),
    weigh_in_weight DECIMAL(5,2),
    purse DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fight_id, fighter_id),
    UNIQUE(fight_id, corner)
);

-- Fight statistics
CREATE TABLE fight_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID REFERENCES fights(id) ON DELETE CASCADE UNIQUE,
    fighter1_id UUID REFERENCES fighters(id),
    fighter2_id UUID REFERENCES fighters(id),
    
    -- Striking statistics
    fighter1_strikes_landed INTEGER DEFAULT 0,
    fighter1_strikes_attempted INTEGER DEFAULT 0,
    fighter2_strikes_landed INTEGER DEFAULT 0,
    fighter2_strikes_attempted INTEGER DEFAULT 0,
    
    -- Grappling statistics
    fighter1_takedowns INTEGER DEFAULT 0,
    fighter1_takedown_attempts INTEGER DEFAULT 0,
    fighter2_takedowns INTEGER DEFAULT 0,
    fighter2_takedown_attempts INTEGER DEFAULT 0,
    
    -- Control time (in seconds)
    fighter1_control_time INTEGER DEFAULT 0,
    fighter2_control_time INTEGER DEFAULT 0,
    
    -- Additional statistics stored as JSON
    detailed_stats JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scorecards for decision fights
CREATE TABLE scorecards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID REFERENCES fights(id) ON DELETE CASCADE,
    judge_name VARCHAR(100) NOT NULL,
    fighter1_score INTEGER NOT NULL,
    fighter2_score INTEGER NOT NULL,
    round_scores JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rankings
CREATE TABLE rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    weight_class_id UUID REFERENCES weight_classes(id),
    fighter_id UUID REFERENCES fighters(id),
    rank_position INTEGER NOT NULL,
    ranking_date DATE NOT NULL,
    is_champion BOOLEAN DEFAULT false,
    is_interim_champion BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, weight_class_id, rank_position, ranking_date)
);

-- Content management
CREATE TABLE content_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id UUID REFERENCES content_categories(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID REFERENCES content_categories(id),
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    excerpt TEXT,
    content TEXT,
    content_type VARCHAR(20) DEFAULT 'article' CHECK (content_type IN ('article', 'news', 'blog', 'video')),
    
    -- Media
    featured_image_url TEXT,
    video_url TEXT,
    video_duration INTEGER,
    
    -- SEO and metadata
    meta_title VARCHAR(255),
    meta_description TEXT,
    tags JSONB DEFAULT '[]',
    
    -- Publishing
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    published_at TIMESTAMP,
    author_id UUID,
    
    -- Engagement
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content-Fighter relationships
CREATE TABLE content_fighters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    fighter_id UUID REFERENCES fighters(id) ON DELETE CASCADE,
    relevance VARCHAR(20) DEFAULT 'mentioned' CHECK (relevance IN ('primary', 'secondary', 'mentioned')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, fighter_id)
);

-- Content-Event relationships
CREATE TABLE content_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id UUID REFERENCES content(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    relevance VARCHAR(20) DEFAULT 'mentioned' CHECK (relevance IN ('primary', 'secondary', 'mentioned')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, event_id)
);

-- Users table for authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'editor', 'user')),
    
    -- OAuth fields
    google_id VARCHAR(255),
    facebook_id VARCHAR(255),
    
    -- Profile
    avatar_url TEXT,
    bio TEXT,
    preferences JSONB DEFAULT '{}',
    
    -- Account status
    is_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API keys for external access
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    permissions JSONB DEFAULT '{}',
    rate_limit INTEGER DEFAULT 1000,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_fighters_names ON fighters USING gin(to_tsvector('english', full_name));
CREATE INDEX idx_fighters_first_last ON fighters(last_name, first_name);
CREATE INDEX idx_fighters_nationality ON fighters(nationality);
CREATE INDEX idx_fighters_active ON fighters(is_active);

CREATE INDEX idx_events_date ON events(date DESC);
CREATE INDEX idx_events_organization ON events(organization_id);
CREATE INDEX idx_events_status ON events(status);

CREATE INDEX idx_fights_event ON fights(event_id);
CREATE INDEX idx_fights_status ON fights(status);
CREATE INDEX idx_fights_date ON fights(event_id, fight_order);

CREATE INDEX idx_fight_participants_fighter ON fight_participants(fighter_id);
CREATE INDEX idx_fight_participants_fight ON fight_participants(fight_id);

CREATE INDEX idx_content_status_published ON content(status, published_at DESC);
CREATE INDEX idx_content_category ON content(category_id);
CREATE INDEX idx_content_type ON content(content_type);

CREATE INDEX idx_rankings_current ON rankings(organization_id, weight_class_id, ranking_date DESC);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_fighters_updated_at BEFORE UPDATE ON fighters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fights_updated_at BEFORE UPDATE ON fights FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_content_updated_at BEFORE UPDATE ON content FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data
INSERT INTO organizations (name, abbreviation, founded_date, headquarters, website) VALUES
('Ultimate Fighting Championship', 'UFC', '1993-11-12', 'Las Vegas, Nevada, USA', 'https://www.ufc.com'),
('Konfrontacja Sztuk Walki', 'KSW', '2004-05-01', 'Warsaw, Poland', 'https://www.ksw.com'),
('Oktagon MMA', 'Oktagon', '2016-01-01', 'Prague, Czech Republic', 'https://www.oktagon.sport'),
('Professional Fighters League', 'PFL', '2017-12-31', 'New York, USA', 'https://www.pflmma.com');

-- Insert weight classes for UFC (male divisions)
INSERT INTO weight_classes (organization_id, name, weight_limit_lbs, weight_limit_kg, gender) 
SELECT id, 'Flyweight', 125, 56.7, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Bantamweight', 135, 61.2, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Featherweight', 145, 65.8, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Lightweight', 155, 70.3, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Welterweight', 170, 77.1, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Middleweight', 185, 83.9, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Light Heavyweight', 205, 93.0, 'male' FROM organizations WHERE abbreviation = 'UFC'
UNION ALL
SELECT id, 'Heavyweight', 265, 120.2, 'male' FROM organizations WHERE abbreviation = 'UFC';

-- Insert content categories
INSERT INTO content_categories (name, slug, description) VALUES
('News', 'news', 'Latest MMA news and updates'),
('Fight Previews', 'fight-previews', 'Upcoming fight analysis and predictions'),
('Fighter Profiles', 'fighter-profiles', 'In-depth fighter biographies and analysis'),
('Event Recaps', 'event-recaps', 'Post-event analysis and highlights'),
('Interviews', 'interviews', 'Fighter and industry interviews'),
('Analysis', 'analysis', 'Technical fight breakdowns and analysis');