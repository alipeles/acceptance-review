# Judgement — #43 Gate 2, run 3

**Gate 2 does not pass, and I do not believe it can pass for this task.**

**Command:** `.venv/bin/acceptance check --task current-task.md --base a520d67 --head f1dff85 --mode record --continue 9c7c98188e9d21ff`
**Run id:** `d00123128b5c7539`, continuing `9c7c98188e9d21ff`
**Cost:** $0.3420 on 47 live calls. Three Gate 2 runs cost $1.32 in total.

## Result

`Task completion: INCOMPLETE`. Eight obligations with non-discriminating test
evidence, eight recommended tests, no unjudged pairs, four unrequested changes
all dispositioned `in_service`.

The three runs moved 11 → 9 → 8 obligations. Every step came from a real fix, and
the remaining eight do not look reachable by more of the same.

## Why more rounds will not reach clean

Three of the eight remaining recommendations restate one limit that is real,
documented, and unkillable by any test: **the network block is at the Python
socket layer, not the operating system's.** A C extension that opens a socket
without going through `socket` is not caught. There is no portable way to get an
operating-system network namespace on macOS without privileges, so that defect
stays enumerated and unkilled, and `network-access-blocked-for-tests` therefore
cannot be strongly supported. The gate requires every obligation strongly
supported. That is a structural stop, not a shortfall in effort.

Three more are factually wrong about the code, which I verified by reading it:

| the report says | what the code does |
|---|---|
| "`_ALLOWED_FAMILIES` includes `AF_UNIX`; a test reaching a service over loopback or another allowed family can still connect" | `AF_UNIX` is not loopback. An `AF_INET` socket is not in `_ALLOWED_FAMILIES`, so `connect` and `connect_ex` refuse it — demonstrated by `test_a_direct_socket_connect_is_blocked`, which is parametrised over both. |
| "The subprocess environment disables `PYTHONNOUSERSITE`" | It sets `PYTHONNOUSERSITE=1`, which disables *user site-packages*. The finding inverts the sense of the variable. |
| "`PYTHONPATH` never wires the copied plugin module path into pytest's import path" | `_run_in_workspace` copies the plugin into `plugin_dir` and `_sandbox_env` sets `PYTHONPATH` to exactly that directory. |

The remaining two are about paths the public API cannot reach: a per-test budget
of zero (`SandboxConfig` rejects any budget ≤ 0 at validation) and an empty
request producing no outcomes (deliberate, and the reason `only-named-tests-run`
holds at all).

## What the three runs did buy — six real defects

They were worth the money. Every one of these was found by the tool and none by
me:

1. `pytest_configure` returned early when no report path was set, installing the
   network block but never arming the per-test clock. A run with nowhere to
   report was half protected while still looking sandboxed.
2. A test that reached its own body and called `pytest.skip()` was recorded as
   never started.
3. Every requested test with no outcome got one undifferentiated reason, so "the
   budget stopped the run", "the run reported nothing at all" and "the run never
   reached this one" were indistinguishable.
4. The launching machine's user site-packages stayed on the child's path.
   Dropping `PYTHONPATH` from the allowlist does not remove it.
5. `socket.socket.connect` and `connect_ex` had no test at all. The earlier tests
   went only through `create_connection` and `getaddrinfo`, so half the block was
   unevidenced.
6. The per-test budget was silently skipped where `signal.setitimer` is absent,
   producing a result that looks time-bounded and is not. It now declines the
   run.

## Unrequested changes

Four, all `in_service`, and I agree with all four as observations. The public
package surface, the environment allowlist, the specific socket entry points
patched, and the runtime-versus-collection skip distinction all go beyond the
literal obligations. None is separable work; each is how the requested behaviour
is delivered. No action.

## Defect injection, which is the evidence behind the fixes

Ten defects injected one at a time, each reverted before the next. Two rounds
were needed because two tests survived the first pass and were rewritten:

- Killing only the pytest process, not its group, passed. The slow work ran
  inside pytest and died with it either way. The test now spawns a grandchild.
- Passing an empty request straight to pytest passed. With no ids requested the
  result is empty whether or not pytest ran. The project's test module now
  writes a marker on import.
- The "run produced no report" test used an unusable interpreter, which raises
  out of the spawn and is caught a level up — a different path from the one the
  test named. It now uses a conftest that raises.
- The user-site test asserted `site.ENABLE_USER_SITE` is false, which passes with
  the fix removed because this suite runs under a virtualenv. It now asserts the
  switch is set, and says in its own docstring that this is the weaker claim.

All ten are killed now.

## One environment note

`test_a_local_unix_socket_is_still_allowed` skips on this machine. I verified by
probe that the cause is the development sandbox refusing `AF_UNIX` **bind** with
`PermissionError: Operation not permitted`, not anything in this code — the same
probe with the sandbox disabled completes the round trip. The skip condition
probes as far as `bind`, because merely creating the socket succeeds and would
answer the wrong question.
