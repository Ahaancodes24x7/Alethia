const pageTelemetry = {
  events: [],
  counts: {
    cursor: 0,
    scroll: 0,
    keydown: 0,
    keyup: 0,
    focus_loss: 0,
    focus_gain: 0,
    external: 0,
    tab_switch: 0,
    copy: 0,
    paste: 0,
    mouse_click: 0,
    double_click: 0,
  },
  cursor: {
    points: [],
    totalDistance: 0,
    lastPoint: null,
  },
  scroll: {
    lastPosition: window.scrollY || 0,
    totalDistance: 0,
    reversalCount: 0,
    lastDirection: 0,
  },
  video: {
    perVideo: {},
    rewindCount: 0,
    pauseCount: 0,
    replayCount: 0,
    recentActions: [],
  },
  typing: {
    keyDownMap: {},
    dwellTimes: [],
    flightTimes: [],
    backspaceCount: 0,
    correctionBurstCount: 0,
    burstLength: 0,
    lastKeyWasCorrection: false,
    lastKeydownTime: null,
  },
  focus: {
    totalHiddenMs: 0,
    lastHiddenTime: document.hidden ? Date.now() : null,
    blurCount: 0,
    focusCount: 0,
    currentState: document.hidden ? "hidden" : "visible",
  },
  quiz: {
    quizStartCount: 0,
    questionAttemptCount: 0,
    answerSubmitCount: 0,
    hintClickCount: 0,
    confidenceRatings: [],
  },
  idle: {
    isIdle: false,
    lastActive: Date.now(),
    idleStartMs: null,
    idleSessions: [],
  },
};

function recordEvent(type, payload = {}) {
  pageTelemetry.events.push({
    event_type: type,
    timestamp: Date.now(),
    payload,
  });

  if (pageTelemetry.counts[type] !== undefined) {
    pageTelemetry.counts[type] += 1;
  }
}

function addCursorPoint(x, y) {
  const now = Date.now();
  const nextPoint = { x, y, t: now };
  const previous = pageTelemetry.cursor.lastPoint;

  if (previous) {
    const dx = x - previous.x;
    const dy = y - previous.y;
    const dist = Math.hypot(dx, dy);
    pageTelemetry.cursor.totalDistance += dist;
  }

  pageTelemetry.cursor.points.push(nextPoint);
  pageTelemetry.cursor.lastPoint = nextPoint;
}

function handleScroll() {
  const position = window.scrollY;
  const delta = position - pageTelemetry.scroll.lastPosition;
  const direction = Math.sign(delta);

  if (delta !== 0) {
    pageTelemetry.scroll.totalDistance += Math.abs(delta);
    if (direction !== 0 && pageTelemetry.scroll.lastDirection !== 0 && direction !== pageTelemetry.scroll.lastDirection) {
      pageTelemetry.scroll.reversalCount += 1;
    }
    pageTelemetry.scroll.lastDirection = direction;
    pageTelemetry.scroll.lastPosition = position;
    recordEvent("scroll", { position, delta });
  }
}

function handleKeydown(event) {
  const now = Date.now();
  const key = event.key;
  pageTelemetry.typing.keyDownMap[key] = now;

  if (pageTelemetry.typing.lastKeydownTime !== null) {
    pageTelemetry.typing.flightTimes.push(now - pageTelemetry.typing.lastKeydownTime);
  }
  pageTelemetry.typing.lastKeydownTime = now;

  if (key === "Backspace" || key === "Delete") {
    pageTelemetry.typing.backspaceCount += 1;
    if (pageTelemetry.typing.lastKeyWasCorrection) {
      pageTelemetry.typing.burstLength += 1;
    } else {
      pageTelemetry.typing.burstLength = 1;
      pageTelemetry.typing.lastKeyWasCorrection = true;
    }
  } else {
    if (pageTelemetry.typing.lastKeyWasCorrection && pageTelemetry.typing.burstLength >= 3) {
      pageTelemetry.typing.correctionBurstCount += 1;
    }
    pageTelemetry.typing.lastKeyWasCorrection = false;
    pageTelemetry.typing.burstLength = 0;
  }

  recordEvent("keydown", { key });
}

function handleKeyup(event) {
  const now = Date.now();
  const key = event.key;
  const downTime = pageTelemetry.typing.keyDownMap[key];
  if (downTime) {
    pageTelemetry.typing.dwellTimes.push(now - downTime);
    delete pageTelemetry.typing.keyDownMap[key];
  }
  recordEvent("keyup", { key });
}

