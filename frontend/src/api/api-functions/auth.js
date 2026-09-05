import { apiGet, apiSend } from "../client";
import { authEndpoints } from "../apiEndpoints";
import { MOCK_SESSION } from "../mocks";

// Expected: { id, name, email, role }
//
// Falls back to a seeded internal user so the app is navigable before /auth
// exists. Phase 3 replaces the fallback with a redirect to /login.
export async function loadSession() {
  try {
    return await apiGet(authEndpoints.me);
  } catch {
    return MOCK_SESSION;
  }
}

// Expected: { id, name, email, role } - sets an httpOnly cookie
export async function login(email, password) {
  return apiSend(authEndpoints.login, "POST", { email, password });
}

export async function logout() {
  return apiSend(authEndpoints.logout, "POST");
}

// Expected: { id, name, email, role } - self-signup is always SALES_REP.
// The role is decided by the backend and cannot be requested.
export async function signup(email, password, fullName) {
  return apiSend(authEndpoints.signup, "POST", {
    email,
    password,
    full_name: fullName,
  });
}
