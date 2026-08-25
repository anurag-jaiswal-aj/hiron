"use client";
import React from "react";
import Link from "next/link";
import Image from "next/image";

export function Navbar(): React.ReactElement {
  return (
    <nav className="sticky top-0 z-50 bg-[#0a0a0a] border-b border-[#262626]">
      <div className="flex items-center justify-between max-w-[1280px] mx-auto px-6 py-[18px]">
        <div className="flex items-center">
          <Link href="/" className="flex items-center">
            <Image
              src="/hiron-logo-white.png"
              alt="Hiron Logo"
              width={152}
              height={38}
              className="h-[42px] w-auto object-contain"
              priority
            />
          </Link>
        </div>

        <div className="flex items-center">
          <Link
            href="/login"
            className="text-[14px] font-medium text-[#a3a3a3] hover:text-[#fafafa] tracking-wide px-3 py-2 rounded transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-[#525252]"
          >
            Log in
          </Link>
        </div>
      </div>
    </nav>
  );
}
