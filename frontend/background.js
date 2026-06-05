const externalTelemetry = {
  open_count: 0,
  close_count: 0,
  session_active: false,
  session_baseline_open_count: 0,
  session_baseline_close_count: 0,
  last_session_open_count: 0,
  last_session_close_count: 0,
};

chrome.tabs.onCreated.addListener(() => {
  externalTelemetry.open_count += 1;
});

chrome.tabs.onRemoved.addListener(() => {
  externalTelemetry.close_count += 1;
});

function getSessionExternalTelemetry() {
  if (externalTelemetry.session_active) {
    return {
      external_tab_open_count: externalTelemetry.open_count - externalTelemetry.session_baseline_open_count,
      external_tab_close_count: externalTelemetry.close_count - externalTelemetry.session_baseline_close_count,
    };
  }

  return {
    external_tab_open_count: externalTelemetry.last_session_open_count,
    external_tab_close_count: externalTelemetry.last_session_close_count,
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "startExternalTelemetrySession") {
    externalTelemetry.session_active = true;
    externalTelemetry.session_baseline_open_count = externalTelemetry.open_count;
    externalTelemetry.session_baseline_close_count = externalTelemetry.close_count;
    externalTelemetry.last_session_open_count = 0;
    externalTelemetry.last_session_close_count = 0;
    sendResponse({ status: "started" });
    return;
  }

  if (message?.type === "stopExternalTelemetrySession") {
    const sessionTelemetry = getSessionExternalTelemetry();
    externalTelemetry.session_active = false;
    externalTelemetry.last_session_open_count = sessionTelemetry.external_tab_open_count;
    externalTelemetry.last_session_close_count = sessionTelemetry.external_tab_close_count;
    sendResponse({ status: "stopped", ...sessionTelemetry });
    return;
  }

  if (message?.type === "getExternalTelemetry") {
    sendResponse(getSessionExternalTelemetry());
  }
});
