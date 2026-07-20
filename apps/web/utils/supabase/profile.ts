import { SupabaseClient } from '@supabase/supabase-js';
import { Database, Tables } from '@/types_db';

type StudentProfile = Tables<'student_profiles'>;

// tenant_id is hardcoded to the mcat domain for this epic -- see
// changes/2026/07/20/web-chat-integration/SPEC.md Cross-Cutting Concerns.
export const DOMAIN_ID = process.env.NEXT_PUBLIC_DOMAIN_ID ?? 'mcat';

export async function getStudentProfile(
  supabase: SupabaseClient<Database>,
  userId: string,
  tenantId: string = DOMAIN_ID
): Promise<StudentProfile | null> {
  const { data, error } = await supabase
    .from('student_profiles')
    .select('*')
    .eq('user_id', userId)
    .eq('tenant_id', tenantId)
    .maybeSingle();

  if (error) throw error;
  return data;
}

export async function createStudentProfile(
  supabase: SupabaseClient<Database>,
  params: {
    userId: string;
    testDate: string;
    scoreGoal: number;
    tenantId?: string;
  }
): Promise<void> {
  const { userId, testDate, scoreGoal, tenantId = DOMAIN_ID } = params;

  // Relies on student_profiles' existing RLS insert policy
  // (auth.uid() = user_id and tenant_id = current_tenant()) -- must run
  // under the authenticated session, not the anon key alone. See
  // changes/2026/07/20/web-chat-integration/changes/auth-flow/SPEC.md FR3.
  const { error } = await supabase.from('student_profiles').insert({
    user_id: userId,
    tenant_id: tenantId,
    test_date: testDate,
    score_goal: scoreGoal
  });

  if (error) throw error;
}

// sse-chat-hook (web-chat-integration-2) calls this per-request rather than
// caching the token, so a refreshed session is always used.
export async function getAccessToken(
  supabase: SupabaseClient<Database>
): Promise<string | null> {
  const {
    data: { session }
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

// dashboard-layout (web-chat-integration-4): mirrors apps/backend's
// StudentProfileRepository.load_profile fallback ("Student" when
// full_name is unset) -- the email/password signup form never collects a
// name, so users.full_name is null for every account created via this
// epic's auth-flow.
export async function getDisplayName(
  supabase: SupabaseClient<Database>,
  userId: string
): Promise<string> {
  const { data, error } = await supabase
    .from('users')
    .select('full_name')
    .eq('id', userId)
    .maybeSingle();

  if (error) throw error;
  return data?.full_name ?? 'Student';
}
