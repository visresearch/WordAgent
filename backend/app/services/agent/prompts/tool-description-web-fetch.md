Fetch a webpage and extract its primary readable text content.

## Parameters:
- `url` (str): absolute URL including protocol (for example `https://example.com/page`).

## When to use:
- User provides a concrete webpage URL and asks for page-specific evidence.
- Need to read article/page details that are not in current document context.

## When not to use:
- No URL is provided.
- Question can be answered fully from current document or existing context.

## Returns:
- `str`: extracted page text (or error text on failure).

## Examples (scenarios):
- User says: “请根据这篇官方博客总结关键变更”，并附带 URL -> call `web_fetch` to pull the page content first.
- User asks generic writing optimization without URL -> do not call `web_fetch`.