create table tenants (
  id text primary key,
  name text not null,
  subdomain text not null unique,
  created_at timestamptz not null default now()
);

alter table tenants enable row level security;
create policy "Public read access to tenants." on tenants for select using (true);

insert into tenants (id, name, subdomain) values
  ('mcat', 'MCATai', 'app.mcatai.co');

create or replace function current_tenant() returns text
language sql stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'tenant_id',
    nullif(current_setting('app.tenant_id', true), '')
  );
$$;

create extension if not exists vector;
