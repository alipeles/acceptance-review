from rounding import round_half_even


def test_rounds_to_nearest():
    # Non-discriminating: not a tie, so round-half-up and round-half-even agree.
    assert round_half_even(2.3) == 2
