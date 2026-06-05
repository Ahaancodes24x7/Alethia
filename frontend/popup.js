const output = document.getElementById("output");
const sendButton = document.getElementById("sendButton");
const loginView = document.getElementById("loginView");
const appView = document.getElementById("appView");
const loginButton = document.getElementById("loginButton");
const bypassLoginButton = document.getElementById("bypassLoginButton");
const logoutButton = document.getElementById("logoutButton");
const startSessionButton = document.getElementById("startSessionButton");
const endSessionButton = document.getElementById("endSessionButton");
const signedInUser = document.getElementById("signedInUser");
const sessionElapsed = document.getElementById("sessionElapsed");
const sessionPrompt = document.getElementById("sessionPrompt");

let lastSnapshot = null;
let currentSession = null;
let timerId = null;

function createId(prefix) {
  const randomId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}_${randomId}`;
}

function getStoredSession(callback) {
  chrome.storage.local.get(["alethiaUser", "alethiaSessionCounter", "alethiaCurrentSession"], callback);
}

function saveCurrentSession(session, callback) {
  chrome.storage.local.set({ alethiaCurrentSession: session }, callback);
}

function createSession(user, sessionCounter) {
  return {
    session_number: sessionCounter,
    session_id: createId("session"),
    user_id: user.user_id,
    prompt: "",
    started_at: null,
    ended_at: null,
    elapsed_ms: 0,
    tab_id: null,
    is_recording: false,
  };
}

function saveLogin(user, sessionCounter) {
  const session = createSession(user, sessionCounter);

  chrome.storage.local.set({
    alethiaUser: user,
    alethiaSessionCounter: sessionCounter,
    alethiaCurrentSession: session,
  });

  return session;
}

function createUserSession(user) {
  getStoredSession(({ alethiaSessionCounter }) => {
    const nextSessionNumber = Number(alethiaSessionCounter || 0) + 1;
    const session = saveLogin(user, nextSessionNumber);
    showApp(user, session);
  });
}

function showLogin() {
  stopTimer();
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
  sessionPrompt.value = session.prompt || "";
  setRecordingState(Boolean(session.is_recording));

  if (session.is_recording && session.started_at) {
    startTimer(session.started_at);
  } else {
    showElapsed(session.elapsed_ms || 0);
  }
}

function setRecordingState(isRecording) {
  startSessionButton.disabled = isRecording;
  endSessionButton.disabled = !isRecording;
  sendButton.disabled = isRecording;
  sessionPrompt.disabled = isRecording;
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function showElapsed(ms) {
  sessionElapsed.textContent = formatDuration(ms);
}

function startTimer(startedAt) {
  stopTimer();
  showElapsed(Date.now() - startedAt);
  timerId = setInterval(() => {
    showElapsed(Date.now() - startedAt);
  }, 1000);
}

function stopTimer(finalElapsedMs) {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }

  if (typeof finalElapsedMs === "number") {
    showElapsed(finalElapsedMs);
  }
}

function updateOutput(data) {
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function getSessionMetadata() {
  return {
    session_number: currentSession?.session_number,
    session_id: currentSession?.session_id || document.getElementById("sessionId").value.trim(),
    user_id: currentSession?.user_id || document.getElementById("userId").value.trim(),
    prompt: sessionPrompt.value.trim(),
    content_type: document.getElementById("contentType").value.trim(),
    mode: document.getElementById("mode").value,
    started_at: currentSession?.started_at || null,
    ended_at: currentSession?.ended_at || null,
    elapsed_ms: currentSession?.elapsed_ms || 0,
  };
}

function getActiveTab(callback) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    callback(tabs[0]);
  });
}

function sendMessageToTab(tabId, message, callback) {
  chrome.tabs.sendMessage(tabId, message, (response) => {
    if (chrome.runtime.lastError) {
      callback({ error: chrome.runtime.lastError.message });
      return;
    }

    callback(response || {});
  });
}

function startRecordingSession() {
  if (!currentSession) {
    updateOutput({ error: "Login before starting a session." });
    return;
  }

  const prompt = sessionPrompt.value.trim();
  if (!prompt) {
    updateOutput({ error: "Enter a prompt before starting the session." });
    sessionPrompt.focus();
    return;
  }

  getActiveTab((activeTab) => {
    if (!activeTab?.id) {
      updateOutput({ error: "No active tab found." });
      return;
    }

    const startedAt = Date.now();
    const nextSession = {
      ...currentSession,
      ...getSessionMetadata(),
      prompt,
      started_at: startedAt,
      ended_at: null,
      elapsed_ms: 0,
      tab_id: activeTab.id,
      is_recording: true,
    };

    sendMessageToTab(activeTab.id, {
      type: "startTelemetrySession",
      session: nextSession,
    }, (response) => {
      if (response.error) {
        updateOutput({ error: "Content script not available on this page.", details: response.error });
        return;
      }

      const actualStartedAt = response.started_at || startedAt;
      currentSession = {
        ...nextSession,
        started_at: actualStartedAt,
      };
      lastSnapshot = null;
      saveCurrentSession(currentSession);
      setRecordingState(true);
      startTimer(actualStartedAt);
      updateOutput({
        status: "session-started",
        session: getSessionMetadata(),
      });
    });
  });
}

function endRecordingSession() {
  if (!currentSession?.is_recording) {
    updateOutput({ error: "No active session is recording." });
    return;
  }

  const tabId = currentSession.tab_id;
  if (!tabId) {
    updateOutput({ error: "No recording tab is saved for this session." });
    return;
  }

  sendMessageToTab(tabId, { type: "stopTelemetrySession" }, (response) => {
    if (response.error) {
      updateOutput({ error: "Could not stop the recorded page.", details: response.error });
      return;
    }

    const endedAt = response.ended_at || Date.now();
    const elapsedMs = currentSession.started_at ? endedAt - currentSession.started_at : 0;
    lastSnapshot = response.snapshot || null;
    currentSession = {
      ...currentSession,
      ended_at: endedAt,
      elapsed_ms: elapsedMs,
      is_recording: false,
    };

    saveCurrentSession(currentSession);
    setRecordingState(false);
    stopTimer(elapsedMs);
    updateOutput({
      status: "session-ended",
      session: getSessionMetadata(),
      telemetry: lastSnapshot,
    });
  });
}

function sendToAiModel() {
  if (currentSession?.is_recording) {
    updateOutput({ error: "End the session before analyzing." });
    return;
  }

  if (!lastSnapshot) {
    updateOutput({ error: "Start and end a session before analyzing." });
    return;
  }

  const payload = {
    ...getSessionMetadata(),
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

loginButton.addEventListener("click", () => {
  const name = document.getElementById("loginName").value.trim();
  const email = document.getElementById("loginEmail").value.trim();

  if (!name || !email) {
    return;
  }

  createUserSession({
    name,
    email,
    user_id: createId("user"),
  });
});

bypassLoginButton.addEventListener("click", () => {
  createUserSession({
    name: "Guest User",
    email: "",
    user_id: createId("guest"),
  });
});

startSessionButton.addEventListener("click", startRecordingSession);
endSessionButton.addEventListener("click", endRecordingSession);
sendButton.addEventListener("click", sendToAiModel);

logoutButton.addEventListener("click", () => {
  if (currentSession?.is_recording) {
    updateOutput({ error: "End the session before logging out." });
    return;
  }

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
