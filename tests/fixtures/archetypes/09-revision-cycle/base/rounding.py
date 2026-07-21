import math


def round_half_even(x):
    # First pass: naive rounding — ties round up, not to even.
    return math.floor(x + 0.5)
