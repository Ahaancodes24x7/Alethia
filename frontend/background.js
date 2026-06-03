const externalTelemetry = {
  open_count: 0,
  close_count: 0,
};

chrome.tabs.onCreated.addListener(() => {
  externalTelemetry.open_count += 1;
});

chrome.tabs.onRemoved.addListener(() => {
  externalTelemetry.close_count += 1;
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "getExternalTelemetry") {
    sendResponse({
      external_tab_open_count: externalTelemetry.open_count,
      external_tab_close_count: externalTelemetry.close_count,
    });
  }
});








