# Judgement — #43 Gate 2, run 2

**Not clean.** `Task completion: INCOMPLETE`, 9 obligations with
non-discriminating test evidence, 9 recommended tests, 0 unjudged pairs.

**Command:** `.venv/bin/acceptance check --task current-task.md --base a520d67 --head 6639e3c --mode record --continue d9d9082200406840`
**Run id:** `9c7c98188e9d21ff`, continuing `d9d9082200406840`
**Cost:** $0.4618 on 62 live calls.

The full triage of all three Gate 2 runs is in `43-gate2-run3/judgement.md`. This
file records only what is specific to run 2.

## Two recommendations named real gaps, and both were fixed

1. **`socket.socket.connect` and `connect_ex` had no test.** The earlier tests
   went only through `create_connection` and `getaddrinfo`, so half the network
   block was unevidenced. The report's stated reason was inverted — it claimed
   `_ALLOWED_FAMILIES` leaves IPv4 unblocked, when an `AF_INET` socket is
   precisely what is *not* in that set — but the gap it pointed at was real.
   Worth recording: a finding whose reasoning is wrong can still be worth acting
   on, and the two judgements are separate.
2. **The per-test budget was silently skipped where `signal.setitimer` is
   absent**, producing a result that looks time-bounded and is not. It now
   declines the run instead, which is the direction DR-170 Decision 1's cost
   asymmetry argues for.

Fixing (1) also exposed that the `AF_UNIX` allowance had no test either. Without
one, tightening the block to refuse everything would have looked like an
improvement.

## The unjudged pairs did not recur

Run 1 left 20 pairs unjudged, all against one test. Run 2 left none, with that
test still in the candidate set. Intermittent, not deterministic.
