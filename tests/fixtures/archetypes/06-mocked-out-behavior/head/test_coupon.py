from unittest.mock import Mock

from coupon import coupon


def test_coupon_uses_selected_rate():
    source = Mock()
    # rate_for is mocked to a constant regardless of the date, so this test
    # never establishes that the rate for THIS date is the one selected.
    source.rate_for.return_value = 0.05
    assert coupon(1000.0, source, "2020-01-26") == 50.0
