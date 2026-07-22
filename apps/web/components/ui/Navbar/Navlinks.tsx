'use client';

import Link from 'next/link';
import { SignOut } from '@/utils/auth-helpers/server';
import { handleRequest } from '@/utils/auth-helpers/client';
import Logo from '@/components/icons/Logo';
import { usePathname, useRouter } from 'next/navigation';
import { getRedirectMethod } from '@/utils/auth-helpers/settings';
import s from './Navbar.module.css';
import Image from 'next/image';

// Import SVG directly as a component asset from components/icons/
import mcataiLogo from '@/components/icons/mcatai-logo.svg';

interface NavlinksProps {
  user?: any;
}

export default function Navlinks({ user }: NavlinksProps) {
  const router = getRedirectMethod() === 'client' ? useRouter() : null;
  
  return (
    <div className="flex justify-between align-center border-b border-zinc-800 py-4">
      <div className="flex items-center flex-1">
        <div className="inline-flex items-center gap-2">
          <Image
            src={mcataiLogo}
            alt="MCATai Logo"
            width={32}
            height={32}
            priority
            className="shrink-0"
          />
          <span className="text-sm font-medium text-white tracking-wide whitespace-nowrap">
            MCATai
          </span>
        </div>
        <nav className="ml-6 space-x-2 lg:block">
          {/* Updated to link to /dashboard */}
          <Link href="/dashboard" className={s.link}>
            Pricing
          </Link>
          {user && (
            <Link href="/account" className={s.link}>
              Account
            </Link>
          )}
        </nav>
      </div>
      <div className="flex justify-end space-x-8">
        {user ? (
          <form onSubmit={(e) => handleRequest(e, SignOut, router)}>
            <input type="hidden" name="pathName" value={usePathname()} />
            <button type="submit" className={s.link}>
              Sign out
            </button>
          </form>
        ) : (
          <Link href="/signin" className={s.link}>
            Sign In
          </Link>
        )}
      </div>
    </div>
  );
}