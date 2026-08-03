import assert from "node:assert/strict";
import test from "node:test";

import {
  createExternalLinkMessage,
  createDialogUrl,
  handleDialogMessage,
  openExternalLinkFromDialog,
  openOfficeDialog,
  resetDialogStateForTests,
} from "../src/officeDialog.mjs";

test("creates a same-origin URL for the requested dialog view", () => {
  assert.equal(
    createDialogUrl("setting", "https://localhost:3000/taskpane.html"),
    "https://localhost:3000/dialog.html?view=setting"
  );
});

test("opens settings through the Office dialog API", () => {
  resetDialogStateForTests();
  let received;
  const handlers = new Map();
  const dialog = {
    addEventHandler(type, handler) {
      handlers.set(type, handler);
    },
  };
  const office = {
    AsyncResultStatus: { Succeeded: "succeeded" },
    EventType: {
      DialogEventReceived: "dialog-event",
      DialogMessageReceived: "dialog-message",
    },
    context: {
      ui: {
        displayDialogAsync(url, options, callback) {
          received = { url, options };
          callback({ status: "succeeded", value: dialog });
        },
      },
    },
  };

  assert.equal(
    openOfficeDialog("setting", {
      office,
      baseUrl: "https://localhost:3000/taskpane.html",
    }),
    true
  );
  assert.equal(received.url, "https://localhost:3000/dialog.html?view=setting");
  assert.deepEqual(received.options, {
    height: 75,
    width: 65,
    displayInIframe: true,
    promptBeforeOpen: false,
  });
  assert.equal(typeof handlers.get("dialog-event"), "function");
  assert.equal(typeof handlers.get("dialog-message"), "function");
});

test("asks the parent task pane to open external links from an Office dialog", () => {
  let message;
  const office = {
    context: {
      ui: {
        messageParent(value) {
          message = value;
        },
      },
    },
  };

  assert.equal(
    openExternalLinkFromDialog("https://example.com/docs", { office }),
    true
  );
  assert.deepEqual(JSON.parse(message), {
    type: "open-external-link",
    url: "https://example.com/docs",
  });
});

test("opens dialog external-link messages in the system browser API", () => {
  let openedUrl;
  const office = {
    context: {
      ui: {
        openBrowserWindow(url) {
          openedUrl = url;
        },
      },
    },
  };

  assert.equal(
    handleDialogMessage(
      { message: createExternalLinkMessage("https://example.com/help") },
      { office }
    ),
    true
  );
  assert.equal(openedUrl, "https://example.com/help");
});

test("never navigates the dialog when a browser popup is blocked", () => {
  assert.equal(
    openExternalLinkFromDialog("https://example.com", {
      office: undefined,
      openWindow: () => null,
    }),
    false
  );
});

test("uses a browser popup when the Office dialog API is unavailable", () => {
  resetDialogStateForTests();
  let received;
  const popup = {};

  const result = openOfficeDialog("about", {
    office: undefined,
    baseUrl: "https://localhost:3000/taskpane.html",
    openWindow(...args) {
      received = args;
      return popup;
    },
  });

  assert.equal(result, popup);
  assert.deepEqual(received, [
    "https://localhost:3000/dialog.html?view=about",
    "_blank",
    "popup=yes,width=900,height=650",
  ]);
});
