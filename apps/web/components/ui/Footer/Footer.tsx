import Link from 'next/link';

import Image from 'next/image';
import mcataiLogo from '@/components/icons/mcatai-logo.svg';

export default function Footer() {
  return (
    <footer className="mx-auto max-w-[1920px] px-6 bg-zinc-900">
      <div className="grid grid-cols-1 gap-8 py-12 text-white transition-colors duration-150 border-b lg:grid-cols-12 border-zinc-600 bg-zinc-900">
        {/* Brand Info */}
        <div className="col-span-1 lg:col-span-6">
          <div className="flex items-center gap-3 mb-4">
            <Image
              src={mcataiLogo}
              alt="MCATai Logo"
              width={24}
              height={24}
            />
            <span className="font-bold text-white tracking-wide">
              MCATai
            </span>
          </div>
          <p className="text-sm text-zinc-500 max-w-sm">
            AI-powered learning and practice tools designed for MCAT preparation.
          </p>
        </div>
        {/* Quick Links */}
        <div className="col-span-1 lg:col-span-3">
          <p className="font-semibold text-white mb-3">Navigation</p>
          <ul className="space-y-2 text-sm">
            <li>
              <Link href="/dashboard" className="hover:text-white transition">
                Home
              </Link>
            </li>
            <li>
              <Link href="/account" className="hover:text-white transition">
                Account
              </Link>
            </li>
          </ul>
        </div>

        {/* Legal Links */}
        <div className="col-span-1 lg:col-span-3">
          <p className="font-semibold text-white mb-3">Legal</p>
          <ul className="space-y-2 text-sm">
            <li>
              <Link href="/privacy" className="hover:text-white transition">
                Privacy Policy
              </Link>
            </li>
            <li>
              <Link href="/terms" className="hover:text-white transition">
                Terms of Service
              </Link>
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom Copyright Notice */}
      <div className="flex flex-col items-center justify-between py-6 md:flex-row text-xs text-zinc-600">
        <div>
          &copy; {new Date().getFullYear()} MCATai. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