function handleVisibilityChange() {
  const now = Date.now();
  if (document.hidden) {
    pageTelemetry.counts.tab_switch += 1;
    pageTelemetry.focus.lastHiddenTime = now;
    pageTelemetry.focus.currentState = "hidden";
    recordEvent("focus_loss", {});
    pageTelemetry.focus.blurCount += 1;
  } else {
    if (pageTelemetry.focus.lastHiddenTime !== null) {
      pageTelemetry.focus.totalHiddenMs += now - pageTelemetry.focus.lastHiddenTime;
      pageTelemetry.focus.lastHiddenTime = null;
    }
    pageTelemetry.focus.currentState = "visible";
    recordEvent("focus_gain", {});
    pageTelemetry.focus.focusCount += 1;
  }
}

function classifyUrl(url) {
  const host = (new URL(url)).hostname || '';
  const edu = /khanacademy|coursera|edx|udemy|udacity|learn|school|canvas/i;
  if (edu.test(host)) return 'education';
  const social = /facebook|instagram|twitter|linkedin|reddit/i;
  if (social.test(host)) return 'social';
  const video = /youtube|vimeo|wistia|brightcove/i;
  if (video.test(host)) return 'video';
  return 'other';
}

// Video tracking helpers
function attachVideoListeners(vid) {
  if (!vid) return;
  const id = vid.dataset.__telemetryId || Math.random().toString(36).slice(2, 9);
  vid.dataset.__telemetryId = id;
  pageTelemetry.video.perVideo[id] = pageTelemetry.video.perVideo[id] || { lastTime: 0, rewinds: 0, pauses: 0 };

  vid.addEventListener('seeking', () => {
    try {
      const prev = pageTelemetry.video.perVideo[id].lastTime || vid.currentTime;
      const curr = vid.currentTime;
      pageTelemetry.video.perVideo[id].lastTime = curr;
      if (curr + 0.5 < prev) {
        pageTelemetry.video.rewindCount += 1;
        pageTelemetry.video.perVideo[id].rewinds += 1;
        pageTelemetry.video.recentActions.push({ type: 'rewind', t: Date.now(), videoId: id, from: prev, to: curr });
        recordEvent('video_rewind', { videoId: id, from: prev, to: curr });
      }
    } catch (e) { /* best-effort */ }
  });

  vid.addEventListener('pause', () => {
    pageTelemetry.video.pauseCount += 1;
    pageTelemetry.video.perVideo[id].pauses = (pageTelemetry.video.perVideo[id].pauses || 0) + 1;
    pageTelemetry.video.recentActions.push({ type: 'pause', t: Date.now(), videoId: id, at: vid.currentTime });
    recordEvent('video_pause', { videoId: id, at: vid.currentTime });
  });

  vid.addEventListener('play', () => {
    // if a rewind was immediately followed by play, call it a replay behavior
    const last = pageTelemetry.video.recentActions[pageTelemetry.video.recentActions.length - 1];
    if (last && last.type === 'rewind' && Date.now() - last.t < 5000) {
      pageTelemetry.video.replayCount += 1;
      recordEvent('video_replay_behavior', { videoId: id });
    }
  });
}

function scanAndAttachVideos() {
  document.querySelectorAll('video').forEach(attachVideoListeners);
}

// Observe DOM for new video elements
const videoObserver = new MutationObserver((mutations) => {
  for (const m of mutations) {
    if (m.addedNodes && m.addedNodes.length) {
      m.addedNodes.forEach((n) => {
        if (n.nodeType === 1 && n.tagName && n.tagName.toLowerCase() === 'video') attachVideoListeners(n);
        if (n.querySelectorAll) n.querySelectorAll('video').forEach(attachVideoListeners);
      });
    }
  }
});
videoObserver.observe(document, { childList: true, subtree: true });
scanAndAttachVideos();

// Copy/Paste detection
window.addEventListener('copy', (e) => { pageTelemetry.counts.copy += 1; recordEvent('copy', {}); });
window.addEventListener('paste', (e) => { pageTelemetry.counts.paste += 1; recordEvent('paste', {}); });

// Mouse click / double click
window.addEventListener('click', (e) => { pageTelemetry.counts.mouse_click += 1; pageTelemetry.counts.mouse_click = pageTelemetry.counts.mouse_click; recordEvent('mouse_click', { x: e.clientX, y: e.clientY, tag: e.target.tagName }); });
window.addEventListener('dblclick', (e) => { pageTelemetry.counts.double_click += 1; recordEvent('double_click', { x: e.clientX, y: e.clientY, tag: e.target.tagName }); });

