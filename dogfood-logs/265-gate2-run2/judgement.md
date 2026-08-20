# Judgement — #265, Gate 2, run 2

`check --base c63bf86 --head 8a09d5c --continue 7971c67ae6329468 --mode record`.
Run id `d4e73514c738223a`, continuing Gate 1's `7971c67ae6329468`.

## Outcome: NOT clean. `Task completion: INCOMPLETE`.

```
2 obligation(s) with non-discriminating test evidence
  (test-request-unique-content-after-shared-content,
   test-shared-content-byte-identical-across-requests).
```

Sixteen of eighteen obligations are fully satisfied. Two are `unsupported`, both
reported as `(no mapped test)`, and both are Completion expectations whose
Constraint twin is `strongly supported` **citing the exact test the Completion
twin is told is missing**.

| # | obligation | rating | the test |
|---|---|---|---|
| 4 | `shared-content-ordered-by-breadth` (constraint-02) | strongly supported | cites `test_no_request_places_content_unique_to_it_ahead_of_content_it_shares` (4.14) |
| 15 | `test-request-unique-content-after-shared-content` (completion-02) | **unsupported** | "(no mapped test)" |
| 3 | `shared-content-byte-identical-across-requests` (constraint-01) | strongly supported | cites `test_content_two_requests_share_is_written_the_same_way_in_both` (3.13) |
| 16 | `test-shared-content-byte-identical-across-requests` (completion-03) | **unsupported** | "(no mapped test)" |

Everything else is clean: no open questions, all ten unrequested changes
dispositioned `in_service`, no `separable` or `risky`, no `unclear`, no
`not_addressed`, and the only evidence limitation is the standing one that static
judgements were not confirmed by execution.

## The recommendations, read before forming an opinion

- Obligation 15: *"A test case shows a request with unique content ordered before
  shared content and the test fails."* Detects: *"A stage assembles its request
  with stage-specific content before the shared opening."*
- Obligation 16: *"A test case shows the same shared content rendered differently
  in two requests and the test fails."*

Both describe tests that exist:

- `tests/test_pipeline_request_openings.py::test_no_request_places_content_unique_to_it_ahead_of_content_it_shares`
- `tests/test_pipeline_request_openings.py::test_content_two_requests_share_is_written_the_same_way_in_both`

Both were falsified before being trusted. Injecting the pre-change shape into
`recommendations.py` — the diff appended after the stage's own criteria — makes
the first fail; reversing `assemble`'s sort makes the second fail. Neither is a
test that passes because nothing is checked.

## Attribution: #245, evidenced from the transcripts rather than inferred

The mapping stage **did** map the test to obligation 15. From the run's own
mapping transcript `714a89b33d`:

```
test: tests/test_pipeline_request_openings.py::test_no_request_places_...
ids : ['shared-content-ordered-by-breadth',
       'test-request-unique-content-after-shared-content']
why : Fails when content shared by multiple requests appears after
      request-unique content, which is exactly the breadth-based ordering
      rule and its corresponding failure case.
```

Both ids, with a rationale that names the twin relationship correctly. And a
second mapping transcript, `39e47c338f`, for the **same test in its own batch**,
returned only `['shared-content-ordered-by-breadth']`. Two calls, same test, same
partition size (12), five minutes apart, different answers — and the run
consumed the one that dropped the twin.

So this is not a mapper that cannot see the relationship. It saw it, articulated
it, and did not return it on the call that counted. That is #245 (twin
obligations split across a Constraint/Completion pair), with the sharpest
evidence yet: the correct answer is in the corpus, from the same stage, minutes
away from the wrong one.

Traced to be sure the loss was not downstream of mapping:
`apply_test_mapping` (`mapping.py:241-254`) iterates every returned
`obligation_id`, and `extraction.py:60` carries the whole list, so neither drops
a twin. The persisted review has `"test_evidence": []` on obligation 15, which
matches the consumed mapping exactly.

**Queued as a comment on #245.** Not filed as a new issue: #245 owns this
failure and already carries three instances.

## Disposition: this is a stop, not a pass with a caveat

Per the gate rules the finding is attributed to a tool defect and recorded
against it, which is one of the two permitted dispositions. But attribution does
not make the gate clean, and the rule is explicit that anything short of every
obligation strongly supported is a stop. **Presented to the human, not worked
around.**

The alternative — writing a second, differently-named test so the mapper
attaches something to obligations 15 and 16 — was rejected. The tests the
recommendations describe already exist and are already cited elsewhere in the
same report. Adding duplicates would be chasing a rating rather than fixing a
defect, which is the disposition #259's Gate 2 recorded for the same shape.

## The measurement #265 exists for: no improvement inside a run

This is not a Gate 2 criterion — `exclusion-04` puts provider behaviour out of
scope, deliberately — but it is why the issue exists, so it is recorded here.

Per-stage cached share from the live pass:

```
test-to-obligation mapping    18 calls  85,609 prompt   4.5% cached
coverage classification        1 call   79,073 prompt   0.0% cached
unrequested-change detection   1 call   78,585 prompt   0.0% cached
discrimination judgment        1 call   13,716 prompt   0.0% cached
```

Coverage classification and unrequested-change detection now open with a
byte-identical ~70k-token diff block, seconds apart, in one run — and the second
reused none of it. **The cross-stage prefix did not pay.**

One hypothesis, offered as a hypothesis: each stage sends a different
`response_format` schema (`_Coverage` vs `_Detections`), and if the provider's
cache key covers the schema as well as the messages, then no two stages can ever
share a prefix however their messages are ordered. That would also explain
mapping's stubborn 3-of-464 in the baseline, which #265's comment recorded as
unexplained by either ordering or length. It is testable — issue the same
messages twice under one schema and under two — and it should be tested before
any more work is done on ordering.

If it holds, the ordering change is still correct and still cheap, but the win
it was made for lives in *sibling* calls within a partitioned stage, not across
stages, and #265's remaining lever is batching rather than ordering.
