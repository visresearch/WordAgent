const DIALOG_CONFIG = Object.freeze({
  setting: Object.freeze({ height: 75, width: 65 }),
  about: Object.freeze({ height: 70, width: 48 }),
  templates: Object.freeze({ height: 75, width: 65 }),
});

const OPEN_EXTERNAL_LINK_MESSAGE = "open-external-link";
const CREATE_TEMPLATE_MESSAGE = "create-template-document";
const TEMPLATE_RESULT_MESSAGE = "template-document-result";
const TEMPLATE_ID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

let activeDialog = null;
let dialogOpening = false;

export function createDialogUrl(view, baseUrl) {
  if (!DIALOG_CONFIG[view]) {
    throw new Error(`Unsupported dialog view: ${view}`);
  }

  const url = new URL("dialog.html", baseUrl);
  url.searchParams.set("view", view);
  return url.toString();
}

function clearDialog(dialog) {
  if (activeDialog === dialog) {
    activeDialog = null;
  }
}

function normalizeExternalUrl(url) {
  const normalized = new URL(url).toString();
  const protocol = new URL(normalized).protocol;
  if (protocol !== "http:" && protocol !== "https:") {
    throw new Error(`Unsupported external URL protocol: ${protocol}`);
  }
  return normalized;
}

export function createExternalLinkMessage(url) {
  return JSON.stringify({
    type: OPEN_EXTERNAL_LINK_MESSAGE,
    url: normalizeExternalUrl(url),
  });
}

export function openExternalLinkFromDialog(
  url,
  {
    office = globalThis.Office,
    openWindow = globalThis.open,
  } = {}
) {
  const normalizedUrl = normalizeExternalUrl(url);
  const messageParent = office?.context?.ui?.messageParent;
  if (typeof messageParent === "function") {
    messageParent.call(office.context.ui, createExternalLinkMessage(normalizedUrl));
    return true;
  }

  return Boolean(openWindow?.(normalizedUrl, "_blank", "noopener,noreferrer"));
}

export function handleDialogMessage(
  event,
  {
    office = globalThis.Office,
    openWindow = globalThis.open,
  } = {}
) {
  let message;
  try {
    message = JSON.parse(event?.message || "");
  } catch (error) {
    return false;
  }

  if (message?.type !== OPEN_EXTERNAL_LINK_MESSAGE) {
    return false;
  }

  const normalizedUrl = normalizeExternalUrl(message.url);
  const openBrowserWindow = office?.context?.ui?.openBrowserWindow;
  if (typeof openBrowserWindow === "function") {
    openBrowserWindow.call(office.context.ui, normalizedUrl);
    return true;
  }

  return Boolean(openWindow?.(normalizedUrl, "_blank", "noopener,noreferrer"));
}

export function createTemplateDialogRequester(office = globalThis.Office) {
  let pending;
  let subscribed = false;
  return async (id) => {
    if (!TEMPLATE_ID.test(id)) throw new Error("Invalid template ID.");
    await office?.onReady?.();
    const ui = office?.context?.ui;
    if (!ui?.messageParent || !ui?.addHandlerAsync ||
        office.context.requirements?.isSetSupported("DialogApi", "1.2") === false) {
      throw new Error("This Word host cannot open a document from the dialog. Download the template copy instead.");
    }
    if (!subscribed) {
      await new Promise((resolve, reject) => {
        ui.addHandlerAsync(office.EventType.DialogParentMessageReceived, (event) => {
          let result;
          try { result = JSON.parse(event.message); } catch (error) { return; }
          if (result?.type === TEMPLATE_RESULT_MESSAGE && pending?.id === result.id) {
            pending.finish(result.error ? new Error(result.error) : null);
          }
        }, (result) => result.status === (office.AsyncResultStatus?.Succeeded ?? "succeeded")
          ? resolve()
          : reject(new Error(result.error?.message || "Unable to connect to the Word task pane.")));
      });
      subscribed = true;
    }
    if (pending) throw new Error("Word is already opening a template.");
    return new Promise((resolve, reject) => {
      const finish = (error) => {
        clearTimeout(timer);
        pending = null;
        if (error) reject(error);
        else resolve();
      };
      const timer = setTimeout(() => finish(new Error("Word did not confirm creation of the copy.")), 60_000);
      pending = { id, finish };
      try {
        ui.messageParent(JSON.stringify({ type: CREATE_TEMPLATE_MESSAGE, id }));
      } catch (error) {
        finish(error);
      }
    });
  };
}

async function openTemplateDocument(event, dialog, createDocumentFromTemplate) {
  let message;
  try { message = JSON.parse(event?.message || ""); } catch (error) { return false; }
  if (message?.type !== CREATE_TEMPLATE_MESSAGE || !TEMPLATE_ID.test(message.id)) return false;

  const result = { type: TEMPLATE_RESULT_MESSAGE, id: message.id };
  try {
    await createDocumentFromTemplate(message.id);
  } catch (error) {
    result.error = error?.message || String(error);
  }
  if (activeDialog === dialog) dialog.messageChild?.(JSON.stringify(result));
  return true;
}

export function openOfficeDialog(
  view,
  {
    office = globalThis.Office,
    baseUrl = globalThis.location?.href,
    openWindow = globalThis.open,
    createDocumentFromTemplate,
  } = {}
) {
  const config = DIALOG_CONFIG[view];
  if (!config) {
    throw new Error(`Unsupported dialog view: ${view}`);
  }

  const url = createDialogUrl(view, baseUrl);
  const displayDialogAsync = office?.context?.ui?.displayDialogAsync;

  // Keep the pages usable in a normal browser during local development.
  if (typeof displayDialogAsync !== "function") {
    return openWindow?.(url, "_blank", "popup=yes,width=900,height=650") ?? null;
  }

  if (activeDialog || dialogOpening) {
    return activeDialog;
  }

  dialogOpening = true;
  displayDialogAsync.call(
    office.context.ui,
    url,
    {
      ...config,
      displayInIframe: true,
      promptBeforeOpen: false,
    },
    (result) => {
      dialogOpening = false;
      const succeeded = office.AsyncResultStatus?.Succeeded ?? "succeeded";
      if (result.status !== succeeded) {
        console.error("Failed to open Office dialog:", result.error);
        return;
      }

      const dialog = result.value;
      activeDialog = dialog;
      dialog.addEventHandler(office.EventType.DialogEventReceived, () => clearDialog(dialog));
      dialog.addEventHandler(office.EventType.DialogMessageReceived, async (event) => {
        if (view === "templates" && createDocumentFromTemplate &&
            await openTemplateDocument(event, dialog, createDocumentFromTemplate)) return;
        handleDialogMessage(event, { office, openWindow });
      });
    }
  );

  return true;
}

export function resetDialogStateForTests() {
  activeDialog = null;
  dialogOpening = false;
}
