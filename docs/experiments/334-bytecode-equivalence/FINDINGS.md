# Comparing compiled forms — what it actually catches

**#334's stated rationale for the bytecode check is wrong. Comparing compiled
forms catches none of the three cases the issue names.** It catches a different
and narrower class — edits that differ only in formatting, comments or line
position — and that class is real, since the existing text check is byte
equality and lets those through.

Run 2026-09-21 by `probe.py`, on the interpreter the project uses:

```
python 3.10.11
case                       code objects equal   instruction stream equal
always-true (literal)      False                False
always-true (opaque)       False                False
ignored value              False                False
no-effect reordering       False                False
blank line only            False                True
comment only               True                 True
```

"Equal" means the check refuses the edit.

## The three cases #334 names

#334 says a text comparison "misses an added condition that is always true, a
value the callee ignores, and a reordering with no effect". All three compile to
*different* code, so a compiled-form comparison lets all three through, exactly
as the text comparison does. An always-true condition emits a real test and
jump; an ignored assignment emits a real store; a reordering emits the same
instructions in a different order. None of them changes behaviour, and that is a
different question from whether the compiled form changes.

The `if True:` case was included in case CPython folded it away at compile time.
It does not, on 3.10.11.

A model is the right instrument for these three, which is what #335's first
question — does the edit change the code's behaviour at all — already asks.

## What it does catch, and the implementation consequence

The last two rows. A blank line and a comment both leave the instruction stream
identical while changing the text, so the existing check in
`mutation/validity.py`, which compares the replaced text to the replacement byte
for byte, accepts them today. `tests/test_mutation_validity.py::TestValidity::test_an_edit_differing_only_in_whitespace_is_not_identical`
pins that behaviour.

**The comparison has to be on the instruction stream, not on whole code
objects.** The blank-line row is the case that matters and whole-object equality
reports it as *different*, because the line-number tables differ. #334's wording,
"compile the original and the mutated module and compare the code objects",
describes the comparison that misses the only case it fixes.

A real implementation also has to recurse into nested code objects rather than
inspect one function, and applies only to languages with a compiler — the same
shape as `_PARSERS` in `mutation/validity.py`.

## Scope

Only Python 3.10.11 was measured, and only on one small function. The claim here
is about which *kind* of difference survives compilation, which does not depend
on the example, but a different interpreter version may fold constants
differently.
