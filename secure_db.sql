-- Enable RLS on tables
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_bindings ENABLE ROW LEVEL SECURITY;

-- Create Policies
DROP POLICY IF EXISTS "Public can read sessions" ON sessions;
CREATE POLICY "Public can read sessions" ON sessions FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public can read attendance" ON attendance;
CREATE POLICY "Public can read attendance" ON attendance FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public can insert attendance" ON attendance;
CREATE POLICY "Public can insert attendance" ON attendance FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Public can insert device_bindings" ON device_bindings;
CREATE POLICY "Public can insert device_bindings" ON device_bindings FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Admin can delete sessions" ON sessions;
CREATE POLICY "Admin can delete sessions" ON sessions FOR DELETE USING (true);

DROP POLICY IF EXISTS "Admin can delete attendance" ON attendance;
CREATE POLICY "Admin can delete attendance" ON attendance FOR DELETE USING (true);

DROP POLICY IF EXISTS "Admin can delete device_bindings" ON device_bindings;
CREATE POLICY "Admin can delete device_bindings" ON device_bindings FOR DELETE USING (true);
