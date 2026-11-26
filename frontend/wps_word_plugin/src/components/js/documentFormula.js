import { latexToOmml, ommlToLatex } from '@quirekit/math-omml';
import { strFromU8, strToU8, unzipSync, zipSync } from 'fflate';

const MATH_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math';
const WORD_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
const DOCUMENT_PART = 'word/document.xml';
const DOCUMENT_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml';
const RELATIONSHIPS = `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="${DOCUMENT_PART}"/>
</Relationships>`;

export function prepareFormula(run) {
  if (run?.formulaError != null) {
    throw new Error('无法写回读取失败的公式，请先提供正确的 LaTeX');
  }
  if (run?.formula == null) {
    return null;
  }
  if (typeof run.formula !== 'string' || run.text != null || run.url != null) {
    throw new Error('公式 run 必须提供 LaTeX 字符串 formula，且不能同时提供 text 或 url');
  }

  const latex = run.formula.trim().replace(
    /^\$\$([\s\S]*?)\$\$$|^\$([\s\S]*?)\$$|^\\\(([\s\S]*?)\\\)$|^\\\[([\s\S]*?)\\\]$/,
    '$1$2$3$4'
  ).trim();
  if (!latex) {
    throw new Error('formula 不能为空');
  }
  const result = latexToOmml(latex);
  if (!result.ok) {
    throw new Error(`无法转换 LaTeX 公式（位置 ${result.diagnostic.offset + 1}）：${result.diagnostic.message}`);
  }
  // Spacing approximations do not change the meaning of the formula.
  const unsupported = result.losses.filter(loss => loss !== 'negative-space');
  if (unsupported.length) {
    throw new Error(`公式包含无法写入 WPS 的 LaTeX 结构：${unsupported.join('、')}`);
  }

  const documentXml = `<w:document xmlns:w="${WORD_NS}"><w:body><w:p>${result.xml}</w:p></w:body></w:document>`;
  const flatPackage = `<pkg:package xmlns:pkg="http://schemas.microsoft.com/office/2006/xmlPackage">
<pkg:part pkg:name="/_rels/.rels" pkg:contentType="application/vnd.openxmlformats-package.relationships+xml">
<pkg:xmlData>${RELATIONSHIPS}</pkg:xmlData></pkg:part>
<pkg:part pkg:name="/${DOCUMENT_PART}" pkg:contentType="${DOCUMENT_TYPE}">
<pkg:xmlData>${documentXml}</pkg:xmlData>
</pkg:part></pkg:package>`;
  return { documentXml, flatPackage };
}

function wpsFileAccess() {
  const app = globalThis.Application || globalThis.wps;
  return app?.FileSystem && app?.Env?.GetTempPath ? app : null;
}

function withTemporaryDocx(app, operation) {
  const directory = app.Env.GetTempPath().replace(/[\\/]+$/, '');
  const name = `wence-formula-${Date.now()}-${Math.random().toString(36).slice(2)}.docx`;
  const path = `${directory}/${name}`;
  try {
    return operation(app.FileSystem, path);
  } finally {
    try { app.FileSystem.unlinkSync(path); } catch (error) { /* Already removed or never written. */ }
  }
}

export function canInsertFormula(range) {
  return typeof range.InsertXML === 'function' || (typeof range.InsertFile === 'function' && !!wpsFileAccess());
}

export function insertFormula(doc, position, formula) {
  // Always insert into a collapsed range so a failed import cannot consume existing content.
  const endBefore = doc.Content.End;
  const attempt = (insert) => {
    try {
      insert(doc.Range(position, position));
      const end = position + doc.Content.End - endBefore;
      const maths = end > position && doc.Range(position, end).OMaths;
      if (maths?.Count === 1) {
        const mathRange = maths.Item(1).Range;
        if (mathRange.Start === position && mathRange.End === end) return end;
        // A WPS release may import the fragment's enclosing paragraph mark too.
        if (mathRange.Start === position && mathRange.End === end - 1 && doc.Range(end - 1, end).Text === '\r') {
          doc.Range(end - 1, end).Delete();
          if (doc.Content.End === endBefore + end - position - 1) return end - 1;
        }
      }
    } catch (error) {
      // Check the actual edit below even if the automation method threw.
    }
    const added = doc.Content.End - endBefore;
    if (added > 0) {
      doc.Range(position, position + added).Delete();
      if (doc.Content.End !== endBefore) throw new Error('WPS 无法回退未完成的公式插入，请重新读取文档');
    }
    return null;
  };

  const range = doc.Range(position, position);
  if (typeof range.InsertXML === 'function') {
    const end = attempt(target => target.InsertXML(formula.flatPackage));
    if (end !== null) return end;
  }

  const app = wpsFileAccess();
  if (app && typeof range.InsertFile === 'function') {
    const end = withTemporaryDocx(app, (fs, path) => {
      const docx = zipSync({
        '[Content_Types].xml': strToU8(`<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Override PartName="/${DOCUMENT_PART}" ContentType="${DOCUMENT_TYPE}"/>
</Types>`),
        '_rels/.rels': strToU8(RELATIONSHIPS),
        [DOCUMENT_PART]: strToU8(formula.documentXml)
      });
      const binary = strFromU8(docx, true);
      if (fs.writeAsBinaryString(path, binary) === false) throw new Error('WPS 无法创建临时公式文档');
      return attempt(target => target.InsertFile(path));
    });
    if (end !== null) return end;
  }
  throw new Error('WPS 未能插入原生公式，请确认文档格式和客户端版本支持公式');
}

