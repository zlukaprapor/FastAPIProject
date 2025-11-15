-- PostgreSQL migration for Travel Planner API
-- Travel Plans (main entity)
CREATE TABLE travel_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL CHECK (LENGTH(TRIM(title)) > 0),
    description TEXT,
    start_date DATE,
    end_date DATE,
    budget DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD' CHECK (LENGTH(currency) = 3),
    is_public BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1 CHECK (version > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    CHECK (budget IS NULL OR budget >= 0)
);

-- Locations with ordered visits
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    travel_plan_id UUID NOT NULL REFERENCES travel_plans(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL CHECK (LENGTH(TRIM(name)) > 0),
    address TEXT,
    latitude DECIMAL(10, 6),
    longitude DECIMAL(11, 6),
    visit_order INTEGER CHECK (visit_order > 0),
    arrival_date TIMESTAMP WITH TIME ZONE,
    departure_date TIMESTAMP WITH TIME ZONE,
    budget DECIMAL(10,2),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    CHECK (departure_date IS NULL OR arrival_date IS NULL OR departure_date >= arrival_date),
    CHECK (budget IS NULL OR budget >= 0),
    UNIQUE (travel_plan_id, visit_order)
);

-- Performance indexes
CREATE INDEX idx_travel_plans_dates ON travel_plans(start_date, end_date) WHERE start_date IS NOT NULL;
CREATE INDEX idx_travel_plans_public ON travel_plans(is_public, updated_at DESC) WHERE is_public = TRUE;
CREATE INDEX idx_travel_plans_updated ON travel_plans(updated_at DESC);

CREATE INDEX idx_locations_plan_order ON locations(travel_plan_id, visit_order);
CREATE INDEX idx_locations_coordinates ON locations(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_travel_plans_updated_at 
    BEFORE UPDATE ON travel_plans 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();