// Simple quiz/button heuristics
window.addEventListener('click', (e) => {
  try {
    const el = e.target;
    const text = (el.innerText || el.textContent || '').toLowerCase();
    if (/start quiz|begin quiz|quiz start/.test(text)) {
      pageTelemetry.quiz.quizStartCount += 1;
      recordEvent('quiz_start', {});
    }
    if (/submit answer|submit|check answer|answer submit/.test(text)) {
      pageTelemetry.quiz.answerSubmitCount += 1;
      recordEvent('answer_submit', {});
    }
    if (/attempt|try question|next question/.test(text)) {
      pageTelemetry.quiz.questionAttemptCount += 1;
      recordEvent('question_attempt', {});
    }
    if (/hint/.test(text)) {
      pageTelemetry.quiz.hintClickCount += 1;
      recordEvent('hint_click', {});
    }
    // confidence inputs
    if (el.tagName === 'INPUT' && /confidence|self[- ]?rated/.test(el.name || el.id || '')) {
      const val = parseFloat(el.value);
      if (!Number.isNaN(val)) {
        pageTelemetry.quiz.confidenceRatings.push(val);
        recordEvent('confidence_rating', { rating: val });
      }
    }
  } catch (e) { /* best-effort */ }
});

// Idle detection
const IDLE_THRESHOLD = 60000; // 1 minute
function markActive() {
  pageTelemetry.idle.lastActive = Date.now();
  if (pageTelemetry.idle.isIdle) {
    pageTelemetry.idle.isIdle = false;
    const end = Date.now();
    pageTelemetry.idle.idleSessions.push({ start: pageTelemetry.idle.idleStartMs, end });
    recordEvent('USER_IDLE_END', { start: pageTelemetry.idle.idleStartMs, end });
    pageTelemetry.idle.idleStartMs = null;
  }
}

function checkIdle() {
  const now = Date.now();
  if (!pageTelemetry.idle.isIdle && now - pageTelemetry.idle.lastActive > IDLE_THRESHOLD) {
    pageTelemetry.idle.isIdle = true;
    pageTelemetry.idle.idleStartMs = now;
    recordEvent('USER_IDLE_START', { at: now });
  }
}

['mousemove', 'keydown', 'scroll', 'click', 'touchstart'].forEach((ev) => window.addEventListener(ev, markActive, { passive: true }));
setInterval(checkIdle, 2000);

function handleWindowBlur() {
  recordEvent("focus_loss", { reason: "window_blur" });
  pageTelemetry.focus.blurCount += 1;
  pageTelemetry.focus.currentState = "hidden";
  if (pageTelemetry.focus.lastHiddenTime === null) {
    pageTelemetry.focus.lastHiddenTime = Date.now();
  }
}

function handleWindowFocus() {
  recordEvent("focus_gain", { reason: "window_focus" });
  pageTelemetry.focus.focusCount += 1;
  pageTelemetry.focus.currentState = "visible";
  if (pageTelemetry.focus.lastHiddenTime !== null) {
    pageTelemetry.focus.totalHiddenMs += Date.now() - pageTelemetry.focus.lastHiddenTime;
    pageTelemetry.focus.lastHiddenTime = null;
  }
}

