from orders import cancel_order, ship_order


def test_cancel_order_marks_cancelled():
    order = {"status": "pending"}
    assert cancel_order(order) is True
    assert order["status"] == "cancelled"


def test_ship_order_still_marks_shipped():
    order = {"status": "pending"}
    assert ship_order(order) is True
    assert order["status"] == "shipped"
