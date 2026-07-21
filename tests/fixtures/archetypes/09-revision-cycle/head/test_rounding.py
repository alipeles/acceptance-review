from rounding import round_half_even


def test_rounds_to_nearest():
    assert round_half_even(2.3) == 2


def test_ties_round_to_even():
    # The discriminating case the first pass was missing.
    assert round_half_even(2.5) == 2
    assert round_half_even(3.5) == 4
