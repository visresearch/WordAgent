const STORAGE_PREFIX = 'wence_wps_ui_zoom';
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.1;

export const UI_ZOOM_EVENT = 'wps-ui-zoom-change';

let zoom = 1;

function getStorageKey() {
  const { hash = '', search = '', pathname = '' } = window.location || {};
  const route = hash.replace(/^#/, '');
  const queryIndex = route.indexOf('?');
  const params = new URLSearchParams(queryIndex >= 0 ? route.slice(queryIndex + 1) : search);
  const windowId = params.get('windowId');
  const panel = (route.split('?')[0] || pathname).split('/').filter(Boolean).pop();
  // A page without an explicit owner keeps its zoom in memory only.
  return windowId && panel ? `${STORAGE_PREFIX}:${windowId}:${panel}` : null;
}

function normalizeZoom(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0
    ? Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(number * 10) / 10))
    : 1;
}

export function getUiZoom() {
  return zoom;
}

export function getUiViewport() {
  return { width: window.innerWidth / zoom, height: window.innerHeight / zoom };
}

// Chromium < 128 returns rectangles before root CSS zoom; newer CEF versions
// include that zoom. Measure the root to use layout coordinates on both.
export function getUiRect(element) {
  const rect = element.getBoundingClientRect();
  const scale = document.documentElement.getBoundingClientRect().width / getUiViewport().width || 1;
  return Object.fromEntries(
    ['left', 'top', 'right', 'bottom', 'width', 'height'].map(key => [key, rect[key] / scale])
  );
}

export function installUiZoom() {
  const storageKey = getStorageKey();
  const root = document.documentElement;
  const previousZoom = root.style.zoom;
  const viewportProperties = ['--wps-viewport-width', '--wps-viewport-height'];
  const previousViewport = viewportProperties.map(name => root.style.getPropertyValue(name));

  const updateViewport = () => {
    const { width, height } = getUiViewport();
    // CSS viewport units are not reduced by CSS zoom. Compensate explicitly so
    // the chat input and dialog footers stay inside the native pane at any DPI.
    root.style.setProperty(viewportProperties[0], `${width}px`);
    root.style.setProperty(viewportProperties[1], `${height}px`);
  };

  const applyZoom = (value, persist = false) => {
    const next = normalizeZoom(value);
    const changed = next !== zoom;
    zoom = next;
    root.style.zoom = String(zoom);
    updateViewport();
    if (persist && storageKey) {
      try {
        window.localStorage.setItem(storageKey, String(zoom));
      } catch {
        // Some WPS installations restrict storage; zoom still works in memory.
      }
    }
    if (changed) {
      window.dispatchEvent(new Event(UI_ZOOM_EVENT));
    }
  };

  const onWheel = event => {
    if (!event.ctrlKey || event.altKey || event.metaKey || event.shiftKey
      || !Number.isFinite(event.deltaY) || event.deltaY === 0) {
      return;
    }
    // Prevent native browser zoom too, including when already at the limit.
    event.preventDefault();
    // Windows and Linux CEF report different delta magnitudes/units. A wheel
    // tick changes the scale by 10% on either platform, regardless of deltaMode.
    applyZoom(zoom + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP), true);
  };

  const onKeydown = event => {
    if (event.ctrlKey && !event.altKey && !event.metaKey && !event.shiftKey
      && event.key === '0') {
      event.preventDefault();
      applyZoom(1, true);
    }
  };

  let storedZoom;
  try {
    if (storageKey) storedZoom = window.localStorage.getItem(storageKey);
  } catch {
    // Storage is optional in the embedded browser.
  }
  applyZoom(storedZoom);

  const wheelOptions = { capture: true, passive: false };
  const keyOptions = { capture: true };
  window.addEventListener('wheel', onWheel, wheelOptions);
  window.addEventListener('keydown', onKeydown, keyOptions);
  window.addEventListener('resize', updateViewport);

  return () => {
    window.removeEventListener('wheel', onWheel, wheelOptions);
    window.removeEventListener('keydown', onKeydown, keyOptions);
    window.removeEventListener('resize', updateViewport);
    root.style.zoom = previousZoom;
    viewportProperties.forEach((name, index) => {
      if (previousViewport[index]) {
        root.style.setProperty(name, previousViewport[index]);
      } else {
        root.style.removeProperty(name);
      }
    });
    zoom = 1;
  };
}
