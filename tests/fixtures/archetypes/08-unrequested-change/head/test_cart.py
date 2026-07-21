from cart import apply_discount, checkout


def test_apply_discount():
    assert apply_discount(100.0, 10) == 90.0


def test_checkout_default_unchanged():
    assert checkout([{"price": 2.0}, {"price": 3.0}]) == 5.0
