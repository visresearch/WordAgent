/**
 * 文档搜索引擎 - Query DSL 执行器
 * 
 * 类似 Elasticsearch Query DSL 的文档搜索功能
 * 用于在全文 JSON 中定位需要修改的段落
 * 
 * 使用方式：
 * import { executeQuery, generateSummary } from './documentSearch.js'
 * 
 * const result = executeQuery(docJson, {
 *   query: { match: { field: "text", query: "公司" } },
 *   context: 1
 * })
 */

import { PSTYLE, RSTYLE } from './docxJsonConverter.js';

// ============== Query 执行器 ==============

/**
 * 执行 Query DSL 查询
 * @param {Object} docJson - 完整文档 JSON
 * @param {Object} queryDSL - Query DSL 对象
 * @returns {Object} 查询结果
 */
export function executeQuery(docJson, queryDSL) {
  const paragraphs = docJson.paragraphs || [];
  const { query, context = 1, highlight = true, size = 50 } = queryDSL;
  
  if (!paragraphs.length) {
    return { found: false, matchedIndices: [], paragraphs: [], total: 0 };
  }
  
  // 执行查询，获取匹配的索引
  const matchedIndices = executeQueryClause(paragraphs, query);
  
  // 限制数量
  const limitedIndices = matchedIndices.slice(0, size);
  
  // 扩展上下文
  const expandedIndices = expandContext(limitedIndices, paragraphs.length, context);
  
  // 提取匹配的段落（带元信息）
  const matchedParagraphs = extractParagraphs(paragraphs, expandedIndices, limitedIndices, query, highlight);
  
  return {
    found: matchedParagraphs.length > 0,
    matchedIndices: limitedIndices,
    matchedCount: limitedIndices.length,
    totalParagraphs: paragraphs.length,
    paragraphs: matchedParagraphs,
    query: queryDSL  // 返回原查询，便于调试
  };
}

/**
 * 执行查询子句
 * @param {Array} paragraphs - 段落数组
 * @param {Object} clause - 查询子句
 * @returns {Array} 匹配的索引数组
 */
function executeQueryClause(paragraphs, clause) {
  if (!clause) {
    return [];
  }
  
  // Bool 查询
  if (clause.must || clause.should || clause.must_not) {
    return executeBoolQuery(paragraphs, clause);
  }
  
  // Match 查询
  if (clause.match) {
    return executeMatchQuery(paragraphs, clause.match);
  }
  
  // Range 查询
  if (clause.range) {
    return executeRangeQuery(paragraphs, clause.range);
  }
  
  // Term 查询
  if (clause.term) {
    return executeTermQuery(paragraphs, clause.term);
  }
  
  // Match All
  if (clause.match_all !== undefined) {
    return paragraphs.map((_, i) => i);
  }
  
  return [];
}

/**
 * 执行 Bool 查询
 */
function executeBoolQuery(paragraphs, bool) {
  const { must = [], should = [], must_not = [], minimum_should_match = 1 } = bool;
  
  // 初始化：所有段落都是候选
  let candidates = new Set(paragraphs.map((_, i) => i));
  
  // 处理 must - 交集
  for (const clause of must) {
    const matches = new Set(executeQueryClause(paragraphs, clause));
    candidates = new Set([...candidates].filter(i => matches.has(i)));
  }
  
  // 处理 must_not - 排除
  for (const clause of must_not) {
    const matches = new Set(executeQueryClause(paragraphs, clause));
    candidates = new Set([...candidates].filter(i => !matches.has(i)));
  }
  
  // 处理 should - 至少匹配 N 个
  if (should.length > 0) {
    const shouldMatches = should.map(clause => 
      new Set(executeQueryClause(paragraphs, clause))
    );
    
    candidates = new Set([...candidates].filter(i => {
      const matchCount = shouldMatches.filter(set => set.has(i)).length;
      return matchCount >= minimum_should_match;
    }));
  }
  
  return [...candidates].sort((a, b) => a - b);
}

/**
 * 执行 Match 查询
 */
function executeMatchQuery(paragraphs, match) {
  const { field = 'text', query, fuzzy = false } = match;
  const matches = [];
  
  paragraphs.forEach((para, index) => {
    const fieldValue = getFieldValue(para, field);
    if (fieldValue === null) {
      return;
    }
    
    const haystack = String(fieldValue).toLowerCase();
    const needle = String(query).toLowerCase();
    
    if (fuzzy) {
      // 模糊匹配：检查是否包含部分关键词
      const keywords = needle.split(/\s+/);
      if (keywords.some(kw => haystack.includes(kw))) {
        matches.push(index);
      }
    } else {
      // 精确包含
      if (haystack.includes(needle)) {
        matches.push(index);
      }
    }
  });
  
  return matches;
}

/**
 * 执行 Range 查询
 */
