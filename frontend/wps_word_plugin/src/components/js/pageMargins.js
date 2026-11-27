import { assertAppliedMargins, PAGE_MARGIN_SIDES, planPageMargins, summarizePageMargins } from '../../../../shared/js/pageMargins.mjs';

const fields = { top: 'TopMargin', bottom: 'BottomMargin', left: 'LeftMargin', right: 'RightMargin' };

function snapshotMargins(doc) {
  const sections = doc.Sections;
  const setups = sections?.Count > 0
    ? Array.from({ length: sections.Count }, (_, index) => sections.Item(index + 1).PageSetup)
    : [doc.PageSetup];
  return setups.map(setup => ({
    setup,
    margins: Object.fromEntries(PAGE_MARGIN_SIDES.map(side => [side, setup[fields[side]]])),
    width: setup.PageWidth,
    height: setup.PageHeight
  }));
}

export function readPageMargins(doc) {
  try {
    return summarizePageMargins(snapshotMargins(doc).map(section => section.margins));
  } catch {
    return null;
  }
}

export function adjustPageMargins(doc, pageMarginsCm) {
  if (doc.ReadOnly) throw new Error('当前文档为只读，无法修改页边距。');
  const sections = snapshotMargins(doc);
  const changes = planPageMargins(sections, pageMarginsCm);
  const getValue = ({ setup, side }) => setup[fields[side]];
  const attempted = [];
  try {
    for (const change of changes) {
      attempted.push(change);
      change.setup[fields[change.side]] = change.after;
    }
    assertAppliedMargins(changes, getValue);
    return { success: true, pageMarginsCm: summarizePageMargins(sections.map(({ setup }) =>
      Object.fromEntries(PAGE_MARGIN_SIDES.map(side => [side, setup[fields[side]]])))) };
  } catch (error) {
    for (const change of attempted.reverse()) {
      try {
        if (getValue(change) !== change.before) change.setup[fields[change.side]] = change.before;
      } catch {
        // Restore and verify the other sides even if one setter fails.
      }
    }
    try {
      assertAppliedMargins(attempted, getValue, 'before');
    } catch {
      return { success: null, requiresRead: true, error: `修改页边距失败，未能确认恢复原值：${error.message}` };
    }
    throw error;
  }
}
