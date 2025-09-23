-- Create sample tables
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    amount DECIMAL(10,2),
    status VARCHAR(50),
    order_date DATE
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    category VARCHAR(100),
    price DECIMAL(10,2),
    description TEXT
);

-- Insert sample data
INSERT INTO customers (name, email) VALUES
    ('Alice Johnson', 'alice@example.com'),
    ('Bob Smith', 'bob@example.com'),
    ('Carol White', 'carol@example.com');

INSERT INTO products (name, category, price, description) VALUES
    ('Laptop Pro', 'Electronics', 1299.99, 'High-performance laptop for professionals'),
    ('Wireless Mouse', 'Accessories', 29.99, 'Ergonomic wireless mouse'),
    ('USB-C Hub', 'Accessories', 49.99, '7-port USB-C hub with HDMI');

INSERT INTO orders (customer_id, amount, status, order_date) VALUES
    (1, 1329.98, 'completed', '2024-01-15'),
    (2, 29.99, 'completed', '2024-01-20'),
    (3, 1379.97, 'pending', '2024-01-25');
