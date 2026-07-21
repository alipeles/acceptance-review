from loan import amortize


def test_returns_a_payment_for_each_month():
    schedule = amortize(1200.0, 0.06, 12)
    assert isinstance(schedule, list)
    assert len(schedule) == 12
    assert all(payment > 0 for payment in schedule)
