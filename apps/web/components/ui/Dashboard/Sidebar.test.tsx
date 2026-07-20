import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Sidebar from './Sidebar';

function isoDateDaysFromNow(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

describe('Sidebar', () => {
  it('AC1: shows name, a future test-date countdown, and a progress bar reflecting current/goal', () => {
    render(
      <Sidebar
        displayName="Jordan"
        testDate={isoDateDaysFromNow(30)}
        scoreGoal={520}
        currentScore={480}
      />
    );

    expect(screen.getByText('Jordan')).toBeInTheDocument();
    expect(screen.getByText(/days to go/i)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '92');
    expect(screen.getByText('480 / 520')).toBeInTheDocument();
  });

  it('AC2: current_score null renders a 0-state progress bar without crashing or NaN', () => {
    expect(() =>
      render(
        <Sidebar
          displayName="Jordan"
          testDate={isoDateDaysFromNow(10)}
          scoreGoal={520}
          currentScore={null}
        />
      )
    ).not.toThrow();

    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
    expect(screen.getByText('— / 520')).toBeInTheDocument();
  });

  it('shows "Test day!" for a test date in the past rather than a negative number', () => {
    render(
      <Sidebar
        displayName="Jordan"
        testDate={isoDateDaysFromNow(-5)}
        scoreGoal={520}
        currentScore={null}
      />
    );

    expect(screen.getByText('Test day!')).toBeInTheDocument();
  });

  it('shows "Not set" when no test date exists', () => {
    render(
      <Sidebar displayName="Jordan" testDate={null} scoreGoal={null} currentScore={null} />
    );

    expect(screen.getByText('Not set')).toBeInTheDocument();
  });
});
