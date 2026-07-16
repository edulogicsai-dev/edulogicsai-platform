create table episodic_memory (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  student_id uuid not null,
  session_id uuid not null references agent_sessions(id) on delete cascade,
  summary text not null,
  embedding vector(1536),
  relevance_score real check (relevance_score is null or (relevance_score >= 0 and relevance_score <= 1)),
  occurred_at timestamptz not null default now(),
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

create index episodic_memory_embedding_idx on episodic_memory
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index episodic_memory_student_tenant_idx on episodic_memory (student_id, tenant_id);

alter table episodic_memory enable row level security;

create policy "Students can view own episodic memory." on episodic_memory
  for select using (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can insert own episodic memory." on episodic_memory
  for insert with check (auth.uid() = student_id and tenant_id = current_tenant());
