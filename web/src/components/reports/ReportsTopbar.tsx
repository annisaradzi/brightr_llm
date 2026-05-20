import Link from "next/link";

type Props = {
  active?: "reports" | "analysis";
};

export function ReportsTopbar({ active = "reports" }: Props) {
  return (
    <header
      className="flex items-center justify-between gap-4 border-b px-5 py-2.5"
      style={{
        background: "var(--v2-surface)",
        borderColor: "var(--v2-border)",
      }}
    >
      <div className="flex items-center gap-2.5 text-[15px] font-semibold tracking-tight">
        <div
          className="grid h-[22px] w-[22px] place-items-center rounded-[5px] text-[11px] font-bold text-white"
          style={{ background: "var(--v2-brand)" }}
        >
          b
        </div>
        <span style={{ color: "var(--v2-text)" }}>
          brightr<span style={{ color: "var(--v2-brand)" }}>.AI</span>
        </span>
      </div>
      <nav className="flex gap-5 text-[13px] font-medium">
        <Link
          href="/"
          className="border-b-2 pb-1.5 transition-colors"
          style={{
            color: active === "analysis" ? "var(--v2-text)" : "var(--v2-text-2)",
            borderColor: active === "analysis" ? "var(--v2-brand)" : "transparent",
          }}
        >
          New Analysis
        </Link>
        <Link
          href="/reports"
          className="border-b-2 pb-1.5 transition-colors"
          style={{
            color: active === "reports" ? "var(--v2-text)" : "var(--v2-text-2)",
            borderColor: active === "reports" ? "var(--v2-brand)" : "transparent",
          }}
        >
          Reports
        </Link>
      </nav>
    </header>
  );
}
