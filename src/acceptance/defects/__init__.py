"""Defect enumeration: the ways a change could plausibly fail an obligation.

The first stage of the defect-first evidence shape (#312, #313). It runs before
any test is looked at and produces a set of typed, identified `Defect` records
per obligation — the denominator a later stage maps tests onto.

Advisory in this milestone: nothing here changes a verdict or an obligation's
rating. That is deliberate (DR-312 decision 5). Landing enumeration alongside
the existing mapping/discrimination/strength chain rather than in place of it is
what makes a rating movement attributable to one cause instead of three.
"""

from acceptance.defects.enumeration import enumerate_defects
from acceptance.defects.taxonomy import CHECKLIST, checklist_for, enumerable

__all__ = ["CHECKLIST", "checklist_for", "enumerable", "enumerate_defects"]
