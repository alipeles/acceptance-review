from inventory import restock


def test_restock_increases_quantity():
    item = {"qty": 5}
    assert restock(item, 3) == 8
    assert item["qty"] == 8
