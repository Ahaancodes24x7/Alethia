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
const sessionDuration = document.getElementById("sessionDuration");
const comprehensionScore = document.getElementById("comprehensionScore");
const retentionScore = document.getElementById("retentionScore");
const fatigueScore = document.getElementById("fatigueScore");

let lastSnapshot = null;
let currentSession = null;
let timerId = null;

const STORAGE_KEYS = [
  "alethiaUser",
  "alethiaAuthToken",
  "alethiaSessionCounter",
  "alethiaCurrentSession",
];

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch (error) {
    return {};
  }
}

function createId(prefix) {
  const randomId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}_${randomId}`;
}

function getStoredSession(callback) {
  chrome.storage.local.get(STORAGE_KEYS, callback);
}

function saveCurrentSession(session, callback) {
  chrome.storage.local.set({ alethiaCurrentSession: session }, callback);
}

function createSession(user, sessionCounter) {
  return {
    session_number: sessionCounter,
    session_id: "",
    user_id: user.user_id,
    prompt: "",
    duration: 60,
    started_at: null,
    ended_at: null,
    elapsed_ms: 0,
    tab_id: null,
    is_recording: false,
  };
}

function saveLogin(user, sessionCounter, token) {
  const session = createSession(user, sessionCounter);

  const values = {
    alethiaUser: user,
    alethiaSessionCounter: sessionCounter,
    alethiaCurrentSession: session,
  };

  if (token) {
    values.alethiaAuthToken = token;
  }

  chrome.storage.local.set(values);

  return session;
}

function createUserSession(user, token) {
  getStoredSession(({ alethiaSessionCounter }) => {
    const nextSessionNumber = Number(alethiaSessionCounter || 0) + 1;
    const session = saveLogin(user, nextSessionNumber, token);
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
  sessionDuration.value = session.duration || 60;
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
  sessionDuration.disabled = isRecording;
}

function hasBackendLogin() {
  return getAuthToken().then(Boolean);
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
    duration: Number(sessionDuration.value) || currentSession?.duration || 60,
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

async function startRecordingSession() {
  if (!currentSession) {
    updateOutput({ error: "Login before starting a session." });
    return;
  }

  if (!(await hasBackendLogin())) {
    updateOutput({
      error: "Backend sessions require login.",
      details: "Use Login / Create Account before starting a session.",
    });
    showLogin();
    return;
  }

  const prompt = sessionPrompt.value.trim();
  if (!prompt) {
    updateOutput({ error: "Enter a prompt before starting the session." });
    sessionPrompt.focus();
    return;
  }

  const duration = Number(sessionDuration.value);
  if (!Number.isFinite(duration) || duration <= 0) {
    updateOutput({ error: "Enter a valid session duration in minutes." });
    sessionDuration.focus();
    return;
  }

  let backendSession;
  try {
    updateOutput({ status: "creating-backend-session" });
    backendSession = await createSessionRequest({ prompt, duration });
  } catch (error) {
    updateOutput({ error: "Could not create backend session.", details: error.message });
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
      session_id: backendSession.id,
      prompt,
      duration,
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
      document.getElementById("sessionId").value = currentSession.session_id;
      sessionDuration.value = currentSession.duration;
      lastSnapshot = null;
      saveCurrentSession(currentSession);
      setRecordingState(true);
      startTimer(actualStartedAt);
      updateOutput({
        status: "session-started",
        backend: backendSession,
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

async function uploadTelemetryEvents(sessionId, snapshot) {
  const events = buildBackendEvents(snapshot);

  for (const event of events) {
    await addSessionEvent(sessionId, event);
  }

  return events.length;
}

function buildBackendEvents(snapshot) {
  const rawEvents = Array.isArray(snapshot?.events) ? snapshot.events : [];
  const normalizedEvents = rawEvents
    .map((event) => normalizeTelemetryEvent(event, snapshot))
    .filter(Boolean);

  if (normalizedEvents.length) {
    return normalizedEvents;
  }

  const summary = snapshot?.feature_summary || {};
  return [{
    timestamp: toSeconds(snapshot?.session_ended_at || Date.now()),
    event_type: "session_summary",
    payload: {
      ...summary,
      mode: snapshot?.mode || "learning",
      prompt: snapshot?.prompt || "",
    },
  }];
}

function normalizeTelemetryEvent(event, snapshot = {}) {
  const eventType = String(event?.event_type || event?.type || "").trim().toLowerCase();
  if (!eventType) {
    return null;
  }

  const payload = event?.payload && typeof event.payload === "object" ? { ...event.payload } : {};
  const timestamp = toSeconds(event?.timestamp || Date.now());
  const summary = snapshot?.feature_summary || {};

  if (eventType === "scroll") {
    return {
      timestamp,
      event_type: "scroll",
      payload: {
        ...payload,
        scroll_y: Number(payload.scroll_y ?? payload.position ?? payload.scroll_position ?? 0),
        delta_y: Number(payload.delta_y ?? payload.delta ?? payload.scroll_delta ?? 0),
        document_height: Number(payload.document_height ?? document.documentElement?.scrollHeight ?? summary.scroll_total_distance_px ?? 1),
      },
    };
  }

  if (eventType === "keydown" || eventType === "keyup") {
    const key = payload.key || "";
    return {
      timestamp,
      event_type: eventType,
      payload: {
        ...payload,
        key_category: key === "Backspace" || key === "Delete" ? "backspace" : "character",
      },
    };
  }

  if (eventType === "video_rewind") {
    return {
      timestamp,
      event_type: "video_seek_backward",
      payload: {
        ...payload,
        from_position: Number(payload.from ?? payload.from_position ?? 0),
        to_position: Number(payload.to ?? payload.to_position ?? 0),
      },
    };
  }

  if (eventType === "video_replay_behavior") {
    return {
      timestamp,
      event_type: "video_position",
      payload: {
        ...payload,
        position: Number(payload.position ?? payload.to ?? 0),
      },
    };
  }

  if (eventType === "video_pause") {
    return {
      timestamp,
      event_type: "video_pause",
      payload: {
        ...payload,
        position: Number(payload.position ?? payload.at ?? 0),
        duration: Number(payload.duration ?? 0),
      },
    };
  }

  if (eventType === "hint_click") {
    return {
      timestamp,
      event_type: "hint_request",
      payload: {
        ...payload,
        question_id: payload.question_id || "q1",
        hint_level: Number(payload.hint_level || 1),
      },
    };
  }

  if (eventType === "answer_submit") {
    return {
      timestamp,
      event_type: "answer_submit",
      payload: {
        ...payload,
        question_id: payload.question_id || "q1",
        is_correct: Boolean(payload.is_correct ?? payload.correctness ?? false),
        attempt_number: Number(payload.attempt_number ?? payload.attempts ?? 1),
      },
    };
  }

  if (eventType === "confidence_rating") {
    return {
      timestamp,
      event_type: "confidence_rating",
      payload: {
        ...payload,
        question_id: payload.question_id || "q1",
        rating: Number(payload.rating || 0),
      },
    };
  }

  return {
    timestamp,
    event_type: eventType,
    payload,
  };
}

function toSeconds(timestamp) {
  const value = Number(timestamp);
  if (!Number.isFinite(value)) {
    return Date.now() / 1000;
  }

  return value > 100000000000 ? value / 1000 : value;
}


function formatScore(value) {
  if (value === undefined || value === null || value === "") {
    return "--";
  }

  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }

  return String(value);
}

function percentScore(value) {
  if (value === undefined || value === null || value === "") {
    return "--";
  }

  const number = Number(value);
  if (!Number.isFinite(number)) {
    return String(value);
  }

  const normalized = number <= 1 ? number * 100 : number;
  return `${Math.round(normalized)}%`;
}

function updateScoreCards(report) {
  const source = report?.report || report || {};
  const modelOutputs = source.model_outputs || {};
  const metrics = source.metrics || {};

  comprehensionScore.textContent = percentScore(
    modelOutputs.comprehension_score
      ?? metrics.comprehension_score
      ?? source.comprehension
      ?? source.comprehension_score
      ?? source.overall_learning_score
  );

  retentionScore.textContent = percentScore(
    modelOutputs.retention_probability
      ?? modelOutputs.retention_strength
      ?? (modelOutputs.retention_risk_score !== undefined ? 1 - modelOutputs.retention_risk_score : undefined)
      ?? metrics.retention_strength
      ?? source.retention
      ?? source.retention_score
  );

  fatigueScore.textContent = percentScore(
    modelOutputs.fatigue_probability
      ?? metrics.fatigue_probability
      ?? source.fatigue
      ?? source.fatigue_score
  );
}

async function sendToAiModel() {
  if (currentSession?.is_recording) {
    updateOutput({ error: "End the session before analyzing." });
    return;
  }

  if (!lastSnapshot) {
    updateOutput({ error: "Start and end a session before analyzing." });
    return;
  }

  const sessionId = currentSession.session_id;
  if (!sessionId) {
    updateOutput({ error: "No backend session ID found. Start a new session first." });
    return;
  }

  try {
    sendButton.disabled = true;
    updateOutput({ status: "uploading-events" });
    const uploadedEvents = await uploadTelemetryEvents(sessionId, lastSnapshot);
    updateOutput({ status: "running-analysis", uploaded_events: uploadedEvents });
      const result = await finishSessionRequest(sessionId);
    sendButton.disabled = Boolean(currentSession?.is_recording);
  }
}

async function loginOrCreateAccount(name, email, password) {
  try {
    return await authLogin({ email, password });
  } catch (loginError) {
    await authSignup({ name, email, password });
    return authLogin({ email, password });
  }
}

loginButton.addEventListener("click", async () => {
  const name = document.getElementById("loginName").value.trim();
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;

  if (!name || !email || !password) {
    updateOutput({ error: "Name, email and password are required." });
    return;
  }

  try {
    loginButton.disabled = true;
    const auth = await loginOrCreateAccount(name, email, password);
    const payload = decodeJwtPayload(auth.token);
    createUserSession({
      name,
      email,
      user_id: payload.id || email,
    }, auth.token);
  } catch (error) {
    updateOutput({ error: "Could not log in or create account.", details: error.message });
  } finally {
    loginButton.disabled = false;
  }
});

bypassLoginButton.addEventListener("click", () => {
  chrome.storage.local.remove(["alethiaAuthToken"]);
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

  chrome.storage.local.remove(["alethiaUser", "alethiaAuthToken", "alethiaCurrentSession"], () => {
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
