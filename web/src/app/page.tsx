import { Suspense } from "react";
import { BrightrDashboard } from "@/components/BrightrDashboard";

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-stone-500">
          Loading…
        </div>
      }
    >
      <BrightrDashboard />
    </Suspense>
  );
}
