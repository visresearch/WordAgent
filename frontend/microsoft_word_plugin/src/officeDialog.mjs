const DIALOG_CONFIG = Object.freeze({
  setting: Object.freeze({ height: 75, width: 65 }),
  about: Object.freeze({ height: 70, width: 48 }),
});

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
    }
  );

  return true;
}

export function resetDialogStateForTests() {
  activeDialog = null;
  dialogOpening = false;
}
