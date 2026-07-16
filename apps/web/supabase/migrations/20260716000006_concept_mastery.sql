create table concept_mastery (
  student_id uuid not null,
  tenant_id text not null references tenants(id),
  concept_id text not null check (concept_id like '%::%'),
  ease_factor real not null default 2.5,
  next_review date,
  last_reviewed_at timestamptz,
  review_count int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (student_id, tenant_id, concept_id),
  foreign key (student_id, tenant_id) references student_profiles(user_id, tenant_id) on delete cascade
);

alter table concept_mastery enable row level security;

create policy "Students can view own mastery." on concept_mastery
  for select using (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can insert own mastery." on concept_mastery
  for insert with check (auth.uid() = student_id and tenant_id = current_tenant());

create policy "Students can update own mastery." on concept_mastery
  for update using (auth.uid() = student_id and tenant_id = current_tenant());
