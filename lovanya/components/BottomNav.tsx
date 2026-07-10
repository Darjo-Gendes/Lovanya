"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shirt } from "lucide-react";
import { Add, BookSaved, Home, User } from "iconsax-react";

export default function BottomNav() {
  const pathname = usePathname();

  const tab = (
    href: string,
    label: string,
    renderIcon: (active: boolean) => ReactNode
  ) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`flex w-[54px] flex-col items-center gap-1.5 transition-colors ${
          active ? "text-rosewood" : "text-ink-faint"
        }`}
      >
        {renderIcon(active)}
        <span className={`text-[11px] ${active ? "font-semibold" : "font-medium"}`}>
          {label}
        </span>
      </Link>
    );
  };

  const analyzeActive = pathname === "/check";

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 mx-auto w-full max-w-[430px]">
      <div className="relative h-[84px] rounded-t-[28px] bg-card shadow-[0_-8px_26px_-14px_rgba(206,150,150,0.45)]">
        <div className="absolute inset-x-0 top-3.5 flex items-start justify-around px-3.5">
          {tab("/", "Home", (a) => (
            <Home size={23} variant={a ? "Bold" : "Linear"} />
          ))}
          {/* Wardrobe stays on lucide Shirt — Iconsax 0.0.8 has no apparel glyph.
              Active state uses a stroke-weight bump instead of Bold/Linear. */}
          {tab("/closet", "Wardrobe", (a) => (
            <Shirt size={23} strokeWidth={a ? 2.2 : 1.8} />
          ))}

          <Link
            href="/check"
            aria-label="Style Me — check an outfit"
            className="flex w-[54px] flex-col items-center"
          >
            <span
              className={`-mt-[30px] flex h-[54px] w-[54px] items-center justify-center rounded-full border-[5px] border-card text-white shadow-lift transition-transform active:scale-95 ${
                analyzeActive ? "ring-2 ring-blush-deep" : ""
              }`}
              style={{ background: "linear-gradient(135deg,#e48ea0,#ce6c84)" }}
            >
              <Add size={24} />
            </span>
            <span
              className={`mt-1.5 text-[11px] font-medium ${
                analyzeActive ? "text-rosewood" : "text-ink-faint"
              }`}
            >
              Style Me
            </span>
          </Link>

          {tab("/journal", "Journal", (a) => (
            <BookSaved size={23} variant={a ? "Bold" : "Linear"} />
          ))}
          {tab("/profile", "Profile", (a) => (
            <User size={23} variant={a ? "Bold" : "Linear"} />
          ))}
        </div>
      </div>
    </nav>
  );
}
