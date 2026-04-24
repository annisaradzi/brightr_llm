"use client";

import { useCallback, useMemo, useState } from "react";

type Detection = {
  label: string;
  confidence?: number;
  box: { x: number; y: number; width: number; height: number };
};

type AnalyzeResult = {
  summary: string;
  findings: string[];
  recommendations: string[];
  detections: Detection[];
  reportId: string;
  pdfBase64: string;
  pdfFileName: string;
  geminiModel: string;
  imageWidth: number;
  imageHeight: number;
};

const TIER_LABELS = [
  { k: "IMMEDIATE (0-24H)", className: "text-[#791F1F]" },
  { k: "SHORT TERM (1-2 WK)", className: "text-[#633806]" },
  { k: "LONG TERM (3-6 MO)", className: "text-[#0C447C]" },
] as const;

const TIER_BGS = [
  "bg-[#FCEBEB]",
  "bg-[#FAEEDA]",
  "bg-[#E6F1FB]",
] as const;

const TIER_NUM = [
  { bg: "bg-[#A32D2D]", text: "text-white" },
  { bg: "bg-[#854F0B]", text: "text-white" },
  { bg: "bg-[#185FA5]", text: "text-white" },
] as const;

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function inspectionLabel(reportId: string | null) {
  if (!reportId) return "\u2014";
  const short = reportId.replace(/-/g, "").slice(0, 8).toUpperCase();
  return `INSPECTION #BR-${short}`;
}

function aggregateConfidence(detections: Detection[]): string {
  const cs = detections
    .map((d) => d.confidence)
    .filter((c): c is number => typeof c === "number" && !Number.isNaN(c));
  if (cs.length === 0) return "\u2014";
  const avg = cs.reduce((a, b) => a + b, 0) / cs.length;
  return `High \u00b7 ${Math.round(avg * 100)}%`;
}

