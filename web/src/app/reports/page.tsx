import { ReportsListPage } from "@/components/reports/ReportsListPage";
import { Suspense } from "react";

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <div className="v2-body flex min-h-screen items-center justify-center text-sm text-stone-500">
          Loading reports…
        </div>
      }
    >
      <ReportsListPage />
    </Suspense>
  );
}
