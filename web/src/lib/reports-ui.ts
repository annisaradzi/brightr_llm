export function formatReportDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function formatReportDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function statusBadgeClass(status: string): string {
  switch (status) {
    case "approved":
      return "v2-badge v2-badge-approved";
    case "in_review":
      return "v2-badge v2-badge-review";
    case "submitted":
      return "v2-badge v2-badge-submitted";
    default:
      return "v2-badge v2-badge-draft";
  }
}

export function statusLabel(status: string): string {
  switch (status) {
    case "in_review":
      return "In review";
    case "approved":
      return "Approved";
    case "submitted":
      return "Submitted";
    case "draft":
      return "Draft";
    default:
      return status;
  }
}

export function priorityClass(p: string | null | undefined): string {
  if (p === "high") return "priority-high";
  if (p === "medium") return "priority-medium";
  if (p === "low") return "priority-low";
  return "";
}

export function priorityLabel(p: string | null | undefined): string {
  if (!p) return "—";
  return p.charAt(0).toUpperCase() + p.slice(1);
}

export function equipmentTypeLabel(t: string | null | undefined): string {
  if (!t) return "—";
  return t
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
