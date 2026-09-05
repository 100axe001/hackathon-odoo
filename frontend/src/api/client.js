// Shared request wrapper. Every component and hook goes through this — nothing
// calls fetch() directly.
//
// The backend wraps every response as { success, message, data }, so this unwraps
// `data` and hands callers the plain payload. A non-2xx status, or success:false,
// throws — which is what lets each api-function fall back to its mock.

const API_BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);

  const body = await res.json();

  // Tolerate a bare payload as well as the envelope. A half-migrated endpoint
  // then still renders instead of silently producing undefined.
  if (
    body &&
    typeof body === "object" &&
    !Array.isArray(body) &&
    "success" in body
  ) {
    if (!body.success) throw new Error(body.message || "request failed");
    return body.data;
  }
  return body;
}

export const apiGet = (path) => request(path);

export const apiSend = (path, method, body) =>
  request(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
