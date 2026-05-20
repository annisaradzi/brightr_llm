import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  active: "inspections" | "reports";
  children: ReactNode;
};

export function ReportsShell({ active, children }: Props) {
  return (
    <div className="v2-body">
      <header className="v2-topbar">
        <Link href="/" className="v2-brand">
          <span className="v2-brand-mark">b</span>
          <span>
            brightr<span className="dot">.AI</span>
          </span>
        </Link>
        <nav className="v2-nav">
          <Link href="/" className={active === "inspections" ? "active" : undefined}>
            Inspections
          </Link>
          <Link href="/reports" className={active === "reports" ? "active" : undefined}>
            Reports
          </Link>
        </nav>
      </header>
      {children}
    </div>
  );
}
