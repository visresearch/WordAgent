/* global Word, Office */

import { assertAppliedMargins, PAGE_MARGIN_SIDES, planPageMargins, summarizePageMargins } from '../../../../shared/js/pageMargins.mjs';

const fields = { top: 'topMargin', bottom: 'bottomMargin', left: 'leftMargin', right: 'rightMargin' };
const marginFields = Object.values(fields);

function supportsPageSetup() {
  return typeof Office === 'undefined' || Office.context?.requirements?.isSetSupported?.('WordApiDesktop', '1.3') !== false;
}

async function loadPageSetups(context, includeSize = false) {
  const sections = context.document.sections;
  sections.load('items');
  await context.sync();
  const setups = sections.items.map(section => section.pageSetup);
  if (!setups.length) throw new Error('无法获取 Word 文档的页面设置。');
  for (const setup of setups) {
    setup.load(includeSize ? [...marginFields, 'pageWidth', 'pageHeight'] : marginFields);
  }
  await context.sync();
  return setups;
}

function readSetupMargins(setup) {
  return Object.fromEntries(PAGE_MARGIN_SIDES.map(side => [side, setup[fields[side]]]));
}

export async function readPageMargins(context) {
  try {
    if (!supportsPageSetup()) return null;
    const setups = await loadPageSetups(context);
    return summarizePageMargins(setups.map(readSetupMargins));
  } catch {
    return null;
  }
}

let adjusting = false;

export async function adjustPageMargins(pageMarginsCm) {
  if (!supportsPageSetup()) throw new Error('当前 Word 不支持修改页边距，需要 WordApiDesktop 1.3。');
  if (adjusting) throw new Error('正在调整页边距，请等待当前操作完成。');
  adjusting = true;
  try {
    return await Word.run(async context => {
      const setups = await loadPageSetups(context, true);
      const changes = planPageMargins(setups.map(setup => ({
        setup, margins: readSetupMargins(setup), width: setup.pageWidth, height: setup.pageHeight
      })), pageMarginsCm);
      if (!changes.length) return { success: true, pageMarginsCm: summarizePageMargins(setups.map(readSetupMargins)) };

      const refresh = async () => {
        for (const setup of setups) setup.load(marginFields);
        await context.sync();
      };
      const getValue = ({ setup, side }) => setup[fields[side]];
      try {
        for (const { setup, side, after } of changes) setup[fields[side]] = after;
        await refresh();
        assertAppliedMargins(changes, getValue);
        return { success: true, pageMarginsCm: summarizePageMargins(setups.map(readSetupMargins)) };
      } catch (error) {
        try {
          await refresh();
          for (const change of changes.reverse()) {
            if (getValue(change) !== change.before) change.setup[fields[change.side]] = change.before;
          }
          await refresh();
          assertAppliedMargins(changes, getValue, 'before');
        } catch {
          return { success: null, requiresRead: true, error: `修改页边距失败，未能确认恢复原值：${error.message}` };
        }
        throw error;
      }
    });
  } finally {
    adjusting = false;
  }
}
