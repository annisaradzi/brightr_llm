"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msInfo, setMsInfo] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password, remember }),
      });
      const data = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) {
        setError(data.error || "Sign in failed");
        return;
      }
      router.replace("/");
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="min-h-screen px-4 py-10"
      style={{ background: "var(--color-background-secondary, #F5F4F0)" }}
    >
      <div className="mx-auto w-full max-w-[1100px]">
        <p
          className="mb-3 text-center text-[11px] font-medium uppercase tracking-[0.12em] md:text-left"
          style={{ color: "var(--color-text-tertiary, #a8a29e)" }}
        >
          Sign in
        </p>
        <div className="grid min-h-[min(100vh-8rem,580px)] grid-cols-1 overflow-hidden rounded-[12px] border border-black/[0.08] bg-white shadow-sm md:grid-cols-2">
          <div className="relative flex min-h-[220px] flex-col justify-between overflow-hidden bg-[#1A1A1A] px-8 py-9 text-white max-md:min-h-[200px] md:min-h-[580px]">
            <svg
              className="pointer-events-none absolute right-0 top-0 h-[320px] w-[320px] max-md:opacity-[0.04] md:opacity-[0.08]"
              viewBox="0 0 320 320"
              aria-hidden
            >
              <circle cx="250" cy="70" r="55" fill="#D85A30" />
              <circle cx="200" cy="100" r="32" fill="#D85A30" />
              <circle cx="275" cy="140" r="22" fill="#D85A30" />
            </svg>

            <div className="relative z-[1] flex items-center gap-2.5 text-[17px] font-medium tracking-[-0.3px]">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden
              >
                <circle cx="12" cy="12" r="10" stroke="#D85A30" strokeWidth="1.5" />
                <circle cx="12" cy="12" r="5" fill="#D85A30" />
                <circle cx="12" cy="12" r="2" fill="#FAECE7" />
              </svg>
              <span>
                brightr<span className="text-[#D85A30]">.AI</span>
              </span>
            </div>

            <div className="relative z-[1] my-6 md:my-0">
              <p
                className="mb-3 text-[11px] font-medium uppercase"
                style={{ color: "#D85A30", letterSpacing: "0.1em" }}
              >
                CORROSION INTELLIGENCE
              </p>
              <h2 className="mb-3.5 text-2xl font-medium leading-tight">
                See failures before they happen.
              </h2>
              <p className="text-[13px] leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>
                AI-powered corrosion assessment for oil & gas infrastructure. Aligned with ISO 21457,
                ISO 15156, and NACE standards.
              </p>
            </div>

            <div
              className="relative z-[1] flex flex-wrap gap-6 border-t border-white/10 pt-5 md:gap-8"
            >
              {[
                { val: "ISO", sub: "COMPLIANT" },
                { val: "SOC 2", sub: "CERTIFIED" },
                { val: "256-bit", sub: "ENCRYPTED" },
              ].map((b) => (
                <div key={b.sub} className="badge text-left">
                  <div className="text-lg font-medium">{b.val}</div>
                  <div
                    className="text-[10px] tracking-wide"
                    style={{ color: "rgba(255,255,255,0.5)" }}
                  >
                    {b.sub}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Form column */}
          <div className="flex flex-col justify-center px-8 py-10 md:px-12">
            <h1 className="text-[22px] font-medium">Welcome back</h1>
            <p
              className="mb-7 mt-1.5 text-[13px]"
              style={{ color: "var(--color-text-secondary, #5F5E5A)" }}
            >
              Sign in to continue your inspection work
            </p>

            <div className="mb-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={() =>
                  setMsInfo("Demo: use your work email and password below. Microsoft SSO is not connected in this environment.")
                }
                className="flex items-center justify-center gap-2.5 rounded-lg border border-black/[0.15] bg-white py-2.5 text-[13px] font-medium transition hover:bg-stone-100"
                style={{ color: "#1A1A1A" }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>
                  <path
                    d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z"
                    fill="#737373"
                  />
                </svg>
                Continue with Microsoft SSO
              </button>
            </div>
            {msInfo && (
              <p className="mb-4 text-center text-xs text-amber-800/90" role="status">
                {msInfo}
              </p>
            )}

            <div className="mb-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-black/10" />
              <span
                className="text-[11px] tracking-wide"
                style={{ color: "var(--color-text-tertiary, #888780)" }}
              >
                OR SIGN IN WITH EMAIL
              </span>
              <div className="h-px flex-1 bg-black/10" />
            </div>

            <form onSubmit={onSubmit}>
              {error && (
                <div
                  className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <div className="mb-3.5">
                <label
                  htmlFor="work-email"
                  className="mb-1.5 block text-[12px] font-medium"
                  style={{ color: "var(--color-text-secondary, #5F5E5A)" }}
                >
                  Work email
                </label>
                <input
                  id="work-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="engineer@company.com"
                  className="w-full rounded-lg border border-black/[0.15] bg-white px-3 py-2.5 text-[13px] outline-none transition focus:border-[#D85A30] focus:ring-2 focus:ring-[#D85A30]/20"
                />
              </div>

              <div className="mb-1.5">
                <div className="mb-1.5 flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="text-[12px] font-medium"
                    style={{ color: "var(--color-text-secondary, #5F5E5A)" }}
                  >
                    Password
                  </label>
                  <span
                    className="cursor-not-allowed text-[11px] text-[#D85A30] opacity-80"
                    title="Not available in demo"
                  >
                    Forgot password?
                  </span>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full rounded-lg border border-black/[0.15] bg-white px-3 py-2.5 text-[13px] outline-none transition focus:border-[#D85A30] focus:ring-2 focus:ring-[#D85A30]/20"
                />
              </div>

              <label className="mb-4 flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-stone-300 text-[#D85A30] focus:ring-[#D85A30]"
                />
                <span className="text-[12px]" style={{ color: "var(--color-text-secondary)" }}>
                  Keep me signed in on this device
                </span>
              </label>

              <button
                type="submit"
                disabled={loading}
                className="mb-4 w-full rounded-lg bg-[#D85A30] py-3 text-[13px] font-medium text-white transition hover:bg-[#712B13] disabled:opacity-60"
              >
                {loading ? "Signing in..." : "Sign in to brightr.AI ->"}
              </button>
            </form>

            <p
              className="text-center text-[12px]"
              style={{ color: "var(--color-text-secondary, #5F5E5A)" }}
            >
              New to brightr.AI?{" "}
              <span
                className="cursor-not-allowed font-medium text-inherit"
                title="Request access is not available in the demo"
              >
                Request access
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
