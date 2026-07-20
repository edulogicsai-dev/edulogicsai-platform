import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DashboardShell from './DashboardShell';

const sidebarProps = {
  displayName: 'Jordan',
  testDate: null,
  scoreGoal: null,
  currentScore: null
};

describe('DashboardShell', () => {
  it('AC3: sidebar is collapsed behind a toggle by default and reachable via the toggle button', () => {
    render(
      <DashboardShell sidebar={sidebarProps}>
        <div>chat</div>
      </DashboardShell>
    );

    const sidebar = document.getElementById('dashboard-sidebar');
    // Collapsed by default (mobile-first class), not removed from the DOM.
    expect(sidebar).toHaveClass('hidden');

    fireEvent.click(screen.getByRole('button', { name: /menu/i }));

    expect(sidebar).not.toHaveClass('hidden');
    expect(screen.getByText('chat')).toBeInTheDocument();
  });
});
