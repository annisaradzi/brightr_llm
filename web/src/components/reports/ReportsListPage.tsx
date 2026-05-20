"use client";

import { deleteReport, deleteReportsBulk, listReports, reportPdfUrl } from "@/api/reports";
import { ApiError } from "@/api/client";
import { ReportsShell } from "@/components/reports/ReportsShell";
import {
  equipmentTypeLabel,
  formatReportDate,
  statusBadgeClass,
  statusLabel,
} from "@/lib/reports-ui";
import type { ReportSummary } from "@/types/inspection";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

function parseSort(raw: string | null): { field: string; dir: "asc" | "desc" } {
  if (!raw) return { field: "submittedAt", dir: "desc" };
  const [field, dir] = raw.split(":");
  return {
    field: field || "submittedAt",
    dir: dir === "asc" ? "asc" : "desc",
  };
}

export function ReportsListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const q = searchParams.get("q") ?? "";
  const plant = searchParams.get("plant") ?? "";
  const status = searchParams.get("status") ?? "";
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10) || 1);
  const sortRaw = searchParams.get("sort");
  const sort = parseSort(sortRaw);

  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchInput, setSearchInput] = useState(q);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const replaceParams = useCallback(
    (patch: Record<string, string | null>) => {
      const p = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v === null || v === "") p.delete(k);
        else p.set(k, v);
      }
      router.replace(`/reports?${p.toString()}`);
    },
    [router, searchParams]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listReports({
        q: q || undefined,
        plant: plant || undefined,
        status: status || undefined,
        page,
        limit,
        sort: `${sort.field}:${sort.dir}`,
      });
      setReports(res.reports);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, [q, plant, status, page, limit, sort.field, sort.dir]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setSearchInput(q);
  }, [q]);

  const activePills = useMemo(() => {
    const pills: { key: string; label: string }[] = [];
    if (q) pills.push({ key: "q", label: `Search: ${q}` });
    if (plant) pills.push({ key: "plant", label: `Plant: ${plant}` });
    if (status) pills.push({ key: "status", label: `Status: ${statusLabel(status)}` });
    return pills;
  }, [q, plant, status]);

  const toggleSort = (field: string) => {
    const next =
      sort.field === field && sort.dir === "desc"
        ? `${field}:asc`
        : `${field}:desc`;
    replaceParams({ sort: next, page: "1" });
  };

  const sortClass = (field: string) => {
    if (sort.field !== field) return "sortable";
    return sort.dir === "asc" ? "sortable sorted-asc" : "sortable sorted-desc";
  };

  const onSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    replaceParams({ q: searchInput.trim() || null, page: "1" });
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const onDeleteOne = async (r: ReportSummary) => {
    if (
      !window.confirm(
        `Delete report ${r.systemReportNumber}? This cannot be undone.`
      )
    ) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await deleteReport(r.id);
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(r.id);
        return next;
      });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  const onBulkDelete = async () => {
    const ids = [...selected];
    if (!ids.length) return;
    if (
      !window.confirm(
        `Delete ${ids.length} report${ids.length === 1 ? "" : "s"}? This cannot be undone.`
      )
    ) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      const res = await deleteReportsBulk(ids);
      if (res.failed.length) {
        setError(
          `Deleted ${res.deleted.length}; failed: ${res.failed.map((f) => f.id).join(", ")}`
        );
      }
      setSelected(new Set());
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Bulk delete failed");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <ReportsShell active="reports">
      <div className="v2-wrap">
        <div className="v2-page-header">
          <h1 className="v2-h1">Visual Inspection Reports</h1>
          <Link href="/" className="v2-new-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Analysis
          </Link>
        </div>

        <form className="reports-search-bar" onSubmit={onSearchSubmit}>
          <svg
            className="reports-search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            className="reports-search-input"
            placeholder="Search by system report #, user report #, equipment ID..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          <button
            type="button"
            className={`reports-filter-toggle${filtersOpen ? " active" : ""}`}
            onClick={() => setFiltersOpen((o) => !o)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
            </svg>
            Filters
          </button>
        </form>

        {activePills.length > 0 && (
          <div className="reports-filter-pills">
            {activePills.map((pill) => (
              <span key={pill.key} className="reports-pill">
                {pill.label}
                <button
                  type="button"
                  className="reports-pill-remove"
                  aria-label={`Remove ${pill.key} filter`}
                  onClick={() => replaceParams({ [pill.key]: null, page: "1" })}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </span>
            ))}
            <button
              type="button"
              className="reports-clear-all"
              onClick={() =>
                replaceParams({ q: null, plant: null, status: null, page: "1" })
              }
            >
              Clear all
            </button>
          </div>
        )}

        <div className={`reports-filters-panel${filtersOpen ? " open" : ""}`}>
          <div className="reports-filter-grid">
            <div className="reports-field">
              <label className="reports-field-label">Plant</label>
              <input
                className="reports-field-input"
                type="text"
                placeholder="e.g. MLNG DUA"
                value={plant}
                onChange={(e) => replaceParams({ plant: e.target.value || null, page: "1" })}
              />
            </div>
            <div className="reports-field">
              <label className="reports-field-label">Status</label>
              <select
                className="reports-field-select"
                value={status}
                onChange={(e) =>
                  replaceParams({ status: e.target.value || null, page: "1" })
                }
              >
                <option value="">All statuses</option>
                <option value="submitted">Submitted</option>
                <option value="in_review">In review</option>
                <option value="approved">Approved</option>
              </select>
            </div>
          </div>
        </div>

        <div className="reports-results-bar">
          <div className="reports-count">
            {loading ? (
              "Loading…"
            ) : (
              <>
                Showing <strong>{reports.length}</strong> of <strong>{total}</strong>{" "}
                reports
              </>
            )}
          </div>
          {selected.size > 0 && (
            <div className="reports-bulk-bar">
              <strong>{selected.size}</strong> selected
              <div className="reports-bulk-actions">
                <button
                  type="button"
                  className="reports-bulk-btn reports-bulk-btn-danger"
                  disabled={deleting || loading}
                  onClick={onBulkDelete}
                >
                  Delete selected
                </button>
                <button
                  type="button"
                  className="reports-bulk-btn"
                  disabled={deleting}
                  onClick={() => setSelected(new Set())}
                >
                  Clear selection
                </button>
              </div>
            </div>
          )}
        </div>

        {error && (
          <p className="mb-4 text-sm" style={{ color: "var(--v2-error)" }}>
            {error}
          </p>
        )}

        <div className="reports-table-wrap">
          <table className="reports-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    className="v2-checkbox"
                    checked={reports.length > 0 && selected.size === reports.length}
                    onChange={(e) => {
                      if (e.target.checked) setSelected(new Set(reports.map((r) => r.id)));
                      else setSelected(new Set());
                    }}
                  />
                </th>
                <th
                  className={sortClass("systemReportNumber")}
                  onClick={() => toggleSort("systemReportNumber")}
                >
                  System report #
                </th>
                <th>User report #</th>
                <th>Plant</th>
                <th>System</th>
                <th>Equipment type</th>
                <th>Equipment ID</th>
                <th>Preparer</th>
                <th className={sortClass("submittedAt")} onClick={() => toggleSort("submittedAt")}>
                  Submitted
                </th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!loading && reports.length === 0 && (
                <tr className="is-empty">
                  <td colSpan={11}>No reports match your filters.</td>
                </tr>
              )}
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>
                    <input
                      type="checkbox"
                      className="v2-checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggleSelect(r.id)}
                    />
                  </td>
                  <td className="report-id">{r.systemReportNumber}</td>
                  <td className="user-report">{r.userReportNumber ?? "—"}</td>
                  <td>{r.plant ?? "—"}</td>
                  <td>{r.systemCode ?? "—"}</td>
                  <td>{equipmentTypeLabel(r.equipmentType)}</td>
                  <td>{r.equipmentId ?? "—"}</td>
                  <td>{r.preparerName ?? "—"}</td>
                  <td>{formatReportDate(r.submittedAt)}</td>
                  <td>
                    <span className={statusBadgeClass(r.status)}>{statusLabel(r.status)}</span>
                  </td>
                  <td>
                    <div className="v2-icon-btn-row">
                      <Link
                        href={`/reports/${r.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="v2-icon-btn"
                        title="View"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      </Link>
                      <Link href={`/?session=${r.id}`} className="v2-icon-btn" title="Edit">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </Link>
                      {r.id && (
                        <a
                          href={reportPdfUrl(r.id)}
                          className="v2-icon-btn"
                          title="Download PDF"
                          download
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                          </svg>
                        </a>
                      )}
                      <button
                        type="button"
                        className="v2-icon-btn v2-icon-btn-danger"
                        title="Delete"
                        disabled={deleting || loading}
                        onClick={() => onDeleteOne(r)}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          <line x1="10" y1="11" x2="10" y2="17" />
                          <line x1="14" y1="11" x2="14" y2="17" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="reports-pagination">
            <button
              type="button"
              className="reports-pagination-btn"
              disabled={page <= 1}
              onClick={() => replaceParams({ page: String(page - 1) })}
            >
              Previous
            </button>
            <span className="text-sm" style={{ color: "var(--v2-text-2)" }}>
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              className="reports-pagination-btn"
              disabled={page >= totalPages}
              onClick={() => replaceParams({ page: String(page + 1) })}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </ReportsShell>
  );
}
