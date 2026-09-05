import { apiGet, apiSend } from "../client";
import { authEndpoints } from "../apiEndpoints";
// Expected: { id, name, email, role }, or null when not signed in.
//
// Deliberately no mock fallback. Returning a fake session made RequireRole
// wave everyone through - the guard looked like access control while enforcing
// nothing. Not signed in must read as not signed in.
export async function loadSession() {
  try {
    return await apiGet(authEndpoints.me);
  } catch {
    return null;
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
