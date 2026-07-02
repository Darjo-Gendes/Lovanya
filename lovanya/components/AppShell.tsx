"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useHydrated, useLovanya } from "@/lib/store";
import BottomNav from "@/components/BottomNav";
import AuraOrb from "@/components/AuraOrb";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const hydrated = useHydrated();
  const profile = useLovanya((s) => s.profile);
  const seeded = useLovanya((s) => s.seeded);
  const seedCloset = useLovanya((s) => s.seedCloset);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && !seeded) seedCloset();
  }, [hydrated, seeded, seedCloset]);

  useEffect(() => {
    if (!hydrated) return;
    if (!profile.onboarded && pathname !== "/onboarding") {
      router.replace("/onboarding");
    }
  }, [hydrated, profile.onboarded, pathname, router]);

  if (!hydrated) {
    return (
      <div className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col items-center justify-center gap-6">
        <AuraOrb size={64} />
        <div className="text-center">
          <p className="font-script text-5xl leading-none text-rosewood">Lovanya</p>
          <p className="mt-2 text-sm text-ink-soft">your best friend in fashion</p>
        </div>
      </div>
    );
  }

  const showNav = profile.onboarded && pathname !== "/onboarding";

  return (
    <div className="relative mx-auto min-h-dvh w-full max-w-[430px]">
      <main className={`px-5 pt-6 ${showNav ? "pb-36" : "pb-10"}`}>
        {children}
      </main>
      {showNav && <BottomNav />}
    </div>
  );
}
