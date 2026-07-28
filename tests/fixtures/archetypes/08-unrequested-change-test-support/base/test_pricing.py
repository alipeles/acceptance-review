from pricing import line_total


def _item(qty, price):
    return {"qty": qty, "price": price}


def test_line_total_multiplies_quantity_by_price():
    assert line_total(_item(2, 5.0)) == 10.0


def test_line_total_of_a_single_item():
    assert line_total(_item(1, 3.25)) == 3.25
