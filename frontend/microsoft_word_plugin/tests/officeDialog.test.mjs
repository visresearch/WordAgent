import assert from "node:assert/strict";
import test from "node:test";

import {
  createDialogUrl,
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
  const dialog = {
    addEventHandler(type, handler) {
      received.eventType = type;
      received.handler = handler;
    },
  };
  const office = {
    AsyncResultStatus: { Succeeded: "succeeded" },
    EventType: { DialogEventReceived: "dialog-event" },
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
  assert.equal(received.eventType, "dialog-event");
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
