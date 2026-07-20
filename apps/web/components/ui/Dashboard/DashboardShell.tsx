'use client';

import { PropsWithChildren, useState } from 'react';
import Sidebar, { SidebarProps } from './Sidebar';

interface DashboardShellProps extends PropsWithChildren {
  sidebar: SidebarProps;
}

// FR5: below md, the sidebar collapses behind a toggle rather than being
// permanently hidden -- still reachable, chat takes full width.
export default function DashboardShell({ sidebar, children }: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex flex-col md:flex-row min-h-[calc(100dvh-4rem)]">
      <button
        type="button"
        onClick={() => setSidebarOpen((open) => !open)}
        aria-expanded={sidebarOpen}
        aria-controls="dashboard-sidebar"
        className="md:hidden px-4 py-2 text-left text-zinc-200 border-b border-zinc-800"
      >
        {sidebarOpen ? '✕ Close menu' : '☰ Menu'}
      </button>

      <div id="dashboard-sidebar" className={sidebarOpen ? 'block' : 'hidden md:block'}>
        <Sidebar {...sidebar} />
      </div>

      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
