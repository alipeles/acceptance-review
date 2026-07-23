from cart import apply_discount, checkout


def test_apply_discount_formats_as_money():
    cart = [{"price": 100.0}]
    assert apply_discount(cart, 10) == "$90.00"


def test_apply_discount_supports_other_currency():
    cart = [{"price": 100.0}]
    assert apply_discount(cart, 10, currency="EUR") == "EUR 90.00"


def test_checkout_still_works():
    assert checkout([{"price": 50.0}]) == "$50.00"