function executeRangeQuery(paragraphs, range) {
  const { field = 'index', gte, lte, gt, lt } = range;
  const matches = [];
  const total = paragraphs.length;
  
  paragraphs.forEach((para, index) => {
    let value;
    
    if (field === 'index') {
      value = index;
    } else if (field === 'position') {
      value = para.position || 0;
    } else {
      return;
    }
    
    // 处理负数索引（倒数）
    const normalizeIndex = (val) => {
      if (val === undefined || val === null) {
        return null;
      }
      return val < 0 ? total + val : val;
    };
    
    const normalizedGte = normalizeIndex(gte);
    const normalizedLte = normalizeIndex(lte);
    const normalizedGt = normalizeIndex(gt);
    const normalizedLt = normalizeIndex(lt);
    
    let pass = true;
    if (normalizedGte !== null && value < normalizedGte) {
      pass = false;
    }
    if (normalizedLte !== null && value > normalizedLte) {
      pass = false;
    }
    if (normalizedGt !== null && value <= normalizedGt) {
      pass = false;
    }
    if (normalizedLt !== null && value >= normalizedLt) {
      pass = false;
    }
    
    if (pass) {
      matches.push(index);
    }
  });
  
  return matches;
}

/**
 * 执行 Term 查询
 */
function executeTermQuery(paragraphs, term) {
  const { field, value } = term;
  const matches = [];
  
  paragraphs.forEach((para, index) => {
    let fieldValue;
    
    switch (field) {
      case 'isEmpty':
        fieldValue = para.isEmpty || (!para.text && (!para.runs || para.runs.length === 0));
        break;
      case 'isHeading':
        const styleName = para.pStyle?.[PSTYLE.STYLE_NAME] || '';
        fieldValue = styleName.includes('标题') || styleName.toLowerCase().includes('heading');
        break;
      case 'isBold':
        fieldValue = para.runs?.some(run => run.rStyle?.[RSTYLE.BOLD]) || false;
        break;
      case 'hasHighlight':
        fieldValue = para.runs?.some(run => run.rStyle?.[RSTYLE.HIGHLIGHT] > 0) || false;
        break;
      default:
        return;
    }
    
    if (fieldValue === value) {
      matches.push(index);
    }
  });
  
  return matches;
}

/**
 * 获取段落字段值
 */
function getFieldValue(para, field) {
  switch (field) {
    case 'text':
      return para.text || para.runs?.map(r => r.text).join('') || '';
    case 'styleName':
      return para.pStyle?.[PSTYLE.STYLE_NAME] || '';
    case 'fontName':
      return para.runs?.[0]?.rStyle?.[RSTYLE.FONT_NAME] || '';
    default:
      return null;
  }
}

/**
 * 扩展上下文
 */
function expandContext(indices, total, context) {
  const expanded = new Set();
  
  for (const idx of indices) {
    for (let i = Math.max(0, idx - context); i <= Math.min(total - 1, idx + context); i++) {
      expanded.add(i);
    }
  }
  
  return [...expanded].sort((a, b) => a - b);
}

/**
 * 提取段落并标记
 */
function extractParagraphs(paragraphs, expandedIndices, matchedIndices, query, highlight) {
  const matchedSet = new Set(matchedIndices);
  
  return expandedIndices.map(idx => {
    const para = paragraphs[idx];
    const isTarget = matchedSet.has(idx);
    
    // 获取匹配关键词（用于高亮）
    let highlightKeywords = [];
    if (highlight && isTarget && query?.match?.query) {
      highlightKeywords = [query.match.query];
    }
    
    return {
      index: idx,
      isTarget,  // 是否是目标段落（vs 上下文段落）
      highlightKeywords,
      ...para
    };
  });
}

// ============== 文档摘要生成 ==============

/**
 * 生成文档摘要（用于发送给定位 Agent）
 * 摘要很小，可以安全地发送给 LLM
 * 
 * @param {Object} docJson - 完整文档 JSON
 * @returns {Object} 文档摘要
 */
export function generateSummary(docJson) {
  const paragraphs = docJson.paragraphs || [];
  const tables = docJson.tables || [];
  
  // 提取所有标题
  const headings = [];
  paragraphs.forEach((para, index) => {
    const styleName = para.pStyle?.[PSTYLE.STYLE_NAME] || '';
    const text = getFieldValue(para, 'text').substring(0, 80);
    
    if (styleName.includes('标题') || styleName.toLowerCase().includes('heading')) {
      headings.push({ 
        index, 
        level: styleName.match(/\d/) ? parseInt(styleName.match(/\d/)[0]) : 1,
        text: text.trim()
      });
    }
  });
  
  // 提取首尾段落预览
  const firstPara = getFieldValue(paragraphs[0] || {}, 'text').substring(0, 100);
  const lastPara = getFieldValue(paragraphs[paragraphs.length - 1] || {}, 'text').substring(0, 100);
  
  // 统计格式特征
  let highlightCount = 0;
  let boldCount = 0;
  paragraphs.forEach(para => {
    if (para.runs?.some(r => r.rStyle?.[RSTYLE.HIGHLIGHT] > 0)) {
      highlightCount++;
    }
    if (para.runs?.some(r => r.rStyle?.[RSTYLE.BOLD])) {
      boldCount++;
    }
  });
  
  return {
    paragraphCount: paragraphs.length,
    tableCount: tables.length,
    headings,
    firstParagraph: firstPara,
    lastParagraph: lastPara,
    stats: {
      highlightCount,
      boldCount,
      headingCount: headings.length
    }
  };
}

// ============== 导出 ==============

export default {
  executeQuery,
  generateSummary
};
