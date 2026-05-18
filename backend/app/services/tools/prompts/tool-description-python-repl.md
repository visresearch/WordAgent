Execute short Python snippets in an isolated REPL for calculations or lightweight data transforms.

## Parameters
- `query` (string): Python code to execute.

## When to use
- Quick deterministic calculations.
- Small data transformations needed for reasoning.

## Returns
- The REPL output (stdout or last expression value).

## Safety
- Keep code short and side-effect free unless explicitly required.
- Avoid long-running tasks, network access, or filesystem writes.