function average(values) {
  if (!values.length) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

async function buildTelemetrySnapshot() {
  const externalResponse = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "getExternalTelemetry" }, (resp) => {
      resolve(resp || {});
    });
  });

  const now = Date.now();
  const activeTimeMs = pageTelemetry.cursor.points.length > 1
    ? pageTelemetry.cursor.points[pageTelemetry.cursor.points.length - 1].t - pageTelemetry.cursor.points[0].t
    : 0;

  const sessionStart = pageTelemetry.events.length ? pageTelemetry.events[0].timestamp : now;
  const sessionDurationMs = now - sessionStart;
  const sessionMinutes = Math.max(0.001, sessionDurationMs / 60000);

  // video densities
  const videoRewindCount = pageTelemetry.video.rewindCount || 0;
  const videoPauseCount = pageTelemetry.video.pauseCount || 0;
  const videoReplayCount = pageTelemetry.video.replayCount || 0;

  const video_rewind_density = Math.round((videoRewindCount / sessionMinutes) * 100) / 100; // rewinds per minute
  const pause_density = Math.round((videoPauseCount / sessionMinutes) * 100) / 100; // pauses per minute

  // concept_confusion heuristic: bursts of rewinds/pauses (>=3) within 30s windows
  let concept_confusion_count = 0;
  try {
    const times = (pageTelemetry.video.recentActions || []).map(a => a.t).sort((a, b) => a - b);
    let i = 0;
    while (i < times.length) {
      let j = i + 1;
      while (j < times.length && times[j] - times[i] <= 30000) j++;
      if (j - i >= 3) concept_confusion_count += 1;
      i = j;
    }
  } catch (e) { concept_confusion_count = 0; }

  // idle summary
  let totalIdleMs = 0;
  for (const s of pageTelemetry.idle.idleSessions) {
    if (s && s.end && s.start) totalIdleMs += Math.max(0, s.end - s.start);
  }
  if (pageTelemetry.idle.isIdle && pageTelemetry.idle.idleStartMs) {
    totalIdleMs += now - pageTelemetry.idle.idleStartMs;
  }

  return {
    mode: document.hidden ? "learning" : "learning",
    modality_coverage: ["cursor", "scroll", "typing", "focus", "video", "external"],
    feature_summary: {
      cursor_move_count: pageTelemetry.counts.cursor,
      cursor_path_length_px: Math.round(pageTelemetry.cursor.totalDistance),
      cursor_avg_speed_px_s: activeTimeMs > 0 ? Math.round((pageTelemetry.cursor.totalDistance / activeTimeMs) * 1000) : 0,
      scroll_event_count: pageTelemetry.counts.scroll,
      scroll_total_distance_px: Math.round(pageTelemetry.scroll.totalDistance),
      scroll_reversal_count: pageTelemetry.scroll.reversalCount,
      typing_keydown_count: pageTelemetry.counts.keydown,
      typing_keyup_count: pageTelemetry.counts.keyup,
      typing_backspace_count: pageTelemetry.typing.backspaceCount,
      typing_dwell_mean_ms: Math.round(average(pageTelemetry.typing.dwellTimes)),
      typing_flight_mean_ms: Math.round(average(pageTelemetry.typing.flightTimes)),
      typing_correction_burst_count: pageTelemetry.typing.correctionBurstCount,
      focus_blur_count: pageTelemetry.counts.focus_loss,
      focus_gain_count: pageTelemetry.counts.focus_gain,
      focus_total_hidden_ms: pageTelemetry.focus.totalHiddenMs,
      focus_last_state: pageTelemetry.focus.currentState,
      external_tab_open_count: externalResponse.external_tab_open_count || 0,
      external_tab_close_count: externalResponse.external_tab_close_count || 0,
      session_duration_ms: sessionDurationMs,

      // newly added fields
      video_rewind_count: videoRewindCount,
      video_pause_count: videoPauseCount,
      video_replay_count: videoReplayCount,
      video_rewind_density: video_rewind_density,
      pause_density: pause_density,
      replay_behavior_count: videoReplayCount,
      concept_confusion_count: concept_confusion_count,
      tab_switch_count: pageTelemetry.counts.tab_switch,
      current_domain: window.location.hostname,
      page_title: document.title || '',
      url_category: classifyUrl(window.location.href),
      quiz_start_count: pageTelemetry.quiz.quizStartCount,
      question_attempt_count: pageTelemetry.quiz.questionAttemptCount,
      answer_submit_count: pageTelemetry.quiz.answerSubmitCount,
      hint_click_count: pageTelemetry.quiz.hintClickCount,
      confidence_rating_mean: Math.round(average(pageTelemetry.quiz.confidenceRatings)),
      copy_count: pageTelemetry.counts.copy,
      paste_count: pageTelemetry.counts.paste,
      user_idle_total_ms: totalIdleMs,
      user_idle_sessions: pageTelemetry.idle.idleSessions.length,
      mouse_click_count: pageTelemetry.counts.mouse_click,
      double_click_count: pageTelemetry.counts.double_click,
    },
    counts: {
      ...pageTelemetry.counts,
      external_tab_open_count: externalResponse.external_tab_open_count || 0,
      external_tab_close_count: externalResponse.external_tab_close_count || 0,
    },
    recent_events: pageTelemetry.events.slice(-30),
    note: "Connection Required: send these features to the backend for DL model scoring.",
  };
}

window.addEventListener("mousemove", (event) => {
  addCursorPoint(event.clientX, event.clientY);
  recordEvent("cursor", { x: event.clientX, y: event.clientY });
});
window.addEventListener("scroll", handleScroll, { passive: true });
window.addEventListener("keydown", handleKeydown);
window.addEventListener("keyup", handleKeyup);
window.addEventListener("visibilitychange", handleVisibilityChange);
window.addEventListener("blur", handleWindowBlur);
window.addEventListener("focus", handleWindowFocus);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "getTelemetrySnapshot") {
    buildTelemetrySnapshot().then((snapshot) => {
      sendResponse(snapshot);
    });
    return true;
  }
});