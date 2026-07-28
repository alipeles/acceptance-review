# Task
Produce the §16 CLI output — a per-obligation report where each obligation carries its own code evidence and test evidence, plus unrequested changes and a recommended-next-instruction pointer. The `check` command must run the full assembled review pipeline so the report reflects everything the checker computes.

## Constraints
- One shared pipeline function serves both the CLI and the benchmark. Previously every capability from test discovery onward reached only the benchmark path, so the command used to dogfood the tool ran an older, shorter chain and could not show test evidence or a verdict at all; sharing one function keeps the two consumers identical by construction.
- The report is organized by obligation: each obligation is a block carrying both of its evidence axes beneath it, rather than two separate lists the reader must join by eye. Code evidence answers whether the code responds to the obligation; test evidence answers whether the tests discriminate.
- Every test-evidence line shows its evidence tier, so a static inference is never presented as execution-confirmed.
- Status is stated in words rather than symbols, and obligations, evidence items, findings, questions and recommendations are numbered so a reader can refer to any one of them precisely.
- A test citation names the specific test, not merely the file that contains it. A code citation names the specific changed region.
- An obligation records the code regions that satisfy it whatever its status, so the report can say where an obligation was satisfied and not merely that it was.
- The headline verdict is the computed completion result; a review with no computed verdict renders as indeterminate rather than assumed good.
- Unrequested changes render as advisory, each showing its disposition.

## Completion expectations
- Implementation
- Rendered output matches the §16 layout, with every test-evidence line showing its evidence tier.
- The benchmark and the CLI produce their reviews from the same pipeline function.
- `check` accepts an optional builder declaration and reviews the working tree when no head revision is given.
