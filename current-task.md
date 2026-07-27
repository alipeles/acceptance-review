# Task
Produce the §16 CLI output — obligation coverage, test evidence with per-line evidence tier tags, unrequested changes, and a recommended-next-instruction pointer. The `check` command must run the full assembled review pipeline so the report reflects everything the checker computes.

## Constraints
- One shared pipeline serves both the CLI and the benchmark. Previously every capability from test discovery onward reached only the benchmark path, so the command used to dogfood the tool ran an older, shorter chain and could not show test evidence or a verdict at all; sharing one function keeps the two consumers identical by construction.
- Implementation coverage and test evidence are two distinct axes and render as separate sections: coverage answers whether the code responds to an obligation, evidence answers whether the tests discriminate.
- Every test-evidence line shows its evidence tier, so a static inference is never presented as execution-confirmed.
- The headline verdict is the computed completion result; a review with no computed verdict renders as indeterminate rather than assumed good.
- Unrequested changes render as advisory, each showing its disposition.

## Completion expectations
- Implementation
- Rendered output matches the §16 layout, with every test-evidence line showing its evidence tier.
- The benchmark and the CLI produce their reviews from the same pipeline function.
- `check` accepts an optional builder declaration and reviews the working tree when no head revision is given.
