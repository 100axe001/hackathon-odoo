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

  if (res.status === 401) {
    // The session expired or was never established. Send the user to sign in
    // rather than letting nineteen screens each render their own error.
    if (!window.location.pathname.startsWith("/login")) {
      window.location.replace("/login");
    }
    throw Object.assign(new Error("401 Unauthorized"), { status: 401 });
  }

  if (!res.ok) {
    // Carry the server's own wording through. It explains *why* - which line is
    // over its ceiling, which endpoint owns a refused transition - and a bare
    // "400 Bad Request" throws that away.
    let detail = null;
    try {
      const body = await res.json();
      detail = body?.detail?.message || body?.message || null;
    } catch {
      detail = null;
    }
    throw Object.assign(
      new Error(detail || `${res.status} ${res.statusText}`),
      {
        status: res.status,
        detail,
      },
    );
  }

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
