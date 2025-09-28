-- Initialize PostgreSQL database for FlushBot
-- This file is automatically executed when PostgreSQL container starts

-- Create database (if not exists)
-- Note: Database is created by POSTGRES_DB environment variable

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE flushbot TO flushbot;

-- Create schema (optional - can be handled by SQLAlchemy)
-- The application will create tables automatically via SQLAlchemy