from receipt import format_line


def test_positive_line():
    assert format_line("Widget", 3, 2.5) == "Widget x3 @ $2.50 = $7.50"


def test_two_decimal_formatting():
    assert format_line("Gadget", 1, 4) == "Gadget x1 @ $4.00 = $4.00"
