from pricing import parse_price


def test_dollar_symbol():
    assert parse_price("$12.50") == (12.50, "USD")


def test_euro_symbol():
    assert parse_price("€3.00") == (3.00, "EUR")
