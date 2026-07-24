const PARA_ID_PATTERN = /^[+-]?(0|[1-9]\d*)$/;
const PARA_ID_KEYS = new Set(["paraid", "paragraphid"]);

function normalizeParaID(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    value = String(value);
  }
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return PARA_ID_PATTERN.test(normalized) ? String(Number(normalized)) : null;
}

function normalizeMetadataKey(key) {
  return String(key || "")
    .toLowerCase()
    .replace(/[^a-z]/g, "");
}

function findParaIDInObject(value, seen = new Set()) {
  if (!value || typeof value !== "object" || seen.has(value)) {
    return null;
  }
  seen.add(value);

  for (const [key, candidate] of Object.entries(value)) {
    if (PARA_ID_KEYS.has(normalizeMetadataKey(key))) {
      const paraID = normalizeParaID(candidate);
      if (paraID) {
        return paraID;
      }
    }
  }

  for (const candidate of Object.values(value)) {
    const paraID = findParaIDInObject(candidate, seen);
    if (paraID) {
      return paraID;
    }
  }
  return null;
}

export function parseParaIDFromContentControlMeta(metadata) {
  const direct = normalizeParaID(metadata);
  if (direct) {
    return direct;
  }
  if (typeof metadata !== "string") {
    return null;
  }

  const text = metadata.trim();
  if (!text) {
    return null;
  }

  try {
    const parsed = JSON.parse(text);
    const fromJson = findParaIDInObject(parsed);
    if (fromJson) {
      return fromJson;
    }
  } catch (error) {
    // Legacy tags and titles were also stored as plain key/value text.
  }

  const match = text.match(
    /(?:^|[\s,;|{[(])(?:wence[\s_.:-]*)?para(?:graph)?[\s_.-]*id\s*(?:[:=#]|[-_])\s*["']?([+-]?(?:0|[1-9]\d*))/i
  );
  return match ? normalizeParaID(match[1]) : null;
}

export function parseParaIDFromContentControlMetadata(contentControl) {
  if (!contentControl) {
    return null;
  }
  return (
    parseParaIDFromContentControlMeta(contentControl.tag) ||
    parseParaIDFromContentControlMeta(contentControl.title)
  );
}
