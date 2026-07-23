import { redirect } from 'next/navigation';
import { createClient } from '@/utils/supabase/server';
import { getStudentProfile, DOMAIN_ID } from '@/utils/supabase/profile';
import OnboardingForm from '@/components/ui/OnboardingForm/OnboardingForm';

// FR3 (auth-flow): collects test_date + score_goal and creates the
// student_profiles row a first-time signup doesn't have yet. Returning
// users (row already exists) are bounced straight to /dashboard -- AC3.
export default async function Onboarding() {
  const supabase = await createClient();
  const {
    data: { user }
  } = await supabase.auth.getUser();

  if (!user) {
    return redirect('/signin');
  }

  const existingProfile = await getStudentProfile(supabase, user.id, DOMAIN_ID);
  if (existingProfile) {
    return redirect('/dashboard');
  }

  return (
    <section className="mb-32 bg-black">
      <div className="max-w-xl px-4 py-8 mx-auto sm:px-6 sm:pt-24 lg:px-8">
        <div className="sm:align-center sm:flex sm:flex-col">
          <h1 className="text-4xl font-extrabold text-white sm:text-center sm:text-5xl">
            Let&apos;s set your MCAT goal
          </h1>
          <p className="max-w-xl m-auto mt-5 text-lg text-zinc-200 sm:text-center">
            Your test date and target score help ARIA, MIRA, and QUINN tailor
            your study plan.
          </p>
        </div>
        <div className="mt-8">
          <OnboardingForm userId={user.id} />
        </div>
      </div>
    </section>
  );
}
