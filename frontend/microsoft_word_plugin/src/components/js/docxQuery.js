import { createDocxQuery } from "../../../../shared/js/docxQuery.mjs";
import { PSTYLE, RSTYLE } from "./docxJsonConverter.js";

function normalizeParaIdValue(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return null;
}

const docxQuery = createDocxQuery({
  PSTYLE,
  RSTYLE,
  getRunText: (run) => run?.text ?? "",
  normalizeParaId: normalizeParaIdValue,
});

export const { executeQuery, generateSummary, executeStyleQuery } = docxQuery;
export default docxQuery;
