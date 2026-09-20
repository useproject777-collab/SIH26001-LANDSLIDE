const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API_BASE = (import.meta.env.VITE_API_BASE || (isLocal ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");

function authHeaders() {
  const token = localStorage.getItem("landslide_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseError(response, method, path) {
  const text = await response.text();
  let message = text || `${method} ${path} failed with ${response.status}`;
  try {
    const data = JSON.parse(text);
    message = data.detail || message;
  } catch {}
  if (response.status === 401) {
    localStorage.removeItem("landslide_token");
    window.dispatchEvent(new Event("landslide-auth-expired"));
  }
  throw new Error(message);
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: { Accept: "application/json", ...authHeaders() },
  });
  if (!response.ok) await parseError(response, "GET", path);
  return response.json();
}

export async function apiPost(path, body = undefined) {
  const headers = { ...authHeaders() };
  if (!(body instanceof FormData)) headers["Content-Type"] = "application/json";
  const options = { method: "POST", headers };
  if (body !== undefined) options.body = body instanceof FormData ? body : JSON.stringify(body);
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) await parseError(response, "POST", path);
  return response.json();
}

export { API_BASE };
