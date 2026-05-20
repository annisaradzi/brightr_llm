"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError } from "@/api/client";
import {
  analyzeSession,
  createSession,
  getSession,
  itemImageSrc,
  patchItem,
  submitSession,
  uploadSessionImages,
} from "@/api/sessions";
import type {
  InspectionItem,
  InspectionItemPatch,
  InspectionSession,
  Priority,
  RecommendationCode,
  RustGrade,
} from "@/types/inspection";

const RUST_GRADES: RustGrade[] = ["Ri1", "Ri2", "R3", "R4", "R5"];
const REC_CODES: RecommendationCode[] = ["TBR", "TBRy", "TBP", "TBM", "TBS"];
const PRIORITIES: Priority[] = ["low", "medium", "high"];
const EQUIP_TYPES = ["piping", "pressure_vessel", "flange", "structural", "other"] as const;

function inspectionLabel(sessionId: string | null) {
  if (!sessionId) return "—";
  const short = sessionId.replace(/-/g, "").slice(0, 8).toUpperCase();
  return `INSPECTION #BR-${short}`;
}

function aiDotClass(item: InspectionItem) {
  return item.editedFields.length ? "bg-amber-600" : "bg-green-700";
}

export function BrightrDashboardTemplate() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("finding");
  const fileRef = useRef<HTMLInputElement>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [session, setSession] = useState<InspectionSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");

  const items = session?.items ?? [];
  const activeItem = useMemo(
    () => items.find((i) => i.id === selectedId) ?? items[0] ?? null,
    [items, selectedId]
  );
  const readOnly = session?.status === "submitted";

  const selectItem = useCallback(
    (id: string) => {
      const p = new URLSearchParams(searchParams.toString());
      p.set("finding", id);
      router.replace(`/?${p.toString()}`);
    },
    [router, searchParams]
  );

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await createSession();
      setSession(s);
      if (s.items[0]) selectItem(s.items[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }, [selectItem]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (items.length && !selectedId) {
      selectItem(items[0].id);
    }
  }, [items, selectedId, selectItem]);

  const onUpload = useCallback(
    async (files: FileList | null) => {
      if (!session || !files?.length) return;
      setUploading(true);
      setError(null);
      try {
        await uploadSessionImages(session.id, Array.from(files));
        const refreshed = await getSession(session.id);
        setSession(refreshed);
        if (refreshed.items[0]) selectItem(refreshed.items[0].id);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [session, selectItem]
  );

  const runAnalyze = useCallback(async () => {
    if (!session) return;
    setAnalyzing(true);
    setError(null);
    try {
      const updated = await analyzeSession(session.id, true);
      setSession(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }, [session]);

  const scheduleSave = useCallback(
    (itemId: string, patch: InspectionItemPatch) => {
      if (!session || readOnly) return;
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(async () => {
        setSaveState("saving");
        try {
          const updated = await patchItem(session.id, itemId, patch);
          setSession((prev) =>
            prev
              ? {
                  ...prev,
                  items: prev.items.map((i) => (i.id === updated.id ? updated : i)),
                }
              : prev
          );
          setSaveState("saved");
        } catch (e) {
          setSaveState("idle");
          setError(e instanceof ApiError ? e.message : "Save failed");
        }
      }, 800);
    },
    [session, readOnly]
  );

  const updateCell = useCallback(
    (item: InspectionItem, field: keyof InspectionItemPatch, value: unknown) => {
      setSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((r) => (r.id === item.id ? { ...r, [field]: value } : r)),
        };
      });
      scheduleSave(item.id, { [field]: value } as InspectionItemPatch);
    },
    [scheduleSave]
  );

  const refreshDraft = useCallback(async () => {
    if (!session) return;
    const refreshed = await getSession(session.id);
    setSession(refreshed);
  }, [session]);

  const onSubmit = useCallback(async () => {
    if (!session) return;
    setError(null);
    try {
      const updated = await submitSession(session.id);
      setSession(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Submit failed");
    }
  }, [session]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-stone-500">
        Starting inspection session…
      </div>
    );
  }

  if (session?.status === "submitted") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f5f4] px-6">
        <div className="w-full max-w-[520px] rounded-xl border border-[#e7e5e4] bg-white p-8 shadow-sm">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-50 text-2xl text-green-700">
            ✓
          </div>
          <h1 className="mb-2 text-xl font-semibold">Your report is ready</h1>
          <p className="mb-5 text-sm leading-6 text-[#78716c]">
            The executive inspection report has been submitted. You can download the PDF now or open the full report to review all findings.
          </p>
          <div className="mb-5 rounded-lg bg-[#f5f5f4] p-3 text-xs text-[#78716c]">
            <p><strong className="text-[#1c1917]">System report #</strong> {session.systemReportNumber || "-"}</p>
            <p className="mt-1"><strong className="text-[#1c1917]">User report #</strong> {session.userReportNumber || "-"}</p>
            <p className="mt-1"><strong className="text-[#1c1917]">Submitted</strong> {session.submittedAt ? new Date(session.submittedAt).toLocaleString() : "-"}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {session.pdfUrl && (
              <a href={session.pdfUrl} className="rounded-md border border-[#d85a30] bg-[#d85a30] px-4 py-2 text-sm font-medium text-white">
                Download PDF
              </a>
            )}
            <Link href={`/reports/${session.id}`} target="_blank" className="rounded-md border border-[#e7e5e4] bg-white px-4 py-2 text-sm">
              View full report
            </Link>
          </div>
          <button type="button" onClick={bootstrap} className="mt-5 text-sm font-medium text-[#d85a30]">
            Start new analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5f5f4]">
      <div className="mx-auto max-w-[1400px] p-6">
        <header className="mb-5 flex items-center justify-between border-b border-[#e7e5e4] pb-4">
          <div className="text-base font-medium">
            brightr<span className="text-[#d85a30]">.AI</span>
          </div>
          <nav className="flex items-center gap-2 text-[13px] text-[#78716c]">
            <span>New Analysis</span>
            <Link href="/reports">Reports</Link>
            <span className="rounded-full bg-[#faece7] px-2.5 py-1 text-[11px] font-medium text-[#712b13]">
              Draft
            </span>
          </nav>
        </header>

        <p className="mb-2 text-xs tracking-wide text-[#78716c]">{inspectionLabel(session?.id ?? null)}</p>
        <h1 className="mb-4 text-[22px] font-medium">Visual inspection — new analysis</h1>

        <div className="mb-4 flex flex-wrap gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            className="hidden"
            onChange={(e) => {
              onUpload(e.target.files);
              e.target.value = "";
            }}
          />
          <button type="button" className="rounded-md border border-[#e7e5e4] bg-white px-3.5 py-2 text-[13px]" onClick={() => fileRef.current?.click()} disabled={uploading || readOnly}>
            {uploading ? "Uploading…" : "Upload images"}
          </button>
          <button type="button" className="rounded-md border border-[#d85a30] bg-[#d85a30] px-3.5 py-2 text-[13px] text-white" onClick={runAnalyze} disabled={analyzing || !items.length || readOnly}>
            {analyzing ? "Analyzing…" : "Run AI analysis"}
          </button>
          <button type="button" className="rounded-md border border-[#e7e5e4] bg-white px-3.5 py-2 text-[13px]" onClick={refreshDraft}>
            Save draft
          </button>
          <button type="button" className="rounded-md border border-[#e7e5e4] bg-white px-3.5 py-2 text-[13px]" onClick={onSubmit} disabled={!items.length || readOnly}>
            Submit inspection
          </button>
          <span className="ml-auto self-center text-xs text-[#78716c]">
            {saveState === "saving" ? "Saving…" : saveState === "saved" ? "Saved" : ""}
          </span>
        </div>

        <button
          type="button"
          className="mb-4 block w-full rounded-xl border-2 border-dashed border-[#e7e5e4] bg-white px-8 py-8 text-center text-sm text-[#78716c]"
          onClick={() => fileRef.current?.click()}
        >
          Drop images here or click to browse (PNG, JPG, WEBP) — multiple files allowed
        </button>

        {error && <div className="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}

        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <section className="rounded-xl border border-[#e7e5e4] bg-white p-3">
            <p className="mb-2 text-[13px] font-medium">Image preview ({activeItem?.code || "row"})</p>
            <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-[#fafaf9]">
              {activeItem ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={itemImageSrc(activeItem)} alt="Preview" className="h-full w-full object-contain" />
                  {activeItem.aiBoundingBoxes.map((d, i) => (
                    <div key={i}>
                      <div
                        className="absolute border-2 border-dashed border-[#e24b4a]"
                        style={{
                          left: `${d.x * 100}%`,
                          top: `${d.y * 100}%`,
                          width: `${d.w * 100}%`,
                          height: `${d.h * 100}%`,
                        }}
                      />
                    </div>
                  ))}
                </>
              ) : null}
            </div>
            <p className="mt-2 text-[11px] text-[#78716c]">
              Select a table row to change preview. Bounding boxes shown after analysis.
            </p>
          </section>

          <section className="overflow-x-auto rounded-xl border border-[#e7e5e4] bg-white">
            <table className="min-w-[1200px] w-full border-collapse text-xs">
              <thead>
                <tr>
                  {[
                    "Image ID",
                    "Image",
                    "Findings",
                    "Rust grade",
                    "CoF",
                    "Findings priority",
                    "Equipment type",
                    "Equipment ID",
                    "Rec. code",
                    "Recommendation",
                    "Further insp.",
                    "Open insul.",
                    "Scaffold",
                    "SAP priority",
                  ].map((h) => (
                    <th key={h} className="sticky top-0 z-10 whitespace-nowrap border-b border-[#e7e5e4] bg-[#fafaf9] px-2 py-2 text-left font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const active = activeItem?.id === item.id;
                  return (
                    <tr key={item.id} className={`${active ? "bg-[#faece7]" : ""} hover:bg-[#fafaf9]`} onClick={() => selectItem(item.id)}>
                      <td className="border-b border-[#e7e5e4] px-2 py-2 whitespace-nowrap">
                        {item.code}
                        <span className={`ml-1 inline-block h-1.5 w-1.5 rounded-full align-middle ${aiDotClass(item)}`} />
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img className="h-[42px] w-[56px] rounded bg-[#e7e5e4] object-cover" src={itemImageSrc(item)} alt="" />
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <textarea rows={3} className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.findings || ""} onChange={(e) => updateCell(item, "findings", e.target.value)} onClick={(e) => e.stopPropagation()} disabled={readOnly} />
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <select className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.rustGrade || ""} onChange={(e) => updateCell(item, "rustGrade", e.target.value as RustGrade)} onClick={(e) => e.stopPropagation()} disabled={readOnly}>
                          <option value=""></option>
                          {RUST_GRADES.map((v) => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <input type="number" min={1} max={5} className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.cof ?? ""} onChange={(e) => updateCell(item, "cof", e.target.value ? Number(e.target.value) : null)} onClick={(e) => e.stopPropagation()} disabled={readOnly} />
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <select className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.findingsPriority || ""} onChange={(e) => updateCell(item, "findingsPriority", e.target.value as Priority)} onClick={(e) => e.stopPropagation()} disabled={readOnly}>
                          <option value=""></option>
                          {PRIORITIES.map((v) => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <select className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.equipmentType || ""} onChange={(e) => updateCell(item, "equipmentType", e.target.value)} onClick={(e) => e.stopPropagation()} disabled={readOnly}>
                          <option value=""></option>
                          {EQUIP_TYPES.map((v) => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <input type="text" className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.equipmentId || ""} onChange={(e) => updateCell(item, "equipmentId", e.target.value)} onClick={(e) => e.stopPropagation()} disabled={readOnly} />
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <select className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.recommendationCode || ""} onChange={(e) => updateCell(item, "recommendationCode", e.target.value as RecommendationCode)} onClick={(e) => e.stopPropagation()} disabled={readOnly}>
                          <option value=""></option>
                          {REC_CODES.map((v) => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </td>
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <textarea rows={3} className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.recommendation || ""} onChange={(e) => updateCell(item, "recommendation", e.target.value)} onClick={(e) => e.stopPropagation()} disabled={readOnly} />
                      </td>
                      {(["furtherInspection", "openInsulation", "scaffold"] as const).map((k) => (
                        <td key={k} className="border-b border-[#e7e5e4] px-2 py-2 whitespace-nowrap">
                          <label className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <input type="checkbox" checked={Boolean(item[k])} onChange={(e) => updateCell(item, k, e.target.checked)} disabled={readOnly} />
                            Yes
                          </label>
                        </td>
                      ))}
                      <td className="border-b border-[#e7e5e4] px-2 py-2">
                        <select className="w-full rounded border border-[#e7e5e4] px-1.5 py-1" value={item.sapPriority || ""} onChange={(e) => updateCell(item, "sapPriority", e.target.value as Priority)} onClick={(e) => e.stopPropagation()} disabled={readOnly}>
                          <option value=""></option>
                          {PRIORITIES.map((v) => <option key={v} value={v}>{v}</option>)}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="flex flex-wrap gap-4 p-3 text-[11px] text-[#78716c]">
              <span className="flex items-center gap-1"><span className="inline-block h-1.5 w-1.5 rounded-full bg-green-700" /> AI pre-filled</span>
              <span className="flex items-center gap-1"><span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-600" /> Engineer edited</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
