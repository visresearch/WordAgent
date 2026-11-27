export const PAGE_MARGIN_SIDES = ['top', 'bottom', 'left', 'right'];
const POINTS_PER_CM = 72 / 2.54;

export function summarizePageMargins(sections) {
  if (!sections.length || sections.some(section => PAGE_MARGIN_SIDES.some(side => !Number.isFinite(section[side])))) {
    return null;
  }
  return Object.fromEntries(PAGE_MARGIN_SIDES.map(side => {
    const values = sections.map(section => Number((section[side] / POINTS_PER_CM).toFixed(2)));
    return [side, values.every(value => value === values[0]) ? values[0] : null];
  }));
}

export function planPageMargins(sections, pageMarginsCm) {
  const requested = Object.entries(pageMarginsCm || {}).filter(([, value]) => value != null);
  if (!requested.length || requested.some(([side, value]) =>
    !PAGE_MARGIN_SIDES.includes(side) || !Number.isFinite(value) || value < 0
  )) {
    throw new Error('请至少提供一个有效的页边距，单位为厘米，数值必须大于或等于 0。');
  }

  return sections.flatMap(({ setup, margins, width, height }, index) => {
    const changes = requested.map(([side, value]) => ({
      setup, side, before: margins[side], after: value * POINTS_PER_CM
    }));
    const target = { ...margins, ...Object.fromEntries(changes.map(({ side, after }) => [side, after])) };
    if (![width, height, ...Object.values(margins)].every(Number.isFinite)) {
      throw new Error(`无法读取第 ${index + 1} 节的纸张尺寸或页边距。`);
    }
    if (target.left + target.right >= width || target.top + target.bottom >= height) {
      throw new Error(`第 ${index + 1} 节设置后的页边距超过纸张可用范围。`);
    }
    // Reduce margins first, in case a host enforces the paper limits on each assignment.
    return changes.filter(({ before, after }) => Math.abs(before - after) > 0.025)
      .sort((a, b) => (a.after - a.before) - (b.after - b.before));
  });
}

export function assertAppliedMargins(changes, getValue, key = 'after') {
  // Word formats page dimensions in twips (1/20 of a point).
  if (changes.some(change => {
    const actual = getValue(change);
    return !Number.isFinite(actual) || Math.abs(actual - change[key]) > 0.05;
  })) {
    throw new Error('宿主返回的实际页边距与设置值不一致。');
  }
}
