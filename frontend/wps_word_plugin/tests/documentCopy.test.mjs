import assert from 'node:assert/strict';
import test from 'node:test';
import { copyDocument } from '../src/components/js/documentCopy.js';

function collection(items) {
  return { get Count() { return items.length; }, Item: index => items[index - 1] };
}

function paragraph(ParaID, Start, End) {
  return { ParaID, Range: { Start, End } };
}

function copyFixture(t, blankTarget = false) {
  const sourceParagraphs = [paragraph(91, 0, 5), paragraph(40, 5, 8), paragraph(-14, 8, 12), paragraph(9, 13, 19)];
  const table = { Range: { Start: 5, End: 13, Paragraphs: collection(sourceParagraphs.slice(1, 3)) } };
  const formatted = { Start: 5, End: 13 };
  const sourceReads = [];
  const source = {
    DocID: -9,
    Paragraphs: collection(sourceParagraphs),
    Content: { Start: 0, End: 19, Tables: collection([table]) },
    Range(start, end) {
      sourceReads.push([start, end]);
      return { FormattedText: formatted };
    }
  };
  const targetParagraphs = blankTarget ? [paragraph(7, 0, 1)] : [paragraph(7, 0, 5), paragraph(8, 5, 10)];
  const content = { Start: 0, End: blankTarget ? 1 : 10, Text: blankTarget ? '\r' : 'left\rright\r', Tables: collection([]) };
  const revisions = [];
  const writes = [];
  const application = { UserName: 'Editor', Options: { UseLocalUserInfo: false }, ScreenUpdating: true, ActiveDocument: source };
  const target = {
    DocID: 17, Name: '目标.docx', Application: application, TrackRevisions: false,
    Content: content, Paragraphs: collection(targetParagraphs), Revisions: collection(revisions),
    Range(start, end) {
      return {
        Information: kind => kind === 12 ? false : 1,
        set FormattedText(value) {
          writes.push([start, end, value]);
          assert.equal(target.TrackRevisions, true);
          const length = value.End - value.Start;
          if (blankTarget) targetParagraphs.splice(0, 1);
          const next = targetParagraphs.findIndex(item => item.Range.Start >= start);
          for (const { Range: range } of targetParagraphs) {
            if (range.Start >= start) {
              range.Start += length;
              range.End += length;
            }
          }
          targetParagraphs.splice(next < 0 ? targetParagraphs.length : next, 0, paragraph(20, start, start + length));
          content.End += length - (end - start);
          revisions.push({ Author: application.UserName, Type: 1, Range: { Start: start, End: start + length, Text: 'copied' } });
        }
      };
    }
  };
  application.Documents = collection([source, target]);
  const previousWindow = globalThis.window;
  globalThis.window = { Application: application };
  t.after(() => { globalThis.window = previousWindow; });
  return {
    request: { sourceDocID: -9, start_paraID: 40, end_paraID: -14, targetDocID: 17, insertID: blankTarget ? 0 : 7 },
    sourceReads, writes, targetParagraphs, formatted, application
  };
}

test('copies a complete table by native range into the specified WPS document after the target ID', t => {
  const fixture = copyFixture(t);
  const result = copyDocument(fixture.request, () => true);
  assert.deepEqual(fixture.sourceReads, [[5, 13]]);
  assert.equal(fixture.writes[0][2], fixture.formatted);
  assert.deepEqual(fixture.writes[0].slice(0, 2), [5, 5]);
  assert.deepEqual(fixture.targetParagraphs.map(item => item.ParaID), [7, 20, 8]);
  assert.deepEqual(result, {
    documentId: 17, documentName: '目标.docx', revisionCount: 1,
    lastParagraph: { paraID: 20, paraIndex: 1, pageStart: 1, pageEnd: 1 }
  });
  assert.equal(fixture.application.UserName, 'Editor');
});

test('inserting at the beginning of a blank WPS document consumes its empty placeholder', t => {
  const fixture = copyFixture(t, true);
  const result = copyDocument(fixture.request, () => true);
  assert.deepEqual(fixture.writes[0].slice(0, 2), [0, 1]);
  assert.deepEqual(fixture.targetParagraphs.map(item => item.ParaID), [20]);
  assert.equal(result.lastParagraph.paraIndex, 0);
});

test('inserting at the beginning preserves the first paragraph of a nonempty WPS document', t => {
  const fixture = copyFixture(t);
  copyDocument({ ...fixture.request, insertID: 0 }, () => true);
  assert.deepEqual(fixture.writes[0].slice(0, 2), [0, 0]);
  assert.deepEqual(fixture.targetParagraphs.map(item => item.ParaID), [20, 7, 8]);
});

test('rejects reversed IDs, partial tables and unknown target anchors before writing', t => {
  const fixture = copyFixture(t);
  assert.throws(() => copyDocument({ ...fixture.request, start_paraID: -14, end_paraID: 40 }, () => true), /结束段落/);
  assert.throws(() => copyDocument({ ...fixture.request, end_paraID: 40 }, () => true), /部分表格/);
  assert.throws(() => copyDocument({ ...fixture.request, insertID: 600 }, () => true), /插入锚点/);
  assert.deepEqual(fixture.writes, []);
});
