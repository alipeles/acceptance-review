"""Does comparing compiled forms catch the three cases #334 names?

#334 proposes compiling a module before and after an injected edit and comparing
the code objects, on the stated grounds that a text comparison "misses an added
condition that is always true, a value the callee ignores, and a reordering with
no effect".

This probe compiles each of those three against an unedited baseline, plus two
edits that genuinely change nothing observable, and reports two comparisons:

  - whole code objects, as #334 describes the check;
  - the nested function's instruction stream, constants and names, which is the
    same comparison with line-number tables excluded.

"Equal" means the check would refuse the edit.
"""

import sys

BASE = """
def f(x, items):
    total = 0
    for i in items:
        total += i
    return total + x
"""

ALWAYS_TRUE = """
def f(x, items):
    total = 0
    for i in items:
        if True:
            total += i
    return total + x
"""

ALWAYS_TRUE_OPAQUE = """
def f(x, items):
    total = 0
    for i in items:
        if i is not None or True:
            total += i
    return total + x
"""

IGNORED_VALUE = """
def f(x, items):
    total = 0
    for i in items:
        total += i
    unused = total * 2
    return total + x
"""

REORDERED = """
def f(x, items):
    for i in items:
        pass
    total = 0
    for i in items:
        total += i
    return total + x
"""

BLANK_LINE = """

def f(x, items):
    total = 0
    for i in items:
        total += i
    return total + x
"""

COMMENT_ONLY = """
def f(x, items):
    # a comment that changes nothing
    total = 0
    for i in items:
        total += i
    return total + x
"""

CASES = [
    ("always-true (literal)", ALWAYS_TRUE),
    ("always-true (opaque)", ALWAYS_TRUE_OPAQUE),
    ("ignored value", IGNORED_VALUE),
    ("no-effect reordering", REORDERED),
    ("blank line only", BLANK_LINE),
    ("comment only", COMMENT_ONLY),
]


def code_of(src):
    return compile(src, "<m>", "exec")


def nested(src):
    """The function's own code object, not the module's."""
    top = code_of(src)
    return next(const for const in top.co_consts if hasattr(const, "co_code"))


def whole_objects_equal(a, b):
    """Equality on the module code object, as #334 words the check."""
    return code_of(a) == code_of(b)


def instruction_stream_equal(a, b):
    """The same question with line-number tables excluded."""
    x, y = nested(a), nested(b)
    return (x.co_code, x.co_consts, x.co_names, x.co_varnames) == (
        y.co_code,
        y.co_consts,
        y.co_names,
        y.co_varnames,
    )


def main():
    print(f"python {sys.version.split()[0]}")
    print(f"{'case':<26} {'code objects equal':<20} instruction stream equal")
    for name, src in CASES:
        whole = str(whole_objects_equal(BASE, src))
        stream = instruction_stream_equal(BASE, src)
        print(f"{name:<26} {whole:<20} {stream}")


if __name__ == "__main__":
    main()
