const output = document.getElementById("output");
const captureButton = document.getElementById("captureButton");
const sendButton = document.getElementById("sendButton");
const loginView = document.getElementById("loginView");
const appView = document.getElementById("appView");
const loginButton = document.getElementById("loginButton");
const bypassLoginButton = document.getElementById("bypassLoginButton");
const logoutButton = document.getElementById("logoutButton");
const signedInUser = document.getElementById("signedInUser");
let lastSnapshot = null;
let currentSession = null;

function createId(prefix) {
  const randomId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}_${randomId}`;
}

function getStoredSession(callback) {
  chrome.storage.local.get(["alethiaUser", "alethiaSessionCounter", "alethiaCurrentSession"], callback);
}

function saveSession(user, sessionCounter) {
  const session = {
    session_number: sessionCounter,
    session_id: createId("session"),
    user_id: user.user_id,
    started_at: Date.now(),
  };

  chrome.storage.local.set({
    alethiaUser: user,
    alethiaSessionCounter: sessionCounter,
    alethiaCurrentSession: session,
  });

  return session;
}

function startUserSession(user) {
  getStoredSession(({ alethiaSessionCounter }) => {
    const nextSessionNumber = Number(alethiaSessionCounter || 0) + 1;
    const session = saveSession(user, nextSessionNumber);
    showApp(user, session);
  });
}

function showLogin() {
  loginView.classList.remove("hidden");
  appView.classList.add("hidden");
}

function showApp(user, session) {
  currentSession = session;
  loginView.classList.add("hidden");
  appView.classList.remove("hidden");
  signedInUser.textContent = user.name || user.email || user.user_id;
  document.getElementById("sessionNumber").value = session.session_number;
  document.getElementById("sessionId").value = session.session_id;
  document.getElementById("userId").value = session.user_id;
}

function getFormData() {
  return {
    session_number: currentSession?.session_number,
    session_id: currentSession?.session_id || document.getElementById("sessionId").value.trim(),
    user_id: currentSession?.user_id || document.getElementById("userId").value.trim(),
    content_type: document.getElementById("contentType").value.trim(),
    content_id: document.getElementById("contentId").value.trim(),
    mode: document.getElementById("mode").value,
  };
}

function updateOutput(data) {
  output.textContent = JSON.stringify(data, null, 2);
}

function capturePageSignals() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const activeTab = tabs[0];
    if (!activeTab?.id) {
      updateOutput({ error: "No active tab found." });
      return;
    }

    chrome.tabs.sendMessage(activeTab.id, { type: "getTelemetrySnapshot" }, (response) => {
      if (chrome.runtime.lastError) {
        updateOutput({ error: "Content script not available on this page." });
        return;
      }
      lastSnapshot = response || null;
      updateOutput(lastSnapshot || { error: "No response from page." });
    });
  });
}

function sendToAiModel() {
  if (!lastSnapshot) {
    updateOutput({ error: "Capture page signals before sending." });
    return;
  }

  const payload = {
    ...getFormData(),
    telemetry: lastSnapshot,
    timestamp: Date.now(),
  };

  // Connection Required:
  // fetch("https://your-backend.example.com/telemetry", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify(payload),
  // })
  //   .then((res) => res.json())
  //   .then((result) => updateOutput({ status: "sent", result }))
  //   .catch((err) => updateOutput({ error: err.message }));

  console.warn("Connection Required:");
  updateOutput({ status: "ready-to-send", payload });
}

captureButton.addEventListener("click", capturePageSignals);
sendButton.addEventListener("click", sendToAiModel);
loginButton.addEventListener("click", () => {
  const name = document.getElementById("loginName").value.trim();
  const email = document.getElementById("loginEmail").value.trim();

  if (!name || !email) {
    return;
  }

  startUserSession({
    name,
    email,
    user_id: createId("user"),
  });
});

bypassLoginButton.addEventListener("click", () => {
  startUserSession({
    name: "Guest User",
    email: "",
    user_id: createId("guest"),
  });
});

logoutButton.addEventListener("click", () => {
  chrome.storage.local.remove(["alethiaUser", "alethiaCurrentSession"], () => {
    currentSession = null;
    lastSnapshot = null;
    showLogin();
  });
});

getStoredSession(({ alethiaUser, alethiaCurrentSession }) => {
  if (alethiaUser && alethiaCurrentSession) {
    showApp(alethiaUser, alethiaCurrentSession);
  } else {
    showLogin();
  }
});







