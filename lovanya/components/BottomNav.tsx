"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LineChart, Plus, Shirt, User } from "lucide-react";

export default function BottomNav() {
  const pathname = usePathname();

  const tab = (href: string, label: string, Icon: typeof Home) => {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={`flex w-[54px] flex-col items-center gap-1.5 transition-colors ${
          active ? "text-rosewood" : "text-ink-faint"
        }`}
      >
        <Icon size={23} strokeWidth={active ? 2.2 : 1.8} />
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
          {tab("/", "Home", Home)}
          {tab("/closet", "Wardrobe", Shirt)}

          <Link
            href="/check"
            aria-label="Analyze an outfit"
            className="flex w-[54px] flex-col items-center"
          >
            <span
              className={`-mt-[30px] flex h-[54px] w-[54px] items-center justify-center rounded-full border-[5px] border-card text-white shadow-lift transition-transform active:scale-95 ${
                analyzeActive ? "ring-2 ring-blush-deep" : ""
              }`}
              style={{ background: "linear-gradient(135deg,#e48ea0,#ce6c84)" }}
            >
              <Plus size={24} strokeWidth={2.4} />
            </span>
            <span
              className={`mt-1.5 text-[11px] font-medium ${
                analyzeActive ? "text-rosewood" : "text-ink-faint"
              }`}
            >
              Analyze
            </span>
          </Link>

          {tab("/journey", "Journey", LineChart)}
          {tab("/profile", "Profile", User)}
        </div>
      </div>
    </nav>
  );
}