export function BrightrDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResult | null>(null);

  const onPick = useCallback(
    (f: File | null) => {
      setError(null);
      setData(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      if (!f) {
        setFile(null);
        setPreviewUrl(null);
        return;
      }
      setFile(f);
      setPreviewUrl(URL.createObjectURL(f));
    },
    [previewUrl]
  );

  const onLogout = useCallback(async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      window.location.href = "/login";
    }
  }, []);

  const analyze = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const fd = new FormData();
      fd.append("image", file);
      if (severity.trim()) fd.append("severity", severity.trim());
      const res = await fetch("/api/analyze", { method: "POST", body: fd });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      const j = (await res.json().catch(() => ({}))) as
        | AnalyzeResult
        | { detail?: string | Array<{ msg?: string }> };
      if (!res.ok) {
        const d = "detail" in j ? j.detail : undefined;
        const msg =
          typeof d === "string"
            ? d
            : Array.isArray(d) && d[0]?.msg
              ? d[0].msg
              : "Request failed";
        throw new Error(msg || "Request failed");
      }
      setData(j as AnalyzeResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, [file, severity]);

  const onDownload = useCallback(() => {
    if (!data?.pdfBase64 || !data.pdfFileName) return;
    const bin = atob(data.pdfBase64);
    const u8 = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    const blob = new Blob([u8], { type: "application/pdf" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = data.pdfFileName;
    a.click();
    URL.revokeObjectURL(a.href);
  }, [data]);

  const resolutionText = useMemo(() => {
    if (data) return `${data.imageWidth} \u00d7 ${data.imageHeight}`;
    return "\u2014";
  }, [data]);

  const findingChips = data?.findings?.slice(0, 4) ?? [];

  return (
    <div
      className="min-h-screen p-4 md:p-6"
      style={{ background: "var(--color-background-secondary)" }}
    >
      <div
        className="mx-auto max-w-6xl rounded-[var(--border-radius-lg)] p-6"
        style={{
          background: "var(--color-background-secondary)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        }}
      >
        <div
          className="mb-5 flex flex-wrap items-center justify-between gap-4 border-b pb-5"
          style={{ borderColor: "var(--color-border-tertiary)" }}
        >
          <div className="flex items-center gap-2.5">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden
            >
              <circle cx="12" cy="12" r="10" stroke="#D85A30" strokeWidth="1.5" />
              <circle cx="12" cy="12" r="5" fill="#D85A30" />
              <circle cx="12" cy="12" r="2" fill="#FAECE7" />
            </svg>
            <span
              className="text-base font-medium tracking-tight"
              style={{ letterSpacing: "-0.3px" }}
            >
              brightr<span className="text-[#D85A30]">.AI</span>
            </span>
          </div>
          <nav
            className="flex flex-wrap items-center gap-4 text-[13px]"
            style={{ color: "var(--color-text-secondary)" }}
          >
            <a href="#" className="hover:opacity-80">
              Dashboard
            </a>
            <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>
              New Analysis
            </span>
            <a href="#" className="hover:opacity-80">
              Reports
            </a>
            <a href="#" className="hover:opacity-80">
              Standards
            </a>
            <button
              type="button"
              onClick={onLogout}
              className="text-[13px] hover:opacity-80"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Sign out
            </button>
            <div
              className="flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-medium"
              style={{
                background: "var(--color-background-info)",
                color: "var(--color-text-info)",
              }}
            >
              AZ
            </div>
          </nav>
        </div>

        <div className="px-1 pb-4">
          <p
            className="mb-1 text-xs tracking-wide"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {inspectionLabel(data?.reportId ?? null)}
          </p>
          <h1 className="text-[22px] font-medium">Pipeline segment analysis</h1>
          <p className="mt-1.5 text-[13px]" style={{ color: "var(--color-text-secondary)" }}>
            {data
              ? "Analysis complete \u2014 see findings and recommendations below"
              : "Upload an image to run corrosion assessment"}
          </p>
        </div>

        {error && (
          <div
            className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="mt-2 grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_1fr]">
          <div
            className="rounded-[var(--border-radius-lg)] border p-4"
            style={{
              background: "var(--color-background-primary)",
              borderColor: "var(--color-border-tertiary)",
            }}
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[13px] font-medium">Uploaded image</span>
              <span className="text-[11px]" style={{ color: "var(--color-text-tertiary)" }}>
                {file ? `${file.name} \u00b7 ${formatBytes(file.size)}` : "No file yet"}
              </span>
            </div>

            <label
              className="mb-3 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed py-8"
              style={{ borderColor: "var(--color-border-tertiary)" }}
            >
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="sr-only"
                onChange={(e) => onPick(e.target.files?.[0] ?? null)}
              />
              <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                {file ? "Replace image" : "Drop a file or click to browse (PNG, JPG, WEBP)"}
              </span>
            </label>

            {previewUrl && file && (
              <div
                className="relative w-full overflow-hidden rounded-[var(--border-radius-md)]"
                style={{ aspectRatio: "4/3" }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrl}
                  alt="Inspection preview"
                  className="h-full w-full object-contain"
                />
                {data?.detections?.map((d, i) => {
                  const b = d.box;
                  const isRed = i % 2 === 0;
                  return (
                    <div
                      key={i}
                      className="absolute"
                      style={{ left: 0, top: 0, width: "100%", height: "100%" }}
                    >
                      <div
                        className="absolute border-2"
                        style={{
                          left: `${b.x * 100}%`,
                          top: `${b.y * 100}%`,
                          width: `${b.width * 100}%`,
                          height: `${b.height * 100}%`,
                          borderColor: isRed ? "#E24B4A" : "#EF9F27",
                          borderStyle: "dashed",
                        }}
                      />
                      <div
                        className="absolute max-w-[90%] truncate px-1.5 py-0.5 text-[10px] font-medium text-white"
                        style={{
                          left: `${b.x * 100}%`,
                          top: `calc(${b.y * 100}% - 18px)`,
                          background: isRed ? "#E24B4A" : "#EF9F27",
                        }}
                      >
                        {d.label}
                        {d.confidence != null
                          ? ` \u00b7 ${Math.round(d.confidence * 100)}%`
                          : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              <div
                className="min-w-0 flex-1 rounded-[var(--border-radius-md)] p-2 text-[11px]"
                style={{ background: "var(--color-background-secondary)" }}
              >
                <div style={{ color: "var(--color-text-secondary)" }}>Resolution</div>
                <div className="mt-0.5 font-medium">{resolutionText}</div>
              </div>
              <div
                className="min-w-0 flex-1 rounded-[var(--border-radius-md)] p-2 text-[11px]"
                style={{ background: "var(--color-background-secondary)" }}
              >
                <div style={{ color: "var(--color-text-secondary)" }}>Confidence</div>
                <div
                  className="mt-0.5 font-medium"
                  style={{ color: "var(--color-text-success)" }}
                >
                  {data ? aggregateConfidence(data.detections) : "\u2014"}
                </div>
              </div>
              <div
                className="min-w-0 flex-1 rounded-[var(--border-radius-md)] p-2 text-[11px]"
                style={{ background: "var(--color-background-secondary)" }}
              >
                <div style={{ color: "var(--color-text-secondary)" }}>Model</div>
                <div className="mt-0.5 truncate font-medium" title={data?.geminiModel}>
                  {data?.geminiModel ? data.geminiModel.replace("gemini-", "") : "\u2014"}
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <div
              className="rounded-[var(--border-radius-lg)] border p-4"
              style={{
                background: "var(--color-background-primary)",
                borderColor: "var(--color-border-tertiary)",
              }}
            >
              <label className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
                Stated severity (optional)
              </label>
              <input
                className="mt-1 w-full rounded-lg border px-3 py-2 text-sm outline-none"
                style={{ borderColor: "var(--color-border-tertiary)" }}
                placeholder="e.g. moderate"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              />
              <button
                type="button"
                disabled={!file || loading}
                onClick={analyze}
                className="mt-3 w-full rounded-lg py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                style={{ background: "#D85A30" }}
              >
                {loading ? "Analyzing\u2026" : "Run analysis"}
              </button>
            </div>

            <div
              className="rounded-[var(--border-radius-lg)] border p-4"
              style={{
                background: "var(--color-background-primary)",
                borderColor: "var(--color-border-tertiary)",
              }}
            >
              <div className="mb-2 flex items-center justify-between">
                <span
                  className="text-xs tracking-wide"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  SEVERITY ASSESSMENT
                </span>
                <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-600">
                  Qualitative
                </span>
              </div>
              <div className="mb-3 flex flex-wrap items-baseline gap-2">
                <span className="text-[28px] font-medium text-stone-500">{"\u2014"}</span>
                <span className="text-[13px]" style={{ color: "var(--color-text-secondary)" }}>
                  {data
                    ? (data.summary || "").slice(0, 80) +
                      (data.summary.length > 80 ? "\u2026" : "")
                    : "Run analysis for summary"}
                </span>
              </div>
              <div className="mb-2 flex h-1.5 gap-0.5">
                {["#97C459", "#C0DD97", "#FAC775", "#EF9F27", "#E24B4A"].map((c) => (
                  <div key={c} className="h-full flex-1 rounded-sm" style={{ background: c }} />
                ))}
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
                {data
                  ? "Readings are based on the model output below. For ISO/NACE codes, follow your internal engineering sign-off."
                  : "\u2014"}
              </p>
            </div>

            <div
              className="rounded-[var(--border-radius-lg)] border p-4"
              style={{
                background: "var(--color-background-primary)",
                borderColor: "var(--color-border-tertiary)",
              }}
            >
              <span
                className="text-xs tracking-wide"
                style={{ color: "var(--color-text-secondary)" }}
              >
                CORROSION TYPE (from findings)
              </span>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {findingChips.length ? (
                  findingChips.map((f, i) => (
                    <span
                      key={i}
                      className="rounded-full px-2.5 py-1 text-xs font-medium"
                      style={{
                        background: i % 2 ? "#FAEEDA" : "#FAECE7",
                        color: i % 2 ? "#633806" : "#712B13",
                      }}
                    >
                      {f.length > 60 ? f.slice(0, 60) + "\u2026" : f}
                    </span>
                  ))
                ) : (
                  <span className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                    {"\u2014"}
                  </span>
                )}
              </div>
            </div>

            <div
              className="rounded-[var(--border-radius-lg)] border p-4"
              style={{
                background: "var(--color-background-primary)",
                borderColor: "var(--color-border-tertiary)",
              }}
            >
              <span
                className="text-xs tracking-wide"
                style={{ color: "var(--color-text-secondary)" }}
              >
                REFERENCED STANDARDS (illustrative)
              </span>
              <div className="mt-2.5 space-y-1 text-xs">
                {(
                  [
                    ["ISO 21457:2010", "Materials selection"],
                    ["ISO 15156", "H2S environments"],
                    ["NACE SP0106", "Internal corrosion"],
                  ] as const
                ).map(([a, b]) => (
                  <div
                    key={a}
                    className="flex justify-between gap-2 border-b py-1.5 last:border-0"
                    style={{ borderColor: "var(--color-border-tertiary)" }}
                  >
                    <span className="font-medium">{a}</span>
                    <span style={{ color: "var(--color-text-secondary)" }}>{b}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {data?.summary && (
          <div
            className="mt-4 rounded-[var(--border-radius-lg)] border p-4"
            style={{
              background: "var(--color-background-primary)",
              borderColor: "var(--color-border-tertiary)",
            }}
          >
            <span
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Executive summary
            </span>
            <p className="mt-2 text-sm leading-relaxed text-stone-800">{data.summary}</p>
          </div>
        )}

        <div
          className="mt-4 rounded-[var(--border-radius-lg)] border p-4"
          style={{
            background: "var(--color-background-primary)",
            borderColor: "var(--color-border-tertiary)",
          }}
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[13px] font-medium">Recommended remediation</span>
            <span className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
              {data
                ? `${Math.min(3, data.recommendations.length || 0)} action(s) \u00b7 ordered by priority`
                : "\u2014"}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
            {[0, 1, 2].map((idx) => {
              const r = data?.recommendations?.[idx];
              return (
                <div
                  key={idx}
                  className={`rounded-[var(--border-radius-md)] p-3 ${TIER_BGS[idx]}`}
                >
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <span
                      className={`inline-flex h-[18px] w-[18px] items-center justify-center rounded-full text-[10px] font-medium ${TIER_NUM[idx].bg} ${TIER_NUM[idx].text}`}
                    >
                      {idx + 1}
                    </span>
                    <span
                      className={`text-[11px] font-medium tracking-wide ${TIER_LABELS[idx].className}`}
                    >
                      {TIER_LABELS[idx].k}
                    </span>
                  </div>
                  {r ? (
                    <p className="text-[13px] font-medium leading-snug text-stone-900">{r}</p>
                  ) : (
                    <p className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                      {"\u2014"}
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          <div
            className="mt-3.5 flex flex-wrap items-center justify-between gap-3 border-t pt-3"
            style={{ borderColor: "var(--color-border-tertiary)" }}
          >
            <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
              Full technical report available as PDF
            </span>
            <div className="flex gap-2">
              <span
                className="cursor-not-allowed rounded-md border px-3 py-1.5 text-xs"
                style={{
                  borderColor: "var(--color-border-secondary)",
                  color: "var(--color-text-secondary)",
                }}
                title="Coming later"
              >
                Share
              </span>
              <button
                type="button"
                disabled={!data?.pdfBase64}
                onClick={onDownload}
                className="rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                style={{ background: "var(--color-text-primary)" }}
              >
                Download report
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
