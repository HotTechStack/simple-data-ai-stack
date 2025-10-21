-- Database initialization for orders pipeline
-- This demonstrates production-ready schema design with Postgres 18

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- LOOKUP TABLES (Small reference data cached in Redis)
-- ==========================================

CREATE TABLE IF NOT EXISTS product_catalog (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS currency_rates (
    currency_code CHAR(3) PRIMARY KEY,
    rate_to_usd DECIMAL(10, 6) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS zip_code_zones (
    zip_code VARCHAR(10) PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    country CHAR(2) NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    shipping_zone INT NOT NULL
);

-- ==========================================
-- STAGING TABLES (UNLOGGED for faster writes)
-- ==========================================

-- Raw incoming orders (UNLOGGED = no WAL overhead, 3x faster writes)
CREATE UNLOGGED TABLE IF NOT EXISTS orders_staging (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    order_timestamp TIMESTAMP NOT NULL,
    raw_data JSONB,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_timestamp ON orders_staging(order_timestamp);
CREATE INDEX IF NOT EXISTS idx_staging_ingested ON orders_staging(ingested_at);

-- ==========================================
-- PRODUCTION TABLES (Durable storage)
-- ==========================================

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    total_amount_usd DECIMAL(12, 2) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    country CHAR(2) NOT NULL,
    shipping_zone INT NOT NULL,
    order_timestamp TIMESTAMP NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product FOREIGN KEY (product_id) REFERENCES product_catalog(product_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders(order_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_category ON orders(category);
CREATE INDEX IF NOT EXISTS idx_orders_processed ON orders(processed_at);

-- ==========================================
-- MATERIALIZED VIEWS (Pre-computed aggregations)
-- ==========================================

-- Hourly sales summary
CREATE MATERIALIZED VIEW IF NOT EXISTS sales_hourly AS
SELECT
    DATE_TRUNC('hour', order_timestamp) AS hour,
    category,
    COUNT(*) AS order_count,
    SUM(quantity) AS total_units,
    SUM(total_amount_usd) AS total_revenue_usd,
    AVG(total_amount_usd) AS avg_order_value_usd,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM orders
GROUP BY DATE_TRUNC('hour', order_timestamp), category;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_hourly_unique ON sales_hourly(hour, category);

-- Daily product performance
CREATE MATERIALIZED VIEW IF NOT EXISTS product_performance_daily AS
SELECT
    DATE_TRUNC('day', order_timestamp) AS day,
    product_id,
    product_name,
    category,
    COUNT(*) AS order_count,
    SUM(quantity) AS total_units_sold,
    SUM(total_amount_usd) AS total_revenue_usd
FROM orders
GROUP BY DATE_TRUNC('day', order_timestamp), product_id, product_name, category;

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_perf_unique ON product_performance_daily(day, product_id);

-- Shipping zone analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS shipping_zone_stats AS
SELECT
    shipping_zone,
    country,
    COUNT(*) AS order_count,
    SUM(total_amount_usd) AS total_revenue_usd,
    AVG(total_amount_usd) AS avg_order_value_usd,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM orders
GROUP BY shipping_zone, country;

CREATE UNIQUE INDEX IF NOT EXISTS idx_shipping_zone_unique ON shipping_zone_stats(shipping_zone, country);

-- ==========================================
-- SEED DATA FOR LOOKUPS
-- ==========================================

INSERT INTO product_catalog (product_id, product_name, category, base_price) VALUES
    ('PROD-001', 'Laptop Pro 15"', 'Electronics', 1299.99),
    ('PROD-002', 'Wireless Mouse', 'Electronics', 29.99),
    ('PROD-003', 'USB-C Hub', 'Electronics', 49.99),
    ('PROD-004', 'Mechanical Keyboard', 'Electronics', 149.99),
    ('PROD-005', 'Office Chair', 'Furniture', 299.99),
    ('PROD-006', 'Standing Desk', 'Furniture', 599.99),
    ('PROD-007', 'Monitor 27"', 'Electronics', 399.99),
    ('PROD-008', 'Webcam HD', 'Electronics', 79.99),
    ('PROD-009', 'Desk Lamp', 'Furniture', 39.99),
    ('PROD-010', 'Cable Organizer', 'Accessories', 19.99),
    ('PROD-011', 'Headphones', 'Electronics', 199.99),
    ('PROD-012', 'Notebook Set', 'Stationery', 24.99),
    ('PROD-013', 'Pen Pack', 'Stationery', 9.99),
    ('PROD-014', 'Water Bottle', 'Accessories', 14.99),
    ('PROD-015', 'Backpack', 'Accessories', 79.99)
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO currency_rates (currency_code, rate_to_usd) VALUES
    ('USD', 1.000000),
    ('EUR', 0.920000),
    ('GBP', 0.790000),
    ('CAD', 1.350000),
    ('AUD', 1.520000),
    ('JPY', 149.500000),
    ('INR', 83.200000)
ON CONFLICT (currency_code) DO NOTHING;

INSERT INTO zip_code_zones (zip_code, city, state, country, timezone, shipping_zone) VALUES
    ('10001', 'New York', 'NY', 'US', 'America/New_York', 1),
    ('94102', 'San Francisco', 'CA', 'US', 'America/Los_Angeles', 2),
    ('60601', 'Chicago', 'IL', 'US', 'America/Chicago', 1),
    ('02101', 'Boston', 'MA', 'US', 'America/New_York', 1),
    ('98101', 'Seattle', 'WA', 'US', 'America/Los_Angeles', 2),
    ('33101', 'Miami', 'FL', 'US', 'America/New_York', 3),
    ('75201', 'Dallas', 'TX', 'US', 'America/Chicago', 3),
    ('80201', 'Denver', 'CO', 'US', 'America/Denver', 2),
    ('M5H2N2', 'Toronto', 'ON', 'CA', 'America/Toronto', 1),
    ('V6B1A1', 'Vancouver', 'BC', 'CA', 'America/Vancouver', 2)
ON CONFLICT (zip_code) DO NOTHING;

-- ==========================================
-- HELPER FUNCTIONS
-- ==========================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY sales_hourly;
    REFRESH MATERIALIZED VIEW CONCURRENTLY product_performance_daily;
    REFRESH MATERIALIZED VIEW CONCURRENTLY shipping_zone_stats;
END;
$$ LANGUAGE plpgsql;

-- Function to promote staging data to production
CREATE OR REPLACE FUNCTION promote_staging_to_production()
RETURNS TABLE(inserted_count BIGINT) AS $$
BEGIN
    WITH inserted AS (
        INSERT INTO orders (
            order_id, customer_id, product_id, product_name, category,
            quantity, unit_price, currency, total_amount_usd,
            zip_code, city, state, country, shipping_zone, order_timestamp
        )
        SELECT
            s.order_id,
            s.customer_id,
            s.product_id,
            p.product_name,
            p.category,
            s.quantity,
            s.unit_price,
            s.currency,
            s.unit_price * s.quantity * c.rate_to_usd AS total_amount_usd,
            s.zip_code,
            z.city,
            z.state,
            z.country,
            z.shipping_zone,
            s.order_timestamp
        FROM orders_staging s
        JOIN product_catalog p ON s.product_id = p.product_id
        JOIN currency_rates c ON s.currency = c.currency_code
        JOIN zip_code_zones z ON s.zip_code = z.zip_code
        ON CONFLICT (order_id) DO NOTHING
        RETURNING 1
    )
    SELECT COUNT(*) INTO inserted_count FROM inserted;

    -- Clear staging table after successful promotion
    TRUNCATE orders_staging;

    RETURN QUERY SELECT inserted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dataeng;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dataeng;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO dataeng;
