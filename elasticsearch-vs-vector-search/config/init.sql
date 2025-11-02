-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create products table with vector embeddings
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock_quantity INTEGER,
    error_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(384)  -- Using all-MiniLM-L6-v2 model (384 dimensions)
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS products_embedding_idx ON products
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create regular indexes for hybrid search
CREATE INDEX IF NOT EXISTS products_sku_idx ON products(sku);
CREATE INDEX IF NOT EXISTS products_category_idx ON products(category);
CREATE INDEX IF NOT EXISTS products_error_code_idx ON products(error_code);

-- Create logs table for demonstrating when NOT to use vector search
CREATE TABLE IF NOT EXISTS application_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_level VARCHAR(20),
    error_code VARCHAR(50),
    message TEXT,
    service_name VARCHAR(100),
    user_id VARCHAR(50)
);

-- Create index for efficient log searches (keyword search is better here)
CREATE INDEX IF NOT EXISTS logs_timestamp_idx ON application_logs(timestamp);
CREATE INDEX IF NOT EXISTS logs_error_code_idx ON application_logs(error_code);
CREATE INDEX IF NOT EXISTS logs_service_idx ON application_logs(service_name);

-- Insert some sample application logs
INSERT INTO application_logs (log_level, error_code, message, service_name, user_id) VALUES
('ERROR', 'ERR-1001', 'Database connection timeout', 'auth-service', 'user_123'),
('ERROR', 'ERR-1001', 'Database connection timeout', 'payment-service', 'user_456'),
('ERROR', 'ERR-2003', 'Invalid API key provided', 'api-gateway', 'user_789'),
('WARN', 'WARN-3005', 'Rate limit approaching threshold', 'api-gateway', 'user_123'),
('ERROR', 'ERR-4002', 'Payment processing failed', 'payment-service', 'user_456'),
('INFO', 'INFO-5001', 'User login successful', 'auth-service', 'user_123'),
('ERROR', 'ERR-1001', 'Database connection timeout', 'order-service', 'user_789'),
('ERROR', 'ERR-6004', 'Cache miss - Redis unavailable', 'cache-service', 'user_456');
