def ship_order(order):
    order["status"] = "shipped"
    order["shipped_count"] = order.get("shipped_count", 0) + 1
    return True


def cancel_order(order):
    order["status"] = "cancelled"
    return True
