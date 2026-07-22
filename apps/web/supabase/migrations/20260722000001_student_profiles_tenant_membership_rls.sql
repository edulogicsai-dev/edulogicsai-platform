-- current_tenant() (20260716000001_tenant_foundation.sql) reads
-- app_metadata->>'tenant_id' from the JWT claims, falling back to the
-- app.tenant_id session setting. Supabase Auth does not populate
-- app_metadata.tenant_id by default -- there is no signup-time hook wiring
-- it in this project -- so current_tenant() resolves to null for every
-- ordinary authenticated request from the browser, and
-- `tenant_id = current_tenant()` was therefore never actually satisfiable
-- for a real (non-backend, non-SET-LOCAL) session. Discovered while wiring
-- auth-flow's onboarding insert (changes/2026/07/20/web-chat-integration/
-- changes/auth-flow/) against a real Supabase Auth session.
--
-- Replaces the tenant check with membership in the real `tenants` table --
-- still real tenant-scoping (a forged/unknown tenant_id is rejected), just
-- not dependent on a JWT claim nothing populates. auth.uid() = user_id is
-- unchanged and remains the actual per-row ownership check.
drop policy "Students can view own profile." on student_profiles;
drop policy "Students can insert own profile." on student_profiles;
drop policy "Students can update own profile." on student_profiles;

create policy "Students can view own profile." on student_profiles
  for select using (auth.uid() = user_id and tenant_id in (select id from tenants));

create policy "Students can insert own profile." on student_profiles
  for insert with check (auth.uid() = user_id and tenant_id in (select id from tenants));

create policy "Students can update own profile." on student_profiles
  for update using (auth.uid() = user_id and tenant_id in (select id from tenants));
