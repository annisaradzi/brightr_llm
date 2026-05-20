"use client";

import {
  approveReport,
  getReport,
  reportPdfUrl,
  requestReportChanges,
} from "@/api/reports";
import { itemImageSrc } from "@/api/sessions";
import { ApiError } from "@/api/client";
import { ReportsShell } from "@/components/reports/ReportsShell";
import {
  formatReportDateTime,
  priorityClass,
  priorityLabel,
  statusBadgeClass,
  statusLabel,
} from "@/lib/reports-ui";
import type { InspectionItem, ReportDetail } from "@/types/inspection";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export function ReportDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";

  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [commentOpen, setCommentOpen] = useState(false);
  const [comment, setComment] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const r = await getReport(id);
      setReport(r);
    } catch (e) {
      setReport(null);
      setError(e instanceof ApiError ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const canApprove =
    report?.status === "submitted" || report?.status === "in_review";
  const canRequestChanges =
    report?.status === "submitted" ||
    report?.status === "in_review" ||
    report?.status === "approved";

  const onApprove = async () => {
    if (!report || !canApprove) return;
    setActionBusy(true);
    try {
      await approveReport(report.id);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Approve failed");
    } finally {
      setActionBusy(false);
    }
  };

  const onRequestChanges = async () => {
    if (!report || !comment.trim()) return;
    setActionBusy(true);
    try {
      await requestReportChanges(report.id, comment.trim());
      setComment("");
      setCommentOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setActionBusy(false);
    }
  };

  if (loading) {
    return (
      <ReportsShell active="reports">
        <div className="flex min-h-[50vh] items-center justify-center text-sm text-stone-500">
          Loading report…
        </div>
      </ReportsShell>
    );
  }

  if (!report) {
    return (
      <ReportsShell active="reports">
        <div className="v2-wrap py-16 text-center">
          <h1 className="v2-h1 mb-2">Report not found</h1>
          <p className="mb-6 text-sm" style={{ color: "var(--v2-text-2)" }}>
            {error ??
              "This report may not be submitted yet, or the link is invalid."}
          </p>
          <Link href="/reports" className="v2-btn">
            Back to Reports
          </Link>
        </div>
      </ReportsShell>
    );
  }

  return (
    <ReportsShell active="reports">
      <div className="report-detail-shell">
        <div className="report-subbar">
          <Link href="/reports" className="report-back-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back to Reports
          </Link>
          <span className="report-title">
            Executive report <strong>{report.systemReportNumber}</strong>
          </span>
          <div className="report-actions">
            {report.pdfUrl && (
              <a href={reportPdfUrl(report.id)} className="v2-btn v2-btn-primary" download>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download PDF
              </a>
            )}
          </div>
        </div>

        {error && (
          <p className="px-5 py-2 text-sm" style={{ color: "var(--v2-error)" }}>
            {error}
          </p>
        )}

        <div className="report-content">
          <aside className="report-summary-col">
            <div className="report-summary-card">
              <h1 className="report-user-report-id">
                {report.userReportNumber || report.systemReportNumber}
              </h1>
              <p className="report-system-report-id">
                System report: {report.systemReportNumber}
              </p>
              <div className="report-meta-list">
                <div>
                  <strong>Plant:</strong> {report.plant ?? "—"}
                </div>
                <div>
                  <strong>System:</strong> {report.systemCode ?? "—"}
                </div>
                <div>
                  <strong>Preparer:</strong> {report.preparerName ?? "—"}
                </div>
                <div>
                  <strong>Reviewer:</strong> {report.reviewerName ?? "—"}
                </div>
                <div>
                  <strong>Approver:</strong> {report.approverName ?? "—"}
                </div>
                <div>
                  <strong>Submitted:</strong> {formatReportDateTime(report.submittedAt)}
                </div>
                <div>
                  <strong>Status:</strong>{" "}
                  <span className={statusBadgeClass(report.status)}>
                    {statusLabel(report.status)}
                  </span>
                </div>
              </div>
              {report.executiveSummary && (
                <p className="report-summary-prose">{report.executiveSummary}</p>
              )}
            </div>

            <div className="report-stats">
              <div className="report-stat">
                <div className="report-stat-label">Findings</div>
                <div className="report-stat-value">{report.totalFindings}</div>
              </div>
              <div className="report-stat">
                <div className="report-stat-label">High priority</div>
                <div className="report-stat-value high">{report.highPriorityCount}</div>
                <div className="report-stat-caption">TBR required</div>
              </div>
              <div className="report-stat">
                <div className="report-stat-label">TBS actions</div>
                <div className="report-stat-value medium">{report.tbsCount}</div>
                <div className="report-stat-caption">Insulation removal</div>
              </div>
              <div className="report-stat">
                <div className="report-stat-label">Avg CoF</div>
                <div className="report-stat-value">
                  {report.avgCof != null ? report.avgCof.toFixed(1) : "—"}
                </div>
              </div>
            </div>
          </aside>

          <main className="report-findings-col">
            <h2 className="report-section-title">Findings summary</h2>
            <div className="report-findings-table">
              <table>
                <thead>
                  <tr>
                    <th>Image</th>
                    <th>Code</th>
                    <th>Equipment ID</th>
                    <th>Findings</th>
                    <th>Rust</th>
                    <th>CoF</th>
                    <th>Rec.</th>
                    <th>Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {report.items.map((item) => (
                    <FindingRows
                      key={item.id}
                      item={item}
                      expanded={expandedId === item.id}
                      onToggle={() =>
                        setExpandedId((cur) => (cur === item.id ? null : item.id))
                      }
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </main>
        </div>

        {(canApprove || canRequestChanges) && (
          <div
            className={`report-approval-bar${report.status === "approved" ? " approved" : ""}`}
          >
            <span className="report-approval-msg">
              {report.status === "approved"
                ? "This report has been approved."
                : "Review this report and approve or request changes."}
            </span>
            <div className="report-approval-actions">
              {canApprove && (
                <button
                  type="button"
                  className="v2-btn v2-btn-approve"
                  disabled={actionBusy}
                  onClick={onApprove}
                >
                  Approve
                </button>
              )}
              {canRequestChanges && (
                <>
                  {!commentOpen ? (
                    <button
                      type="button"
                      className="v2-btn"
                      disabled={actionBusy}
                      onClick={() => setCommentOpen(true)}
                    >
                      Request changes
                    </button>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="text"
                        className="reports-field-input min-w-[200px]"
                        placeholder="Comment for preparer…"
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                      />
                      <button
                        type="button"
                        className="v2-btn v2-btn-primary"
                        disabled={actionBusy || !comment.trim()}
                        onClick={onRequestChanges}
                      >
                        Send
                      </button>
                      <button
                        type="button"
                        className="v2-btn"
                        onClick={() => setCommentOpen(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </ReportsShell>
  );
}

function FindingRows({
  item,
  expanded,
  onToggle,
}: {
  item: InspectionItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const findings = item.findings || item.aiFindings || "—";
  const rec = item.recommendation || item.aiRecommendation || "—";

  return (
    <>
      <tr
        className={`finding-row${expanded ? " expanded" : ""}`}
        onClick={onToggle}
      >
        <td>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={itemImageSrc(item)} alt="" className="report-thumb" />
        </td>
        <td className="report-finding-code">{item.code}</td>
        <td>{item.equipmentId ?? "—"}</td>
        <td className="report-findings-truncate">{findings}</td>
        <td>{item.rustGrade ?? "—"}</td>
        <td>{item.cof ?? "—"}</td>
        <td>{item.recommendationCode ?? "—"}</td>
        <td className={priorityClass(item.findingsPriority)}>
          {priorityLabel(item.findingsPriority)}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={8}>
            <div className="report-expanded-content">
              <div className="report-expanded-grid">
                <div className="report-expanded-image">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={itemImageSrc(item)} alt={item.code} />
                </div>
                <div className="report-expanded-text">
                  <h4>Findings</h4>
                  <p>{findings}</p>
                  <h4>Recommendation</h4>
                  <p>{rec}</p>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
