create table domain_content (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  source_id text not null,
  content text not null,
  embedding vector(1536),
  created_at timestamptz not null default now()
);

create index domain_content_embedding_idx on domain_content
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index domain_content_tenant_idx on domain_content (tenant_id);

alter table domain_content enable row level security;

create policy "Authenticated users can read own-tenant content." on domain_content
  for select using (tenant_id = current_tenant());
