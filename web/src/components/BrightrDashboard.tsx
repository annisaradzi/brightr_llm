"use client";

import {
  analyzeSession,
  createSession,
  deleteItem,
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
  ReviewStatus,
  RustGrade,
} from "@/types/inspection";
import { ApiError } from "@/api/client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

const RUST_GRADES: RustGrade[] = ["Ri1", "Ri2", "R3", "R4", "R5"];
const REC_CODES: RecommendationCode[] = ["TBR", "TBRy", "TBP", "TBM", "TBS"];
const PRIORITIES: Priority[] = ["low", "medium", "high"];
const EQUIP_TYPES = [
  "piping",
  "pressure_vessel",
  "flange",
  "structural",
  "other",
] as const;

function inspectionLabel(sessionId: string | null) {
  if (!sessionId) return "—";
  const short = sessionId.replace(/-/g, "").slice(0, 8).toUpperCase();
  return `INSPECTION #BR-${short}`;
}

function priorityStripe(p: string | null | undefined) {
  if (p === "high") return "#e24b4a";
  if (p === "medium") return "#ef9f27";
  if (p === "low") return "#97c459";
  return "#d6d3d1";
}

export function BrightrDashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("finding");
  const sessionParam = searchParams.get("session");

  const [session, setSession] = useState<InspectionSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const items = session?.items ?? [];
  const activeItem = useMemo(() => {
    if (!items.length) return null;
    if (selectedId) {
      const found = items.find((i) => i.id === selectedId);
      if (found) return found;
    }
    return items[0] ?? null;
  }, [items, selectedId]);
  const readOnly = session?.status === "submitted";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = sessionParam
          ? await getSession(sessionParam)
          : await createSession();
        if (!cancelled) setSession(s);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to start session");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionParam]);

  const selectItem = useCallback(
    (id: string | null) => {
      const p = new URLSearchParams(searchParams.toString());
      if (id) p.set("finding", id);
      else p.delete("finding");
      if (session?.id) p.set("session", session.id);
      router.replace(`/?${p.toString()}`);
    },
    [router, searchParams, session?.id]
  );

  useEffect(() => {
    if (items.length && !selectedId) selectItem(items[0].id);
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
          setError(e instanceof ApiError ? e.message : "Save failed");
          setSaveState("idle");
        }
      }, 800);
    },
    [session, readOnly]
  );

  const updateField = useCallback(
    (field: keyof InspectionItemPatch, value: InspectionItemPatch[keyof InspectionItemPatch]) => {
      if (!activeItem) return;
      setSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((i) =>
            i.id === activeItem.id ? { ...i, [field]: value } : i
          ),
        };
      });
      scheduleSave(activeItem.id, { [field]: value } as InspectionItemPatch);
    },
    [activeItem, scheduleSave]
  );

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

  const canDeleteItem = useCallback((item: InspectionItem) => {
    return (
      !readOnly &&
      (item.analysisStatus === "pending" || item.analysisStatus === "failed")
    );
  }, [readOnly]);

  const onRemoveItem = useCallback(
    async (item: InspectionItem) => {
      if (!session || !canDeleteItem(item)) return;
      if (
        !window.confirm(
          `Remove ${item.code}? This cannot be undone after AI analysis runs.`
        )
      ) {
        return;
      }
      setError(null);
      const removedId = item.id;
      setSession((prev) =>
        prev
          ? { ...prev, items: prev.items.filter((i) => i.id !== removedId) }
          : prev
      );
      try {
        const updated = await deleteItem(session.id, removedId);
        setSession(updated);
        const remaining = updated.items;
        if (remaining.length) {
          const next =
            activeItem?.id === removedId
              ? remaining[0].id
              : remaining.find((i) => i.id === activeItem?.id)?.id ?? remaining[0].id;
          selectItem(next);
        } else {
          selectItem(null);
        }
      } catch (e) {
        try {
          const refreshed = await getSession(session.id);
          setSession(refreshed);
        } catch {
          /* ignore refetch failure */
        }
        setError(e instanceof ApiError ? e.message : "Remove failed");
      }
    },
    [session, canDeleteItem, activeItem?.id, selectItem]
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-stone-500">
        Starting inspection session…
      </div>
    );
  }

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-background-secondary)" }}
    >
      <header
        className="flex flex-wrap items-center justify-between gap-4 border-b px-6 py-4"
        style={{
          borderColor: "var(--color-border-tertiary)",
          background: "var(--color-background-primary)",
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base font-medium">
            brightr<span className="text-[#D85A30]">.AI</span>
          </span>
          <span className="text-[13px] font-medium" style={{ color: "var(--color-text-primary)" }}>
            New Analysis
          </span>
          <Link href="/reports" className="text-[13px] hover:underline" style={{ color: "var(--color-text-secondary)" }}>
            Reports
          </Link>
          <span
            className="rounded-full px-2 py-0.5 text-[11px] font-medium"
            style={{ background: "#FAECE7", color: "#712B13" }}
          >
            {session?.status ?? "draft"}
          </span>
        </div>
        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
          {inspectionLabel(session?.id ?? null)}
        </p>
      </header>

      <div className="flex flex-wrap gap-2 border-b px-6 py-3" style={{ borderColor: "var(--color-border-tertiary)" }}>
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
        <button
          type="button"
          className="rounded-lg border px-3 py-1.5 text-sm"
          disabled={readOnly || uploading}
          onClick={() => fileRef.current?.click()}
        >
          {uploading ? "Uploading…" : "Upload images"}
        </button>
        <button
          type="button"
          className="rounded-lg px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          style={{ background: "#D85A30" }}
          disabled={!items.length || analyzing || readOnly}
          onClick={runAnalyze}
        >
          {analyzing ? "Analyzing…" : "Run AI analysis"}
        </button>
        <button
          type="button"
          className="rounded-lg border px-3 py-1.5 text-sm disabled:opacity-50"
          disabled={!session || readOnly}
          onClick={onSubmit}
        >
          Submit inspection
        </button>
        <span className="ml-auto text-xs" style={{ color: "var(--color-text-secondary)" }}>
          {saveState === "saving" ? "Saving…" : saveState === "saved" ? "Saved" : ""}
        </span>
      </div>

      {error && (
        <div className="mx-6 mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}
      {session?.status === "submitted" && (
        <div className="mx-6 mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <p className="font-medium">Your report is ready.</p>
          <p className="text-xs text-emerald-800">
            {session.systemReportNumber || session.id}
            {session.submittedAt ? ` · Submitted ${new Date(session.submittedAt).toLocaleString()}` : ""}
          </p>
          <div className="mt-2 flex gap-3 text-xs">
            {session.pdfUrl && (
              <a className="underline" href={session.pdfUrl}>
                Download PDF
              </a>
            )}
            <Link className="underline" href={`/reports/${session.id}`}>
              View full report
            </Link>
          </div>
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[240px_1fr_380px]">
        {/* Findings rail */}
        <aside
          className="border-r p-3"
          style={{
            borderColor: "var(--color-border-tertiary)",
            background: "var(--color-background-primary)",
          }}
        >
          <p className="mb-2 text-xs font-medium">
            Findings <strong>({items.length})</strong>
          </p>
          <ul className="space-y-1">
            {items.map((item) => (
              <li key={item.id} className="flex gap-1">
                <button
                  type="button"
                  onClick={() => selectItem(item.id)}
                  className="flex min-w-0 flex-1 gap-2 rounded-lg border p-2 text-left text-xs"
                  style={{
                    borderColor:
                      activeItem?.id === item.id ? "#D85A30" : "var(--color-border-tertiary)",
                    background:
                      activeItem?.id === item.id ? "#FAECE7" : "var(--color-background-secondary)",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={itemImageSrc(item)}
                    alt=""
                    className="h-10 w-14 shrink-0 rounded object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1">
                      <span
                        className="h-2 w-1 shrink-0 rounded-full"
                        style={{ background: priorityStripe(item.findingsPriority) }}
                      />
                      <span className="font-medium">{item.code}</span>
                      {item.editedFields.length > 0 && (
                        <span className="text-[9px] text-amber-600">edited</span>
                      )}
                    </div>
                    <p className="truncate text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                      {(item.findings || "Pending analysis").slice(0, 60)}
                    </p>
                  </div>
                </button>
                {canDeleteItem(item) && (
                  <button
                    type="button"
                    title="Remove image"
                    className="shrink-0 self-center rounded border border-red-200 bg-red-50 px-1.5 py-2 text-[10px] text-red-800 hover:bg-red-100 disabled:opacity-50"
                    disabled={analyzing || uploading}
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveItem(item);
                    }}
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
            {!items.length && (
              <p className="text-xs" style={{ color: "var(--color-text-tertiary)" }}>
                Upload images to begin
              </p>
            )}
          </ul>
        </aside>

        {/* Image viewer */}
        <section className="flex flex-col p-4">
          {activeItem ? (
            <>
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-sm font-medium">{activeItem.code}</p>
                {canDeleteItem(activeItem) && (
                  <button
                    type="button"
                    className="rounded border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-800 hover:bg-red-100 disabled:opacity-50"
                    disabled={analyzing || uploading}
                    onClick={() => onRemoveItem(activeItem)}
                  >
                    Remove image
                  </button>
                )}
              </div>
              <div
                className="relative flex-1 overflow-hidden rounded-lg border"
                style={{
                  borderColor: "var(--color-border-tertiary)",
                  background: "#fafaf9",
                  minHeight: 280,
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={itemImageSrc(activeItem)}
                  alt="Finding"
                  className="h-full w-full object-contain"
                />
                {activeItem.aiBoundingBoxes?.map((d, i) => (
                  <div key={i} className="absolute inset-0">
                    <div
                      className="absolute border-2 border-dashed"
                      style={{
                        left: `${(d.x ?? 0) * 100}%`,
                        top: `${(d.y ?? 0) * 100}%`,
                        width: `${(d.w ?? 0) * 100}%`,
                        height: `${(d.h ?? 0) * 100}%`,
                        borderColor: i % 2 ? "#EF9F27" : "#E24B4A",
                      }}
                    />
                  </div>
                ))}
              </div>
              {activeItem.analysisStatus === "failed" && (
                <p className="mt-2 text-xs text-red-700">{activeItem.analysisError}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-stone-500">Select or upload a finding</p>
          )}
        </section>

        {/* Detail form */}
        <aside
          className="overflow-y-auto border-l p-4"
          style={{
            borderColor: "var(--color-border-tertiary)",
            background: "var(--color-background-primary)",
          }}
        >
          {activeItem ? (
            <FindingForm
              item={activeItem}
              readOnly={readOnly}
              onChange={updateField}
            />
          ) : (
            <p className="text-sm text-stone-500">No finding selected</p>
          )}
        </aside>
      </div>
    </div>
  );
}

function FindingForm({
  item,
  readOnly,
  onChange,
}: {
  item: InspectionItem;
  readOnly: boolean;
  onChange: (
    field: keyof InspectionItemPatch,
    value: InspectionItemPatch[keyof InspectionItemPatch]
  ) => void;
}) {
  const edited = new Set(item.editedFields);
  const fieldClass = (name: string) =>
    edited.has(name) ? "border-l-[3px] border-l-amber-500 pl-2" : "";

  return (
    <div className="space-y-4 text-sm">
      <label className={`block ${fieldClass("findings")}`}>
        <span className="text-xs font-medium uppercase tracking-wide text-stone-500">
          Findings
        </span>
        <textarea
          className="mt-1 w-full rounded-lg border p-2 text-sm"
          rows={4}
          disabled={readOnly}
          value={item.findings ?? ""}
          onChange={(e) => onChange("findings", e.target.value)}
        />
        {item.aiConfidence != null && (
          <span className="text-[11px] text-stone-500">
            AI confidence: {Math.round(item.aiConfidence * 100)}%
          </span>
        )}
      </label>

      <div className="grid grid-cols-2 gap-2">
        <label>
          <span className="text-xs text-stone-500">Rust grade</span>
          <select
            className="mt-1 w-full rounded border px-2 py-1"
            disabled={readOnly}
            value={item.rustGrade ?? ""}
            onChange={(e) => onChange("rustGrade", e.target.value as RustGrade)}
          >
            <option value="">—</option>
            {RUST_GRADES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-stone-500">CoF</span>
          <input
            type="number"
            min={1}
            max={5}
            className="mt-1 w-full rounded border px-2 py-1"
            disabled={readOnly}
            value={item.cof ?? ""}
            onChange={(e) => onChange("cof", Number(e.target.value))}
          />
        </label>
        <label>
          <span className="text-xs text-stone-500">Findings priority</span>
          <select
            className="mt-1 w-full rounded border px-2 py-1"
            disabled={readOnly}
            value={item.findingsPriority ?? ""}
            onChange={(e) => onChange("findingsPriority", e.target.value as Priority)}
          >
            <option value="">—</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-stone-500">SAP priority</span>
          <select
            className="mt-1 w-full rounded border px-2 py-1"
            disabled={readOnly}
            value={item.sapPriority ?? ""}
            onChange={(e) => onChange("sapPriority", e.target.value as Priority)}
          >
            <option value="">—</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        <span className="text-xs text-stone-500">Equipment type</span>
        <select
          className="mt-1 w-full rounded border px-2 py-1"
          disabled={readOnly}
          value={item.equipmentType ?? ""}
          onChange={(e) => onChange("equipmentType", e.target.value)}
        >
          <option value="">—</option>
          {EQUIP_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      <label>
        <span className="text-xs text-stone-500">Equipment ID</span>
        <input
          className="mt-1 w-full rounded border px-2 py-1"
          disabled={readOnly}
          value={item.equipmentId ?? ""}
          onChange={(e) => onChange("equipmentId", e.target.value)}
        />
      </label>

      <label className={`block ${fieldClass("recommendation")}`}>
        <span className="text-xs text-stone-500">Rec. code</span>
        <select
          className="mt-1 w-full rounded border px-2 py-1"
          disabled={readOnly}
          value={item.recommendationCode ?? ""}
          onChange={(e) =>
            onChange("recommendationCode", e.target.value as RecommendationCode)
          }
        >
          <option value="">—</option>
          {REC_CODES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <textarea
          className="mt-2 w-full rounded-lg border p-2 text-sm"
          rows={3}
          disabled={readOnly}
          value={item.recommendation ?? ""}
          onChange={(e) => onChange("recommendation", e.target.value)}
        />
      </label>

      <div className="flex flex-wrap gap-3 text-xs">
        {(
          [
            ["furtherInspection", "Further insp."],
            ["openInsulation", "Open insul."],
            ["scaffold", "Scaffold"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center gap-1">
            <input
              type="checkbox"
              disabled={readOnly}
              checked={Boolean(item[key])}
              onChange={(e) => onChange(key, e.target.checked)}
            />
            {label}
          </label>
        ))}
      </div>

      <label>
        <span className="text-xs text-stone-500">Review status</span>
        <select
          className="mt-1 w-full rounded border px-2 py-1"
          disabled={readOnly}
          value={item.reviewStatus}
          onChange={(e) => onChange("reviewStatus", e.target.value as ReviewStatus)}
        >
          <option value="unreviewed">unreviewed</option>
          <option value="in_progress">in_progress</option>
          <option value="confirmed">confirmed</option>
        </select>
      </label>
    </div>
  );
}
