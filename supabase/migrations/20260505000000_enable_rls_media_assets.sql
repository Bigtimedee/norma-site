-- Enable RLS on media_assets with no public policies.
-- Access is restricted to the service_role key only (server-side / Edge Functions).
ALTER TABLE public.media_assets ENABLE ROW LEVEL SECURITY;
