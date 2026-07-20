import Logo from '@/components/icons/Logo';

export interface SidebarProps {
  displayName: string;
  testDate: string | null;
  scoreGoal: number | null;
  currentScore: number | null;
}

// Days remaining until testDate, floored at 0 (a past test date reads as
// "Test day!" rather than a negative number -- SPEC.md Gaps & Assumptions).
function daysUntilTest(testDate: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(testDate);
  target.setHours(0, 0, 0, 0);
  const diffMs = target.getTime() - today.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export default function Sidebar({
  displayName,
  testDate,
  scoreGoal,
  currentScore
}: SidebarProps) {
  const daysToGo = testDate ? daysUntilTest(testDate) : null;

  // AC2: current_score is null for every fresh account (onboarding never
  // sets it) -- empty/0-state progress bar, not NaN.
  const progressPercent =
    scoreGoal && currentScore ? Math.min(100, Math.round((currentScore / scoreGoal) * 100)) : 0;

  return (
    <aside className="flex flex-col gap-6 w-full md:w-64 shrink-0 p-4 border-r border-zinc-800">
      <div className="flex items-center gap-2">
        <Logo />
        <span className="font-bold text-white">MCATai</span>
      </div>

      <div>
        <p className="text-sm text-zinc-400">Welcome back</p>
        <p className="font-semibold text-white">{displayName}</p>
      </div>

      <div>
        <p className="text-sm text-zinc-400">Test date</p>
        <p className="text-white">
          {daysToGo === null
            ? 'Not set'
            : daysToGo > 0
              ? `${daysToGo} days to go`
              : 'Test day!'}
        </p>
      </div>

      <div>
        <p className="mb-1 text-sm text-zinc-400">Practice score</p>
        <div
          className="w-full h-2 overflow-hidden rounded-full bg-zinc-800"
          role="progressbar"
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full"
            style={{
              width: `${progressPercent}%`,
              backgroundColor: 'var(--brand-primary, #ffffff)'
            }}
          />
        </div>
        <p className="mt-1 text-xs text-zinc-500">
          {currentScore ?? '—'} / {scoreGoal ?? '—'}
        </p>
      </div>
    </aside>
  );
}
