const output = document.getElementById("output");
const captureButton = document.getElementById("captureButton");
const sendButton = document.getElementById("sendButton");
let lastSnapshot = null;

function getFormData() {
  return {
    session_id: document.getElementById("sessionId").value.trim(),
    user_id: document.getElementById("userId").value.trim(),
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

  // Connection Required: Replace the URL below with your backend endpoint.
  // fetch("https://your-backend.example.com/telemetry", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify(payload),
  // })
  //   .then((res) => res.json())
  //   .then((result) => updateOutput({ status: "sent", result }))
  //   .catch((err) => updateOutput({ error: err.message }));

  console.warn("Connection Required: backend send not implemented.");
  updateOutput({ status: "ready-to-send", payload });
}

captureButton.addEventListener("click", capturePageSignals);
sendButton.addEventListener("click", sendToAiModel);







