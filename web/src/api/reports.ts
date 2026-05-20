import { apiFetch } from "@/api/client";
import type {
  ReportActionResponse,
  ReportDetail,
  ReportListResponse,
} from "@/types/inspection";

type ListReportsParams = Partial<{
  q: string;
  plant: string;
  systemCode: string;
  preparer: string;
  reviewer: string;
  approver: string;
  status: string;
  page: number;
  limit: number;
  sort: string;
}>;

function withQuery(base: string, params: ListReportsParams): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    q.set(k, String(v));
  }
  const qs = q.toString();
  return qs ? `${base}?${qs}` : base;
}

export async function listReports(
  params: ListReportsParams = {}
): Promise<ReportListResponse> {
  return apiFetch<ReportListResponse>(withQuery("/api/reports", params));
}

export async function getReport(reportId: string): Promise<ReportDetail> {
  return apiFetch<ReportDetail>(`/api/reports/${reportId}`);
}

export function reportPdfUrl(reportId: string): string {
  return `/api/reports/${reportId}/pdf`;
}

export async function approveReport(reportId: string): Promise<ReportActionResponse> {
  return apiFetch<ReportActionResponse>(`/api/reports/${reportId}/approve`, {
    method: "POST",
  });
}

export async function requestReportChanges(
  reportId: string,
  comment: string
): Promise<ReportActionResponse> {
  return apiFetch<ReportActionResponse>(`/api/reports/${reportId}/request-changes`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ comment }),
  });
}

export type BulkDeleteReportsResponse = {
  deleted: string[];
  failed: { id: string; reason: string }[];
};

export async function deleteReport(reportId: string): Promise<{ ok: boolean; id: string }> {
  return apiFetch(`/api/reports/${reportId}`, { method: "DELETE" });
}

export async function deleteReportsBulk(
  reportIds: string[]
): Promise<BulkDeleteReportsResponse> {
  return apiFetch<BulkDeleteReportsResponse>("/api/reports/bulk-delete", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reportIds }),
  });
}
