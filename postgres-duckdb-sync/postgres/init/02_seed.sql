INSERT INTO public.subscriptions (email, plan, lifetime_value)
VALUES
    ('alicia@example.com', 'starter', 199.00),
    ('bryan@example.com', 'free', 0),
    ('carla@example.com', 'growth', 1299.00),
    ('diego@example.com', 'enterprise', 20000.00),
    ('emily@example.com', 'starter', 299.00)
ON CONFLICT (email) DO NOTHING;