function toOmmlElement(element) {
  const name = (node) => {
    if (node.namespaceURI === MATH_NS) return `m:${node.localName}`;
    if (node.namespaceURI === WORD_NS) return `w:${node.localName}`;
    return node.nodeName;
  };
  const children = [];
  for (const child of Array.from(element.childNodes)) {
    if (child.nodeType === 1) {
      if (child.namespaceURI === WORD_NS && child.localName === 'del') continue;
      const value = toOmmlElement(child);
      if (child.namespaceURI === WORD_NS && child.localName === 'ins') {
        children.push(...value['w:ins']);
      } else {
        children.push(value);
      }
    } else if ((child.nodeType === 3 || child.nodeType === 4) && element.localName === 't') {
      children.push({ '#text': child.nodeValue });
    }
  }
  const attributes = Object.fromEntries(
    Array.from(element.attributes)
      .filter(attribute => attribute.namespaceURI !== 'http://www.w3.org/2000/xmlns/')
      .map(attribute => [`@_${name(attribute)}`, attribute.value])
  );
  const result = { [name(element)]: children };
  if (Object.keys(attributes).length) result[':@'] = attributes;
  return result;
}

function parseOmml(xml) {
  if (typeof xml !== 'string' || !xml.includes('oMath')) return [];
  const parsed = new DOMParser().parseFromString(xml, 'application/xml');
  return Array.from(parsed.getElementsByTagNameNS(MATH_NS, 'oMath')).filter(equation => {
    for (let parent = equation.parentElement; parent; parent = parent.parentElement) {
      if (parent.namespaceURI === WORD_NS && parent.localName === 'del') return false;
    }
    return true;
  });
}

function readOmml(range) {
  let xml;
  try {
    xml = range.WordOpenXML;
  } catch (error) {
    xml = null;
  }
  const equations = parseOmml(xml);
  if (equations.length || typeof range.XML !== 'function') return equations;
  try {
    return parseOmml(range.XML(false));
  } catch (error) {
    return [];
  }
}

function exportOmml(range) {
  const app = wpsFileAccess();
  if (!app || typeof range.ExportFragment !== 'function') return [];
  return withTemporaryDocx(app, (fs, path) => {
    range.ExportFragment(path, 12); // wdFormatXMLDocument (.docx)
    const archive = new Uint8Array(fs.ReadFileAsArrayBuffer(path));
    const document = unzipSync(archive, { filter: file => file.name === DOCUMENT_PART })[DOCUMENT_PART];
    return document ? parseOmml(strFromU8(document)) : [];
  });
}

export function readFormulaRanges(range) {
  let maths;
  let count;
  try {
    maths = range?.OMaths;
    count = maths?.Count || 0;
  } catch (error) {
    return [];
  }

  let paragraphOmml;
  const formulas = [];
  for (let index = 1; index <= count; index += 1) {
    let mathRange;
    let start;
    let end;
    try {
      mathRange = maths.Item(index).Range;
      start = mathRange.Start;
      end = mathRange.End;
    } catch (error) {
      continue;
    }
    if (!Number.isInteger(start) || !Number.isInteger(end) || end <= start) continue;

    let run;
    try {
      const local = readOmml(mathRange);
      let element = local.length === 1 ? local[0] : null;
      if (!element) {
        paragraphOmml ??= readOmml(range);
        const exported = paragraphOmml.length === count ? [paragraphOmml[index - 1]] : exportOmml(mathRange);
        if (exported.length === 1) element = exported[0];
      }
      if (element) {
        const result = ommlToLatex(toOmmlElement(element));
        run = result.ok ? { formula: result.latex } : { formulaError: result.reason };
      } else {
        run = { formulaError: 'WPS 未返回此原生公式的 OMML 结构' };
      }
    } catch (error) {
      run = { formulaError: '读取原生公式失败：' + error.message };
    }
    formulas.push({ start, end, run });
  }
  return formulas.sort((left, right) => left.start - right.start);
}
