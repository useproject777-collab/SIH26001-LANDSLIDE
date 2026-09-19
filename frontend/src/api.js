const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `GET ${path} failed`);
  }
  return response.json();
}

export async function apiPost(path) {
  const response = await fetch(`${API_BASE}${path}`, { method: "POST" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `POST ${path} failed`);
  }
  return response.json();
}

export { API_BASE };
