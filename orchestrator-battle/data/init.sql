CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data for yesterday and today
INSERT INTO tickets (title, description, priority, created_at) VALUES
('Login page not loading', 'Users cannot access the login page, getting 500 error', 'high', CURRENT_DATE - INTERVAL '1 day'),
('Slow dashboard performance', 'Dashboard takes 30+ seconds to load with large datasets', 'medium', CURRENT_DATE - INTERVAL '1 day'),
('Email notifications delayed', 'User notifications are arriving 2-3 hours late', 'medium', CURRENT_DATE - INTERVAL '1 day'),
('Mobile app crashes on iOS', 'App crashes when user tries to upload files on iOS 17', 'high', CURRENT_DATE - INTERVAL '1 day'),
('Export feature missing data', 'CSV export only showing first 100 rows instead of all data', 'low', CURRENT_DATE - INTERVAL '1 day'),
('Search functionality broken', 'Search returns no results even for existing records', 'high', CURRENT_DATE),
('Password reset emails not sent', 'Users not receiving password reset emails', 'medium', CURRENT_DATE);
