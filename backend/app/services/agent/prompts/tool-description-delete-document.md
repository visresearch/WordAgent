Delete a paragraph range from the active Word document.

## Parameters:
- `startParaIndex` (int): 0-based inclusive start paragraph index. Default: `0`.
- `endParaIndex` (int): 0-based inclusive end paragraph index. Default: `-1` (end of document).

## When to use:
- User explicitly requests deleting existing content.
- Prepare a replacement rewrite at the same position.
- Multi-step rewrite flows where frontend may defer actual deletion confirmation to a final global confirm action.

## When not to use:
- User asks to append/add content only.
- You only need analysis without editing.

## Returns:
- `str`: confirmation text indicating the frontend received the request.

## Execution note:
- This tool is non-blocking from agent perspective.
- After calling `delete_document`, do not wait for per-operation confirmation; continue subsequent tool calls (such as `generate_document`) in the same agent run.
- Frontend may allow users to confirm all pending deletes in one final action after the agent finishes.

## Examples (scenarios):
- User says: “删除目录后面的空白段落” -> call `delete_document` on the target range.
- User says: “重写这几段” -> call `delete_document` first, then `generate_document` with replacement content.
- User performs deferred confirmation workflow -> still complete all planned generation steps before ending the agent turn.