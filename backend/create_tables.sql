-- SQL Script to Create TruthChain Database Tables
-- Run this inside Docker: docker exec -it truthchain_db psql -U truthchain -d truthchain -f create_tables.sql

-- Organizations Table
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    monthly_quota INTEGER NOT NULL DEFAULT 10000,
    usage_current_month INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_organizations_email ON organizations(email);
CREATE INDEX IF NOT EXISTS idx_organizations_tier ON organizations(tier);

-- API Keys Table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(organization_id);
CREATE INDEX IF NOT  EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Validation Logs Table  
CREATE TABLE IF NOT EXISTS validation_logs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    validation_id VARCHAR(255) UNIQUE NOT NULL,
    input_data JSONB NOT NULL,
    output_data JSONB,
    rules_applied JSONB NOT NULL,
    result VARCHAR(20) NOT NULL,
    violations JSONB,
    auto_corrected BOOLEAN NOT NULL DEFAULT FALSE,
    latency_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_logs_org ON validation_logs(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validation_logs_result ON validation_logs(result);
CREATE INDEX IF NOT EXISTS idx_validation_logs_validation_id ON validation_logs(validation_id);

-- Display created tables
\dt
