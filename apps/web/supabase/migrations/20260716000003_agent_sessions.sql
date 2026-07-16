create table agent_sessions (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null references tenants(id),
  student_id uuid not null,
  agent_id text not null,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  turn_count int not null default 0,
  session_notes text,
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

create index agent_sessions_student_tenant_idx on agent_sessions (student_id, tenant_id);

alter table agent_sessions enable row level security;

create policy "Students can view own sessions." on agent_sessions
  for select using (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can insert own sessions." on agent_sessions
  for insert with check (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can update own sessions." on agent_sessions
  for update using (auth.uid() = student_id and tenant_id = current_tenant());
