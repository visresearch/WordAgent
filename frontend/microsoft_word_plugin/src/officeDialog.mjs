const DIALOG_CONFIG = Object.freeze({
  setting: Object.freeze({ height: 75, width: 65 }),
  about: Object.freeze({ height: 70, width: 48 }),
});

const OPEN_EXTERNAL_LINK_MESSAGE = "open-external-link";

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

export function openOfficeDialog(
  view,
  {
    office = globalThis.Office,
    baseUrl = globalThis.location?.href,
    openWindow = globalThis.open,
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
      dialog.addEventHandler(office.EventType.DialogMessageReceived, (event) =>
        handleDialogMessage(event, { office, openWindow })
      );
    }
  );

  return true;
}

export function resetDialogStateForTests() {
  activeDialog = null;
  dialogOpening = false;
}
