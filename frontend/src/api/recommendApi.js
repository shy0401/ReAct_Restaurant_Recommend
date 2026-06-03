const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function getApiBaseUrl() {
  return API_BASE_URL;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail || `API request failed: ${response.status}`);
  }

  return response.json();
}

export function recommendFood(payload) {
  return request("/recommend", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runAgentQuery(payload) {
  return request("/agent/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMcpStatus() {
  return request("/mcp/status");
}

export function getHealth() {
  return request("/health");
}

export function getPlaceQuickView(payload) {
  return request("/places/quick-view", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
