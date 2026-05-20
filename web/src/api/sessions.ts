import { apiFetch } from "@/api/client";
import type {
  InspectionItem,
  InspectionItemPatch,
  InspectionSession,
  SubmitSessionPayload,
} from "@/types/inspection";

export async function createSession(): Promise<InspectionSession> {
  return apiFetch<InspectionSession>("/api/sessions", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({}),
  });
}

export async function getSession(sessionId: string): Promise<InspectionSession> {
  return apiFetch<InspectionSession>(`/api/sessions/${sessionId}`);
}

export async function uploadSessionImages(
  sessionId: string,
  files: File[]
): Promise<{ sessionId: string; items: InspectionItem[] }> {
  const fd = new FormData();
  for (const f of files) fd.append("images", f);
  return apiFetch(`/api/sessions/${sessionId}/images`, {
    method: "POST",
    body: fd,
  });
}

export async function analyzeSession(
  sessionId: string,
  rerun = false
): Promise<InspectionSession> {
  return apiFetch<InspectionSession>(
    `/api/sessions/${sessionId}/analyze?rerun=${rerun}`,
    { method: "POST" }
  );
}

export async function deleteItem(
  sessionId: string,
  itemId: string
): Promise<InspectionSession> {
  return apiFetch<InspectionSession>(
    `/api/sessions/${sessionId}/items/${itemId}`,
    { method: "DELETE" }
  );
}

export async function patchItem(
  sessionId: string,
  itemId: string,
  patch: InspectionItemPatch
): Promise<InspectionItem> {
  return apiFetch<InspectionItem>(
    `/api/sessions/${sessionId}/items/${itemId}`,
    {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(patch),
    }
  );
}

export async function submitSession(
  sessionId: string,
  payload?: SubmitSessionPayload
): Promise<InspectionSession> {
  return apiFetch<InspectionSession>(`/api/sessions/${sessionId}/submit`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
}

/** Same-origin image URL for Next BFF image route */
export function itemImageSrc(item: InspectionItem): string {
  if (item.imageUrl.startsWith("/api/")) return item.imageUrl;
  return `/api/sessions/${item.sessionId}/items/${item.id}/image`;
}
