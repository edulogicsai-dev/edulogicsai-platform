import { PropsWithChildren } from 'react';
import { redirect } from 'next/navigation';
import { createClient } from '@/utils/supabase/server';
import { getStudentProfile, getDisplayName, DOMAIN_ID } from '@/utils/supabase/profile';
import { mcatTheme } from '@/lib/theme/mcatTheme';
import DashboardShell from '@/components/ui/Dashboard/DashboardShell';

// FR1: theme + auth/profile gate for the whole /dashboard route tree.
// Fetched once here (not duplicated in page.tsx) since a redirect() thrown
// during layout render aborts the page render too.
export default async function DashboardLayout({ children }: PropsWithChildren) {
  const supabase = createClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();

  if (!user) {
    return redirect('/signin');
  }

  const profile = await getStudentProfile(supabase, user.id, DOMAIN_ID);
  if (!profile) {
    return redirect('/onboarding');
  }

  const displayName = await getDisplayName(supabase, user.id);

  return (
    <div style={mcatTheme as React.CSSProperties}>
      <DashboardShell
        sidebar={{
          displayName,
          testDate: profile.test_date,
          scoreGoal: profile.score_goal,
          currentScore: profile.current_score
        }}
      >
        {children}
      </DashboardShell>
    </div>
  );
}
