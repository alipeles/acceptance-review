from billing import prorate


def test_half_of_a_month():
    # 30-day month: price / 30 and price / days_in_month coincide here, so this
    # input cannot distinguish the correct rate from a hard-coded /30.
    assert prorate(30.0, 15, 30) == 15.0
