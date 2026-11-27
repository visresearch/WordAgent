import { createDocxQuery } from '../../../../shared/js/docxQuery.mjs';
import { PSTYLE, RSTYLE } from './docxJsonConverter.js';

const docxQuery = createDocxQuery({
  PSTYLE,
  RSTYLE,
  getRunText: (run) => run?.text ?? run?.formula ?? '',
  normalizeParaId: (value) => Number.isInteger(value) ? value : null,
});

export const { executeQuery, generateSummary, executeStyleQuery } = docxQuery;
export default docxQuery;
