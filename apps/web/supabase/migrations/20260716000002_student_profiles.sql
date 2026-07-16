create table student_profiles (
  user_id uuid not null references auth.users(id) on delete cascade,
  tenant_id text not null references tenants(id),
  test_date date,
  score_goal int,
  current_score int,
  study_streak int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, tenant_id)
);

alter table student_profiles enable row level security;

create policy "Students can view own profile." on student_profiles
  for select using (auth.uid() = user_id and tenant_id = current_tenant());

create policy "Students can insert own profile." on student_profiles
  for insert with check (auth.uid() = user_id and tenant_id = current_tenant());

create policy "Students can update own profile." on student_profiles
  for update using (auth.uid() = user_id and tenant_id = current_tenant());
