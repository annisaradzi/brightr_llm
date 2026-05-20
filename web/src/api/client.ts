export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: "include",
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new ApiError("Unauthorized", 401);
  }
  const text = await res.text();
  let data: unknown = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!res.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data
        ? (data as { detail: unknown }).detail
        : data;
    const msg =
      typeof detail === "string"
        ? detail
        : `Request failed (${res.status})`;
    throw new ApiError(msg, res.status, detail);
  }
  return data as T;
}
