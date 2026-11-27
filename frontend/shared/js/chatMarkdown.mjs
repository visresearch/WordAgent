export function createChatMarkdownRenderer(MarkdownIt, katex) {
  const markdown = new MarkdownIt({
    html: false,
    breaks: true,
    linkify: true,
    typographer: true
  }).use(katex, {
    delimiters: 'all',
    throwOnError: false,
    trust: false
  });

  return (content) => content ? markdown.render(String(content)) : '';
}
