const API_BASE_URL = "http://localhost:3000";

function getAuthToken() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["alethiaAuthToken"], ({ alethiaAuthToken }) => {
      resolve(alethiaAuthToken || "");
    });
  });
}

async function apiRequest(path, options = {}) {
  const token = await getAuthToken();
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: token } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (options.rawResponse) {
    return response;
  }

  return response.json();
}

async function readErrorMessage(response) {
  const fallback = `Request failed with status ${response.status}`;

  try {
    const text = await response.text();
    if (!text) {
      return fallback;
    }

    try {
      const parsed = JSON.parse(text);
      return parsed.error || parsed.message || text;
    } catch (error) {
      return text;
    }
  } catch (error) {
    return fallback;
  }
}

async function authSignup({ name, email, password }) {
  return apiRequest("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, name, password }),
  });
}

async function authLogin({ email, password }) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

async function createSessionRequest({ prompt, duration }) {
  return apiRequest("/session", {
    method: "POST",
    body: JSON.stringify({ prompt, duration }),
  });
}

async function getSessionRequest(sessionId) {
  return apiRequest(`/session/${sessionId}`, {
    method: "GET",
  });
}

async function addSessionEvent(sessionId, payload) {
  return apiRequest(`/session/${sessionId}/event`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

function readSseData(buffer) {
  return buffer
    .split("\n\n")
    .map((chunk) => chunk.trim())
    .filter((chunk) => chunk.startsWith("data:"))
    .map((chunk) => chunk.replace(/^data:\s*/, ""));
}

async function finishSessionRequest(sessionId) {
  const response = await apiRequest(`/session/${sessionId}/finish`, {
    method: "GET",
    rawResponse: true,
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalData = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const messages = readSseData(buffer);
    if (messages.length) {
      finalData = messages[messages.length - 1];
    }
  }

  buffer += decoder.decode();
  const messages = readSseData(buffer);
  if (messages.length) {
    finalData = messages[messages.length - 1];
  }

  if (!finalData || ["failed", "error", "not found"].includes(finalData.toLowerCase())) {
    throw new Error(finalData || "No analysis result returned");
  }

  try {
    return JSON.parse(finalData);
  } catch (error) {
    throw new Error(finalData);
  }
}

async function getDashboard() {
  return apiRequest("/dashboard", {
    method: "GET",
  });
}

async function getDashboardSession(id) {
  return apiRequest(`/dashboard/${id}`, {
    method: "GET",
  });
}