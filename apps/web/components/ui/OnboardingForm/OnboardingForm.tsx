'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Button from '@/components/ui/Button';
import { createClient } from '@/utils/supabase/client';
import { createStudentProfile } from '@/utils/supabase/profile';

const MIN_MCAT_SCORE = 472;
const MAX_MCAT_SCORE = 528;

interface OnboardingFormProps {
  userId: string;
}

export default function OnboardingForm({ userId }: OnboardingFormProps) {
  const router = useRouter();
  const [testDate, setTestDate] = useState('');
  const [scoreGoal, setScoreGoal] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const supabase = createClient();
      await createStudentProfile(supabase, {
        userId,
        testDate,
        scoreGoal: Number(scoreGoal)
      });
      router.push('/dashboard');
    } catch (err) {
      // AC6: insert failure (e.g. RLS denial) shows an inline error and
      // keeps the user on /onboarding rather than redirecting.
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong saving your profile. Please try again.'
      );
      setIsSubmitting(false);
    }
  };

  return (
    <form noValidate={true} className="mb-4" onSubmit={handleSubmit}>
      <div className="grid gap-4">
        <div className="grid gap-1">
          <label htmlFor="test_date">Test date</label>
          <input
            id="test_date"
            type="date"
            name="test_date"
            required
            value={testDate}
            onChange={(e) => setTestDate(e.target.value)}
            className="w-full p-3 rounded-md bg-zinc-800"
          />
        </div>
        <div className="grid gap-1">
          <label htmlFor="score_goal">Target score</label>
          <input
            id="score_goal"
            type="number"
            name="score_goal"
            required
            min={MIN_MCAT_SCORE}
            max={MAX_MCAT_SCORE}
            placeholder={`${MIN_MCAT_SCORE}-${MAX_MCAT_SCORE}`}
            value={scoreGoal}
            onChange={(e) => setScoreGoal(e.target.value)}
            className="w-full p-3 rounded-md bg-zinc-800"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <Button
          variant="slim"
          type="submit"
          className="mt-1"
          loading={isSubmitting}
        >
          Continue to dashboard
        </Button>
      </div>
    </form>
  );
}
