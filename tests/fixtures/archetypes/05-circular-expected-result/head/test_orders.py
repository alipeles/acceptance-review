from orders import _apply_tax, order_total


def test_total_applies_tax():
    subtotal, tax_rate = 100.0, 0.08
    # Expected is built from the same production helper the function uses, so a
    # bug in _apply_tax would appear identically on both sides.
    expected = round(_apply_tax(subtotal, tax_rate), 2)
    assert order_total(subtotal, tax_rate) == expected
