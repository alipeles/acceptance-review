def ship_order(order):
    order["status"] = "shipped"
    return True


def cancel_order(order):
    raise NotImplementedError
