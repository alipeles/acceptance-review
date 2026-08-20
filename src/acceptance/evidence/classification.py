"""The §9.3 evidence-class reduce, on its own so two stages can share it.

`classify_strength` (M5.3) owns the reduce conceptually, and it still does — this
module holds only the arithmetic, and `strength.py` calls it. It was lifted out
because a second caller appeared: the discrimination reader has to know whether
a fresh judgement *moves the rating* before it will accept it (#292), and the
rating is not something the judge returns. The judge returns defects; the class
is this reduce over them.

The reader cannot simply import `classify_strength`, because `strength.py`
imports `ObligationDiscrimination` from `discrimination.py` and the import would
close a cycle. Re-deriving the arithmetic in the reader was the alternative and
is worse: two copies of the bright line drift, and the one in the reader would be
deciding whether to reject a judgement on a rule the classifier no longer used.

So the rule lives here once, and both callers are downstream of it.
"""

from __future__ import annotations

from collections.abc import Sequence

from acceptance.review_state import EvidenceClassification


def evidence_class_for(
    has_mapped_test: bool,
    caught_flags: Sequence[bool] | None,
) -> EvidenceClassification:
    """The §9.3 class implied by one criterion's discrimination verdicts.

    `caught_flags` is that criterion's `would_be_caught` answers in order, or
    None when no discrimination was judged for it at all. The distinction
    between None and an empty sequence is not cosmetic: both mean "no defect
    verdicts", and both classify `indeterminate`, but keeping the argument
    honest about which one happened stops a caller passing `[]` for "not judged"
    and later reading it as "judged, found nothing".

        no mapped test at all         -> unsupported
        mapped test, no defect judged -> indeterminate
        all named defects caught      -> strongly_supported
        some (>=1) but not all        -> partially_supported
        a mapped test, none caught    -> nominally_supported
    """
    if not has_mapped_test:
        return "unsupported"
    if not caught_flags:
        return "indeterminate"
    caught = sum(1 for flag in caught_flags if flag)
    if caught == len(caught_flags):
        return "strongly_supported"
    if caught:
        return "partially_supported"
    return "nominally_supported"
