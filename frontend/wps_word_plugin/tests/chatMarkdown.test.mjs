import assert from 'node:assert/strict';
import test from 'node:test';
import { katex } from '@mdit/plugin-katex';
import MarkdownIt from 'markdown-it';
import { createChatMarkdownRenderer } from '../../shared/js/chatMarkdown.mjs';

const renderMarkdown = createChatMarkdownRenderer(MarkdownIt, katex);
const fourier = String.raw`\hat f(\omega)=\int_{-\infty}^{\infty} f(t)e^{-\mathrm{i}\omega t}\,\mathrm{d}t`;

test('renders a display equation and inline math next to Chinese characters', () => {
  const html = renderMarkdown(['傅里叶变换公式：', '\\[', fourier, '\\]', '其中$\\omega$是角频率。'].join('\r\n'));

  assert.match(html, /<p class=['"]katex-block['"]><span class="katex-display">/);
  assert.match(html, /<mo>∫<\/mo>/);
  assert.match(html, /其中<span class="katex">/);
  assert.match(html, /<\/span>是角频率。/);
  assert.doesNotMatch(html, /class="katex-error"/);
});

test('renders dollar blocks and LaTeX parentheses', () => {
  const html = renderMarkdown(String.raw`$$\frac{1}{2}$$

设\(x^2=4\)成立。`);

  assert.match(html, /class="katex-display"/);
  assert.match(html, /<mfrac>/);
  assert.match(html, /设<span class="katex">/);
});

test('a bracket formula renders once a streamed closing delimiter arrives', () => {
  const partial = `\\[\n${fourier}\n`;
  assert.doesNotMatch(renderMarkdown(partial), /class="katex-display"/);
  assert.match(renderMarkdown(`${partial}\\]`), /class="katex-display"/);
});

test('keeps code, currency and escaped math delimiters literal', () => {
  const html = renderMarkdown('`$x^2$`\n\n```latex\n\\[x^2\\]\n```\n\n$20到$30\n\n\\$x$');

  assert.match(html, /<code>\$x\^2\$<\/code>/);
  assert.match(html, /<pre><code class="language-latex">\\\[x\^2\\\]/);
  assert.match(html, /<p>\$20到\$30<\/p>/);
  assert.match(html, /<p>\$x\$<\/p>/);
  assert.doesNotMatch(html, /class="katex/);
});

test('invalid math shows a fallback and LaTeX cannot add links or images', () => {
  const html = renderMarkdown(String.raw`$\frac{$ 后面仍有正文。 $\href{https://example.com}{x}$ $\includegraphics{https://example.com/pixel.png}$`);

  assert.match(html, /katex-error/);
  assert.match(html, /后面仍有正文。/);
  assert.doesNotMatch(html, /<a\b|<img\b/);
});
